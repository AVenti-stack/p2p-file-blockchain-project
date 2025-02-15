"""
This file is part of aioquic

Copyright (c) 2019 Jeremy Lainé.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of aioquic nor the names of its contributors may
      be used to endorse or promote products derived from this software without
      specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import asyncio
import logging
import os
import pickle
import time
from collections import deque
from pathlib import Path
from typing import AsyncIterator, Deque, Dict, Optional, Tuple, cast
from urllib.parse import urlparse

import httpcore
from httpx import AsyncClient

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, H3Event, Headers, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent

logger = logging.getLogger("client")
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)

configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
session_ticket: Optional[Path] = None

if session_ticket:
    try:
        with open(session_ticket, "rb") as fp:
            configuration.session_ticket = pickle.load(fp)
    except FileNotFoundError:
        pass


class H3Transport(QuicConnectionProtocol, httpcore.AsyncHTTPTransport):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._http = H3Connection(self._quic)
        self._read_queue: Dict[int, Deque[H3Event]] = {}
        self._read_ready: Dict[int, asyncio.Event] = {}

    async def arequest(
            self,
            method: bytes,
            url: Tuple[bytes, bytes, Optional[int], bytes],
            headers: Headers = None,
            stream: httpcore.AsyncByteStream = None,
            ext: dict = None,
    ) -> Tuple[int, Headers, httpcore.AsyncByteStream, dict]:
        stream_id = self._quic.get_next_available_stream_id()
        self._read_queue[stream_id] = deque()
        self._read_ready[stream_id] = asyncio.Event()

        # prepare request
        self._http.send_headers(
            stream_id=stream_id,
            headers=[
                        (b":method", method),
                        (b":scheme", url[0]),
                        (b":authority", url[1]),
                        (b":path", url[3]),
                    ]
                    + [
                        (k.lower(), v)
                        for (k, v) in headers
                        if k.lower() not in (b"connection", b"host")
                    ],
        )
        async for data in stream:
            self._http.send_data(stream_id=stream_id, data=data, end_stream=False)
        self._http.send_data(stream_id=stream_id, data=b"", end_stream=True)

        # transmit request
        self.transmit()

        # process response
        status_code, headers, stream_ended = await self._receive_response(stream_id)
        response_stream = httpcore.AsyncIteratorByteStream(
            aiterator=self._receive_response_data(stream_id, stream_ended)
        )

        return (
            status_code,
            headers,
            response_stream,
            {
                "http_version": "HTTP/3",
            },
        )

    def http_event_received(self, event: H3Event):
        if isinstance(event, (HeadersReceived, DataReceived)):
            stream_id = event.stream_id
            if stream_id in self._read_queue:
                self._read_queue[event.stream_id].append(event)
                self._read_ready[event.stream_id].set()

    def quic_event_received(self, event: QuicEvent):
        #  pass event to the HTTP layer
        if self._http is not None:
            for http_event in self._http.handle_event(event):
                self.http_event_received(http_event)

    async def _receive_response(self, stream_id: int) -> Tuple[int, Headers, bool]:
        """
        Read the response status and headers.
        """
        stream_ended = False
        while True:
            event = await self._wait_for_http_event(stream_id)
            if isinstance(event, HeadersReceived):
                stream_ended = event.stream_ended
                break

        headers = []
        status_code = 0
        for header, value in event.headers:
            if header == b":status":
                status_code = int(value.decode())
            else:
                headers.append((header, value))
        return status_code, headers, stream_ended

    async def _receive_response_data(
            self, stream_id: int, stream_ended: bool
    ) -> AsyncIterator[bytes]:
        """
        Read the response data.
        """
        while not stream_ended:
            event = await self._wait_for_http_event(stream_id)
            if isinstance(event, DataReceived):
                stream_ended = event.stream_ended
                yield event.data
            elif isinstance(event, HeadersReceived):
                stream_ended = event.stream_ended

    async def _wait_for_http_event(self, stream_id: int) -> H3Event:
        """
        Returns the next HTTP/3 event for the given stream.
        """
        if not self._read_queue[stream_id]:
            await self._read_ready[stream_id].wait()
        event = self._read_queue[stream_id].popleft()
        if not self._read_queue[stream_id]:
            self._read_ready[stream_id].clear()
        return event


def save_session_ticket(ticket):
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info("New session ticket received")
    if session_ticket:
        with open(session_ticket, "wb") as fp:
            pickle.dump(ticket, fp)


async def run(
        url: str,
        data: str,
        include: bool,
        output_dir: Optional[str],
) -> None:

    if output_dir is not None and not os.path.isdir(output_dir):
        raise Exception("%s is not a directory" % output_dir)

    # parse URL
    parsed = urlparse(url)
    assert parsed.scheme == "https", "Only https:// URLs are supported."
    host = parsed.hostname
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443

    async with connect(
            host,
            port,
            configuration=configuration,
            create_protocol=H3Transport,
            session_ticket_handler=save_session_ticket,
    ) as transport:
        async with AsyncClient(
                transport=cast(httpcore.AsyncHTTPTransport, transport)
        ) as client:
            # perform request
            start = time.time()
            if data is not None:
                response = await client.post(
                    url,
                    content=data.encode(),
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
            else:
                response = await client.get(url)

            elapsed = time.time() - start

        # print speed
        octets = len(response.content)
        logger.info(
            "Received %d bytes in %.1f s (%.3f Mbps)"
            % (octets, elapsed, octets * 8 / elapsed / 1000000)
        )

        # output response
        if output_dir is not None:
            output_path = os.path.join(
                output_dir, os.path.basename(urlparse(url).path) or "index.html"
            )
            with open(output_path, "wb") as output_file:
                if include:
                    headers = ""
                    for header, value in response.headers.items():
                        headers += header + ": " + value + "\r\n"
                    if headers:
                        output_file.write(headers.encode() + b"\r\n")

                output_file.write(response.content)
