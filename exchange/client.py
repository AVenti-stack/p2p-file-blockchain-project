import framework
from discovery import discover


def download_file(file_id, size, file_name):
    locations = discover(framework.my_peer, file_id, size=size)
    file = bytearray()
    for i in range(len(locations)):
        dests = list(locations[i])


