import random
import tempfile
import time
import itertools
import os
import socket
import math
from pathlib import Path
from typing import List
from threading import Thread
from fsplit.filesplit import Filesplit
from dataclasses import dataclass
from random import randrange

# import framework
import framework

REDUNDANCY_FACTOR = 1

REQUEST_WAIT_INTERVAL = 2
GUARDIAN_WAIT_INTERVAL = 1
WATCHDOG_WAIT_INTERVAL = 1
WATCHDOG_LOOP_INTERVAL = 2
GUARD_THRESHOLD = 2
DOMAIN_NAME = 'bchain-network.xyz'

PEERS = 4
# Tying this to number of peers for now until it is officially determined
PEER_ID_LENGTH = math.ceil(math.log2(PEERS))
# PEER_ID_LENGTH = 36

# How much bigger a file has to be for it to move up a level
LEVEL_DETERMINANT = (100 * 1024)  # 100kB

# slice size in Bytes (32kB)
SLICE_SIZE = 32 * 1024

fs = Filesplit()


def status_report(message: str, ddns, peers):
    print('\n'+message)
    for peer in peers:
        known_peers = len(peer.known_peers)
        if known_peers < 0:
            known_peers = 0
        print('peer {} knows of {} other peers'.format(
            peer.id, known_peers))
    print('BSP index: {}, guardian count: {}'.format(
        ddns.BSPIndex, ddns.guardian_count))


def check_socket(host, port):
    print(f'checking port {port}')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


class fakeDDNS:
    BSPIndex = 0
    guardian_count = 0
    peers = list()

    def resolve(self, domain):
        assert domain == 'bchain-network.xyz'
        return self.peers[self.BSPIndex].ip, self.peers[self.BSPIndex].port

    def update(self, domain, ip, port):
        assert domain == 'bChain'
        for index, peer in enumerate(self.peers):
            if peer.ip == ip and peer.port == port:
                self.BSPIndex = index
                return

    def checkActive(self, ip, port):
        for peer in self.peers:
            if peer.ip == ip and peer.port == port:
                return True
        return False

    def hireNewGuard(self):
        for index, peer in enumerate(self.peers):
            if index != self.BSPIndex:
                self.guardian_count += 1
                guard_bsp_thread = Thread(name=peer.id, target=guardBSP,
                                          args=(peer, self))
                guard_watchdogs_thread = Thread(name=peer.id, target=guardWatchdogs,
                                                args=(peer, self))
                guard_bsp_thread.start()
                guard_watchdogs_thread.start()

    def joinOverlay(self, me):
        for peer in self.peers:
            if me not in peer.known_peers:
                peer.known_peers.append(me)
            if peer not in me.known_peers:
                me.known_peers.append(peer)


@dataclass
class Peer:
    id: str
    ip: str
    port: int
    known_peers: list

    '''
    is_BSP: bool
    guardians: int

    is_guardian: bool
    bsp = None
    '''

    def set_ip(self):
        hostname = socket.gethostname()
        self.ip = socket.gethostbyname(hostname)

    def bootstrap(self, ddns: fakeDDNS):
        ddns.peers.append(self)
        ip, port = ddns.resolve(DOMAIN_NAME)
        if ddns.checkActive(ip, port):
            ddns.joinOverlay(self)
            self.checkBecomeGuardian(ddns)
        else:
            random_offset = random.random() * .1
            time.sleep(REQUEST_WAIT_INTERVAL + random_offset)
            ip, port = ddns.resolve(DOMAIN_NAME)
            if ddns.checkActive(ip, port):
                ddns.joinOverlay(self)
                print('in')
                self.checkBecomeGuardian(ddns)
                print('out')
            else:
                ddns.update(DOMAIN_NAME, self.ip, self.port)
        pass

    def checkBecomeGuardian(self, ddns: fakeDDNS):
        if ddns.guardian_count < GUARD_THRESHOLD:
            random_offset = random.random() * .1
            time.sleep(GUARDIAN_WAIT_INTERVAL + random_offset)
            if ddns.guardian_count < GUARD_THRESHOLD:
                ddns.guardian_count += 1

                guard_bsp_thread = Thread(
                    name=self.id, target=guardBSP, args=(self, ddns))
                guard_watchdogs_thread = Thread(name=self.id, target=guardWatchdogs,
                                                args=(self, ddns))

                guard_bsp_thread.start()
                guard_watchdogs_thread.start()


def guardBSP(peer: Peer, ddns: fakeDDNS):
    while ddns.resolve(DOMAIN_NAME) != (peer.ip, peer.port):
        ip, port = ddns.resolve(DOMAIN_NAME)
        if not ddns.checkActive(ip, port):
            random_offset = random.random() * .1
            time.sleep(WATCHDOG_WAIT_INTERVAL + random_offset)
            ip, port = ddns.resolve(DOMAIN_NAME)
            if not ddns.checkActive(ip, port):
                ddns.update(DOMAIN_NAME, peer.ip, peer.port)
                ddns.guardian_count -= 1
                return
        time.sleep(WATCHDOG_LOOP_INTERVAL)


def guardWatchdogs(peer: Peer, ddns: fakeDDNS):
    while ddns.resolve(DOMAIN_NAME) != (peer.ip, peer.port):
        if ddns.guardian_count < GUARD_THRESHOLD:
            random_offset = random.random() * .1
            time.sleep(REQUEST_WAIT_INTERVAL + random_offset)
            if ddns.guardian_count < GUARD_THRESHOLD:
                ddns.hireNewGuard()
        time.sleep(WATCHDOG_WAIT_INTERVAL)
    ddns.guardian_count -= 1


def slice_file(file_path: Path, file_id: str) -> tempfile.TemporaryDirectory:
    """
    Splits a file into smaller slices for distribution
    """
    print(f'slicing {file_id}')
    dest = tempfile.TemporaryDirectory(file_id)
    fs.split(file=str(file_path.resolve()),
             split_size=SLICE_SIZE, output_dir=dest.name)
    return dest


def level(size):
    """
    returns the level a file should be stored at given it's size
    """

    lowest_level = math.floor(math.log2(PEERS))
    inverse_level = size / LEVEL_DETERMINANT

    return round(max(lowest_level - inverse_level, 1))


def get_ip(me, desired_peer_id: str):
    print(desired_peer_id)
    for peer in me.known_peers:
        if peer.id == desired_peer_id:
            return peer.ip, peer.port
    print("FAILED TO GET IP")
    '''
    for peer in me.known_peers:
        get_ip(peer, desired_peer_id)
    '''


def discover(peer: Peer, file_id: str, file_path: Path = None, size=None):
    """
    Handles discovery of peers to distribute or gather a file's slices from

    Both require a file ID

    Distribution requires a local file path
    EX:
    discover(file_id, file_path=FILE_PATH)

    Gathering requires knowledge of the file size
    EX:
    discover(file_id, size=SIZE)
    """
    if file_path is not None:
        size = os.path.getsize(file_path)
    else:
        assert size is not None
    lvl = level(size)
    num_peers = 2 ** (math.ceil(math.log2(PEERS)) - lvl)
    num_slices = math.ceil(size / SLICE_SIZE)
    prty = parity(file_id)
    reps_needed = math.ceil(REDUNDANCY_FACTOR * (num_slices / num_peers))
    peers = get_peers_list(lvl, prty)
    print(peers)
    print('{} peers, {} slices, {} reps, level {}'.format(num_peers,
                                                          num_slices,
                                                          reps_needed, lvl))
    locations = [set()] * num_slices
    peer_index, slice_index = 0, 0
    for _ in range(num_slices * reps_needed):
        peer_data = get_ip(peer, peers[peer_index])
        print(peer_data)
        locations[slice_index].add(peer_data)
        slice_index = (slice_index + 1) % num_slices
        peer_index = (peer_index + 1) % num_peers
    print(locations)
    if file_path is not None:
        sliced_directory = slice_file(file_path, file_id)
        return sliced_directory, locations
    else:
        return locations


def get_peers_list(level: int, parity: str):
    peers = list()
    # determine string to the right of level that will be same for all peers
    right = parity[-level:]
    # number of digits to the left of level in an ID
    left_digits = (PEER_ID_LENGTH - level)
    # all possible permutations of digits to the left of level
    lefts = ["".join(x) for x in itertools.product("01", repeat=left_digits)]
    # for every permutation
    for left in lefts:
        peers.append((str(left) + str(right)))
    return peers


def parity(file_id: str):
    """
    Returns a deterministic string of 0's and 1's given a file ID
    """
    file_id = str(file_id)
    parity = ''
    for char in file_id:
        parity += str(ord(char) % 2)
    return parity


def spoof() -> List[Peer]:
    print('\n\ncreating {} local peers on random ports'.format(PEERS))
    peers = list()
    ids = ["".join(x) for x in itertools.product("01", repeat=PEER_ID_LENGTH)]
    for i in range(PEERS):
        port = -1
        host = "localhost"
        while port == -1:
            port = randrange(2000, 6000, 1)
            if check_socket(host, port):
                port = -1
        framework.m.bootstrap_progress((float(i) + 1) / (PEERS * 1.1))
        peers.append(Peer(id=ids[i], ip=host, port=port, known_peers=list()))
    print("network initialized\n")
    return peers
