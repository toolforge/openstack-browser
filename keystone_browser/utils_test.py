from . import utils


def test_is_ip():
    assert utils.is_ip("192.0.2.1")
    assert utils.is_ip("::1")
    assert not utils.is_ip("example.com")
