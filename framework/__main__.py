# this page that boots the app up
from gevent import monkey; monkey.patch_all()

from framework.core import Core
from exchange import host_file_server
from discovery import spoof, fakeDDNS, status_report
from blockchain import Blockchain
from flexx import flx
import framework
import discovery
import logging
import flexx
import threading

flexx.config.log_level = logging.INFO


def run_flexx():
    a = flx.App(Core, title='bChain')
    framework.m = a.launch(runtime='chrome-app') # this is where you can change what browser opens the app


def startup():
    framework.blockchain = Blockchain()
    # init peers
    peers = spoof()
    framework.ddns = fakeDDNS()
    for peer in peers:
        print('bootstrapping peer {}'.format(peer.id))
        host_file_server(peer.id, peer.port)
        peer.bootstrap(framework.ddns)

    framework.my_peer = discovery.Peer(id='100', ip='localhost',
                                       port=7000, known_peers=[])
    peers.append(framework.my_peer)
    status_report('BEFORE JOINING', framework.ddns, peers)
    host_file_server(framework.my_peer.id, framework.my_peer.port)
    framework.my_peer.bootstrap(framework.ddns)
    status_report('AFTER JOINING', framework.ddns, peers)
    framework.m.bootstrap_progress(1)


if __name__ == '__main__':
    run_flexx()

    startup_thread = threading.Thread(target=startup)
    startup_thread.start()

    flx.start()
    startup_thread.join()
