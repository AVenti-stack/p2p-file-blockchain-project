import base64
from pathlib import Path

from quart import Quart, request

import framework

app = Quart(__name__)

root_folder = Path().home() / Path("bchain")


def encode_bytes(b: bytes) -> str:
    encoded = base64.b64encode(b)
    return encoded.decode("ascii")


# shows that this peer is alive
@app.route("/ping", methods=["POST"])
async def ping():
    return "1"


# gives requester knowledge of the P2P network
@app.route("/discover/pop", methods=["POST"])
async def discover_pop():
    # TODO: ask how to implement this
    pass


# gives responder knowledge of the P2P network
@app.route("/discover/push", methods=["POST"])
async def discover_push():
    # TODO: ask how to implement this
    pass


# uploads a file slice
@app.route("/upload", methods=["POST"])
async def upload():
    # get the JSON body
    json = await request.get_json()
    # get the JSON data
    file_id = str(json["file_id"])
    slice = int(json["slice"])
    data = str(json["data"])
    # decode the bytes
    bytes = base64.b64decode(data)
    # get the path
    save_folder = root_folder / Path(str(framework.my_peer.id)) / Path(file_id)
    save_folder.mkdir(exist_ok=True)
    slice_file = save_folder / Path(str(slice))
    # write bytes to path
    slice_file.write_bytes(bytes)
    return "1"


# downloads a file slice
@app.route("/download", methods=["POST"])
async def download():
    # get the JSON body
    json = await request.get_json()
    # get the JSON data
    file_id = str(json["file_id"])
    slice = int(json["slice"])
    save_folder = root_folder / Path(str(framework.my_peer.id)) / Path(file_id)
    slice_file = save_folder / Path(str(slice))
    bytes = slice_file.read_bytes()
    data = encode_bytes(bytes)
    return data
