import asyncio
import base64
import math
import re
import threading
from pathlib import Path

from gevent.server import DatagramServer
from gevent import socket
from hypercorn.config import Config
from hypercorn.asyncio import serve

import framework
from discovery import discover, Peer
from exchange.server import app

PART_SEPARATOR = "\u241E"
PAIR_SEPARATOR = "\u241F"
MESSAGE_TERM = "\u001B"

tmp_cache = dict()


def encode_bytes(b: bytes) -> str:
    encoded = base64.b64encode(b)
    return encoded.decode("ascii")


class FileServer(DatagramServer):
    """
    This protocol defines the behavior of receiving a file request and issuing a response.
    """

    def __init__(self, *args, **kwargs):
        self.peer = kwargs.pop("peer")
        DatagramServer.__init__(self, *args, **kwargs)

    def start(self):
        super().start()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)

    def handle(self, data, address):
        msg = data.decode('utf-8')
        parts = msg.split(PART_SEPARATOR)

        name = parts[0]
        print("Got message: " + name)
        if name == "Upload":
            file_id = parts[1].split(PAIR_SEPARATOR)[1]
            slice = int(parts[2].split(PAIR_SEPARATOR)[1])
            data = parts[3].split(PAIR_SEPARATOR)[1]
            bytes = base64.b64decode(data)
            dest = Path.home() / Path(f".bchain/{self.peer}/files/{file_id}")
            dest.mkdir(parents=True, exist_ok=True)
            file_path = f"{str(dest)}/{slice}"
            print(f"Writing {file_path}")
            with open(file_path, "wb") as f:
                f.write(bytes)
        elif name == "SliceRequest":
            file_id = parts[1].split(PAIR_SEPARATOR)[1]
            slice = int(parts[2].split(PAIR_SEPARATOR)[1])
            dest = Path.home() / Path(f".bchain/{self.peer}/files/{file_id}")
            file_path = f"{str(dest)}/{slice}"
            print(f"Got slice request for {file_path}")
            with open(file_path, "rb") as f:
                self.socket.sendto(f.read(), address)
        elif name == "JoinNetwork":
            self.socket.sendto(self.peer.encode(), address)


def get_message(name, **kwargs):
    msg = name
    for key, value in kwargs.items():
        msg += PART_SEPARATOR
        msg += type(value).__name__
        msg += PAIR_SEPARATOR
        msg += str(value)
    # msg += MESSAGE_TERM
    return msg


def probe(peer):
    ip = 'localhost'
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
    seconds = (2).to_bytes(8, 'little')
    useconds = (0).to_bytes(8, 'little')
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, seconds + useconds)
    for port in range(2000, 6000, 1):
        dest = (ip, port)
        msg = get_message("JoinNetwork", ip=ip, port=port)
        sock.connect(dest)
        sock.send(msg.encode())
        data, _ = sock.recvfrom(64 * 1024)
        data = data.decode()
        if type(data) == Peer:
            for mutual in data.known_peers:
                if mutual not in peer.known_peers:
                    peer.known_peers.append(mutual)
                if peer not in mutual.known_peers:
                    mutual.known_peers.append(peer)
            return


def download_file(my_peer, file_id, size, download_path):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
    locations = discover(my_peer, file_id, size=size)
    file = bytearray()
    slices = len(locations)
    for i in range(slices):
        dests = locations[i]
        dest_iter = iter(dests)
        downloading = True
        print("Downloading slice: " + str(i))
        while downloading:
            try:
                dest = next(dest_iter)
                sock.connect(dest)
                msg = get_message("SliceRequest", file_id=file_id, slice=i)
                sock.send(msg.encode())
                data, address = sock.recvfrom(64 * 1024)
                file += bytearray(data)
                downloading = False
            except Exception as e:
                print("err: " + str(e))
        framework.m.download_progress(file_id, float(i) / (slices + 1))
    sock.close()
    download_folder = Path.home() / Path(f".bchain/downloads")
    download_folder.mkdir(parents=True, exist_ok=True)
    dest = download_folder / Path(download_path)
    file_path = str(dest)
    print(f"Downloading {file_id} to {file_path}")
    with open(file_path, "wb") as f:
        f.write(file)
    framework.m.download_progress(file_id, 1)


file_pattern = re.compile(r'.*?(\d+).*?')


def get_order(file):
    match = file_pattern.match(Path(file).name)
    if not match:
        return math.inf
    return int(match.groups()[0])


def upload_file_thread(my_peer, path, file_id):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
    sliced_directory, locations = discover(
        my_peer, file_id=file_id, file_path=path)
    p = Path(sliced_directory.name).glob("*" + path.suffix)
    files = [x for x in p if x.is_file()]
    files = sorted(files, key=get_order)
    print(files)
    slices = len(locations)
    for i in range(slices):
        file = files[i]
        slice_dests = locations[i]
        print("Uploading slice: " + str(i))
        with open(file, "rb") as f:
            bytes = f.read()
            encoded = base64.b64encode(bytes)
            data = encoded.decode("ascii")
            for dest in slice_dests:
                sock.connect(dest)
                msg = get_message("Upload", file_id=file_id,
                                  slice=i, contents=data)
                sock.send(msg.encode())
        framework.m.download_progress(file_id, (float(i) + 1) / slices, False)
    sock.close()


def upload_file(my_peer, path, title, tag, type, size):
    _ = framework.blockchain.new_transaction(title, path.name, type, tag, size)
    file_id = framework.blockchain.new_block()["previous_hash"]
    framework.m.download_progress(file_id, 0, False)
    framework.m.get_chain("upload")
    thread = threading.Thread(
        target=upload_file_thread, args=(my_peer, path, file_id))
    thread.start()


def host_file_server(peer, port):
    FileServer(f':{port}', peer=peer).start()


def run(port):
    config = Config()
    config.bind = ["localhost:" + port]
    asyncio.run(serve(app, config))
