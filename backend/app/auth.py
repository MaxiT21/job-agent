"""Single-user auth: one password (APP_PASSWORD) → an HMAC-signed session cookie.

The cookie holds only an expiry timestamp and its signature; nothing secret is stored
client-side. Failed logins are throttled per client IP.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, SecretStr

from app.config import settings

__all__ = ["SecretStr", "make_token", "require_session", "router", "verify_token"]

log = logging.getLogger(__name__)
COOKIE = "session"
MAX_FREE_FAILURES = 5
MAX_WAIT_S = 300
_ephemeral_secret = secrets.token_hex(32)


def _secret() -> bytes:
    if settings.session_secret:
        return settings.session_secret.get_secret_value().encode()
    return _ephemeral_secret.encode()  # sessions reset when the server restarts


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(now: float) -> str:
    exp = str(int(now + settings.session_days * 86_400))
    return f"{exp}.{_sign(exp)}"


def verify_token(token: str, now: float) -> bool:
    exp, _, sig = token.partition(".")
    if not exp.isdigit() or not hmac.compare_digest(sig, _sign(exp)):
        return False
    return int(exp) > now


def _configured() -> None:
    if not settings.app_password:
        raise HTTPException(503, "APP_PASSWORD is not configured on the server")


def require_session(request: Request) -> None:
    """FastAPI dependency for every private endpoint."""
    _configured()
    token = request.cookies.get(COOKIE)
    if not token or not verify_token(token, time.time()):
        raise HTTPException(401, "Not logged in")


# ---------- throttling ----------


@dataclass
class _Failures:
    count: int = 0
    blocked_until: float = 0.0


_failures: dict[str, _Failures] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_throttle(ip: str, now: float) -> None:
    f = _failures.get(ip)
    if f and f.blocked_until > now:
        wait = int(f.blocked_until - now) + 1
        raise HTTPException(429, "Too many attempts", headers={"Retry-After": str(wait)})


def _record_failure(ip: str, now: float) -> None:
    f = _failures.setdefault(ip, _Failures())
    f.count += 1
    if f.count >= MAX_FREE_FAILURES:
        f.blocked_until = now + min(2 ** (f.count - MAX_FREE_FAILURES), MAX_WAIT_S)


def reset_throttle() -> None:
    _failures.clear()


# ---------- endpoints ----------

router = APIRouter(prefix="/auth", tags=["auth"])


class Login(BaseModel):
    password: SecretStr


class Me(BaseModel):
    authenticated: bool


@router.post("/login", status_code=204)
def login(body: Login, request: Request, response: Response) -> None:
    _configured()
    ip, now = _client_ip(request), time.time()
    _check_throttle(ip, now)
    expected = settings.app_password.get_secret_value().encode()
    if not hmac.compare_digest(body.password.get_secret_value().encode(), expected):
        _record_failure(ip, now)
        log.warning("failed login from %s", ip)
        raise HTTPException(401, "Wrong password")
    _failures.pop(ip, None)
    response.set_cookie(
        COOKIE,
        make_token(now),
        max_age=settings.session_days * 86_400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


@router.get("/me", response_model=Me)
def me(request: Request) -> Me:
    token = request.cookies.get(COOKIE)
    return Me(authenticated=bool(token and verify_token(token, time.time())))
