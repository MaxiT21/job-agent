"""Single-user password auth: the only door to the private app."""

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import app

PASSWORD = "correct horse battery staple"


@pytest.fixture
def anon(monkeypatch):
    monkeypatch.setattr(settings, "app_password", auth.SecretStr(PASSWORD))
    monkeypatch.setattr(settings, "session_secret", auth.SecretStr("s" * 32))
    return TestClient(app)


def login(client, password=PASSWORD):
    return client.post("/auth/login", json={"password": password})


def test_login_sets_httponly_cookie(anon):
    r = login(anon)
    assert r.status_code == 204
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("session=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert anon.get("/auth/me").json() == {"authenticated": True}


def test_wrong_password_401(anon):
    assert login(anon, "nope").status_code == 401
    assert anon.get("/auth/me").json() == {"authenticated": False}


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/runs/x"), ("post", "/runs"), ("get", "/applications"), ("get", "/runs/x/files/cv")],
)
def test_protected_endpoints_require_session(anon, method, path):
    assert getattr(anon, method)(path).status_code == 401


def test_health_is_public(anon):
    assert anon.get("/health").status_code == 200


def test_tampered_or_expired_token_rejected(anon):
    token = auth.make_token(now=1_000.0)
    exp, sig = token.split(".")
    assert auth.verify_token(token, now=1_001.0)
    assert not auth.verify_token(f"{int(exp) + 999}.{sig}", now=1_001.0)  # tampered expiry
    assert not auth.verify_token(token, now=float(exp) + 1)  # expired
    assert not auth.verify_token("garbage", now=1_001.0)


def test_throttle_after_five_failures(anon):
    for _ in range(5):
        assert login(anon, "wrong").status_code == 401
    r = login(anon)  # even the right password waits
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


def test_no_password_configured_503(anon, monkeypatch):
    monkeypatch.setattr(settings, "app_password", None)
    assert login(anon).status_code == 503
    assert anon.get("/applications").status_code == 503


def test_logout_clears_cookie(anon):
    login(anon)
    anon.post("/auth/logout")
    assert anon.get("/auth/me").json() == {"authenticated": False}
    assert anon.get("/applications").status_code == 401
