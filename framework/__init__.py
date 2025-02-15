from logging import getLogger
from pathlib import Path

from flexx import flx

from jinja2 import Environment, PackageLoader, select_autoescape
from tinydb import TinyDB

env = Environment(
    loader=PackageLoader('gui', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

log = getLogger(__name__)

asset_dirs = ["webfonts/", "img/"]

my_peer = None
ddns = None
blockchain = None
m = None
downloads_db = TinyDB('ddb.json')
uploads_db = TinyDB('udb.json')


def load_flexx_static(data):
    for asset_dir in asset_dirs:
        data = data.replace(asset_dir, f"/flexx/data/shared/{asset_dir}/")
    return data


def load_template(filename, kwargs):
    template = env.get_template(filename)
    print(kwargs)
    return load_flexx_static(template.render(**kwargs))


def load_static(filename):
    with open(filename) as f:
        data = f.read()
    return load_flexx_static(data)



for asset_dir in asset_dirs:
    path = f"gui/{asset_dir}"
    for asset in Path(path).iterdir():
        if asset.is_file():
            print("Loaded shared asset " +
                  flx.assets.add_shared_data(f"{asset_dir}{asset.name}", asset.read_bytes()))
