import pytest
from liara_guard.auth import AuthStore, hash_password, verify_password


def test_password_hash_and_session_roundtrip_no_plaintext_storage(tmp_path):
    value = hash_password("correct horse service watch")
    assert verify_password("correct horse service watch", value)
    assert not verify_password("wrong", value)
    auth = AuthStore(tmp_path / "state.sqlite", "s" * 32, value, clock=lambda: 100)
    cookie, owner = auth.login("correct horse service watch", "127.0.0.1")
    assert auth.resolve(cookie) == owner
    assert "correct horse" not in (tmp_path / "state.sqlite").read_bytes().decode(errors="ignore")
    auth.logout(cookie)
    with pytest.raises(ValueError):
        auth.resolve(cookie)


def test_invalid_signature_unicode_expiry_and_restart(tmp_path):
    now = [100]
    value = hash_password("password-long-enough")
    auth = AuthStore(tmp_path / "state.sqlite", "s" * 32, value, clock=lambda: now[0])
    cookie, owner = auth.login("password-long-enough", "a")
    for bad in [None, "bad", cookie + "x", "abc.سلام"]:
        with pytest.raises(ValueError):
            auth.resolve(bad)
    restarted = AuthStore(tmp_path / "state.sqlite", "s" * 32, value, clock=lambda: now[0])
    assert restarted.resolve(cookie) == owner
    now[0] += 86401
    with pytest.raises(ValueError):
        restarted.resolve(cookie)


def test_login_rate_limit_and_configuration_validation(tmp_path):
    value = hash_password("password-long-enough")
    a = AuthStore(tmp_path / "state.sqlite", "s" * 32, value, clock=lambda: 100)
    for _ in range(5):
        with pytest.raises(ValueError):
            a.login("wrong", "ip")
    with pytest.raises(ValueError, match="rate_limited"):
        a.login("password-long-enough", "ip")
    with pytest.raises(ValueError):
        AuthStore(tmp_path / "bad.sqlite", "short", value)
    with pytest.raises(ValueError):
        AuthStore(tmp_path / "bad.sqlite", "s" * 32, "plaintext")
