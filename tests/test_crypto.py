import pytest

from better_dontforget.core import crypto
from better_dontforget.core.crypto import DecryptionError


def test_round_trip():
    payload = crypto.encrypt("hunter2", "my secret note")
    assert "hunter2" not in payload
    assert "my secret note" not in payload
    assert crypto.decrypt("hunter2", payload) == "my secret note"


def test_wrong_passphrase_fails():
    payload = crypto.encrypt("right", "secret")
    with pytest.raises(DecryptionError):
        crypto.decrypt("wrong", payload)


def test_plaintext_not_in_payload():
    payload = crypto.encrypt("pw", "topsecret")
    assert "topsecret" not in payload


def test_malformed_payload():
    with pytest.raises(DecryptionError):
        crypto.decrypt("pw", "not-a-valid-payload")
