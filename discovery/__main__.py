from discovery import fakeDDNS, LEVEL_DETERMINANT, level, spoof
import discovery


def status_report(message: str):
    print('\n'+message)
    for peer in peers+[newPeer]:
        known_peers = len(peer.known_peers)
        if known_peers < 0:
            known_peers = 0
        print('peer {} knows of {} other peers'.format(
            peer.id, known_peers))
    print('BSP index: {}, guardian count: {}'.format(
        ddns.BSPIndex, ddns.guardian_count))


if __name__ == '__main__':
    peers = spoof()
    ddns = fakeDDNS()

    for peer in peers:
        print('bootstrapping peer {}'.format(peer.id))
        peer.bootstrap(ddns)

    newPeer = discovery.Peer(id='100', ip='localhost',
                             port=7000, known_peers=[])

    status_report('BEFORE JOINING')
    newPeer.bootstrap(ddns)
    status_report('AFTER JOINING')


def test_get_slices():
    # assert get_slices(_) == _
    assert False, "No test exists yet, idiot"


def test_level():
    answer = [6, 5, 4, 3, 2, 1, 1, 1, 1, 1, 1]
    for i, ans in zip(range(1 * 1024 ** 2, 1 * 1024 ** 3, LEVEL_DETERMINANT), answer):
        lvl = level(i)
        assert lvl == ans, '\nlevel: {}\n expected: {}'.format(lvl, ans)
