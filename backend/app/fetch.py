"""Fetch a job posting from a URL, safely.

The URL comes from the user, so this is an SSRF surface once the API is deployed:
- only http(s);
- every hop (including redirects) must resolve to public IPs only;
- bounded size and time;
- pages that render client-side (too little text) are rejected with a hint to paste the text.

Known limit: DNS is resolved here and again by httpx (rebinding window). Acceptable for a
single-user tool; put the API behind an egress proxy if it ever becomes multi-tenant.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
MIN_TEXT_CHARS = 200
MAX_TEXT_CHARS = 20_000
TIMEOUT_S = 15.0
USER_AGENT = "job-agent/0.2"
PASTE_HINT = "Paste the posting text instead."


class FetchError(Exception):
    """A user-facing reason why the posting could not be fetched."""


def _resolve(host: str) -> list[str]:
    try:
        return [info[4][0] for info in socket.getaddrinfo(host, None)]
    except socket.gaierror as e:
        raise FetchError(f"Could not resolve {host}.") from e


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("Only http(s) URLs are supported.")
    for ip in _resolve(parts.hostname):
        if not ipaddress.ip_address(ip.split("%")[0]).is_global:
            raise FetchError(f"URLs pointing at private or local addresses are not allowed ({ip}).")


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg", "form"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())


def _download(client: httpx.Client, url: str) -> tuple[str, str]:
    """Follow redirects manually so every hop is checked. Returns (final_url, html)."""
    for _ in range(MAX_REDIRECTS + 1):
        _check_url(url)
        with client.stream("GET", url) as resp:
            if resp.is_redirect:
                url = urljoin(url, resp.headers["location"])
                continue
            if resp.status_code >= 400:
                raise FetchError(f"The page returned HTTP {resp.status_code}. {PASTE_HINT}")
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype and "text/plain" not in ctype:
                raise FetchError(
                    f"The URL is not a web page ({ctype or 'unknown type'}). {PASTE_HINT}"
                )
            body = bytearray()
            for chunk in resp.iter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    raise FetchError(f"The page is too large to read. {PASTE_HINT}")
            return url, body.decode(resp.encoding or "utf-8", errors="replace")
    raise FetchError(f"Too many redirects. {PASTE_HINT}")


def fetch_posting_text(url: str, *, transport: httpx.BaseTransport | None = None) -> str:
    try:
        with httpx.Client(
            timeout=TIMEOUT_S,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        ) as client:
            _, html = _download(client, url.strip())
    except httpx.HTTPError as e:
        raise FetchError(f"Could not fetch the page ({type(e).__name__}). {PASTE_HINT}") from e

    text = _visible_text(html)
    if len(text) < MIN_TEXT_CHARS:
        raise FetchError(
            f"The page has almost no readable text (it may load content with JavaScript). {PASTE_HINT}"
        )
    return text[:MAX_TEXT_CHARS]
