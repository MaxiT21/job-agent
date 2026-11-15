"""URL fetching is user-controlled input: it must not reach internal hosts or hang on junk."""

import httpx
import pytest

from app import fetch
from app.fetch import FetchError, fetch_posting_text

BODY = "<p>" + "We are hiring a backend intern to build Python services with SQL. " * 5 + "</p>"
PAGE = f"<html><head><script>var secret=1</script></head><body><nav>Menu</nav>{BODY}</body></html>"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    hosts = {"jobs.example.com": ["93.184.216.34"], "internal.example.com": ["10.0.0.7"]}
    monkeypatch.setattr(fetch, "_resolve", lambda host: hosts.get(host, ["93.184.216.34"]))


def transport(handler):
    return httpx.MockTransport(handler)


def html(body: str, status: int = 200, **headers) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/html", **headers})


def test_extracts_visible_text():
    text = fetch_posting_text(
        "https://jobs.example.com/1", transport=transport(lambda r: html(PAGE))
    )
    assert text.startswith("We are hiring a backend intern")
    assert "secret" not in text
    assert "Menu" not in text


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://jobs.example.com/x", "jobs.example.com"]
)
def test_rejects_non_http(url):
    with pytest.raises(FetchError, match="http"):
        fetch_posting_text(url, transport=transport(lambda r: html(PAGE)))


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"])
def test_rejects_private_ip(monkeypatch, ip):
    monkeypatch.setattr(fetch, "_resolve", lambda host: [ip])
    with pytest.raises(FetchError, match="not allowed"):
        fetch_posting_text("http://jobs.example.com/", transport=transport(lambda r: html(PAGE)))


def test_rejects_redirect_to_private_host():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "jobs.example.com":
            return httpx.Response(302, headers={"location": "http://internal.example.com/admin"})
        return html(PAGE)

    with pytest.raises(FetchError, match="not allowed"):
        fetch_posting_text("https://jobs.example.com/1", transport=transport(handler))


def test_follows_redirect_to_public_host():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return html(PAGE)

    text = fetch_posting_text("https://jobs.example.com/old", transport=transport(handler))
    assert "backend intern" in text


def test_short_page_asks_to_paste():
    page = "<html><body><div id='root'></div><p>Loading...</p></body></html>"
    with pytest.raises(FetchError, match="(?i)paste"):
        fetch_posting_text("https://jobs.example.com/1", transport=transport(lambda r: html(page)))


def test_rejects_non_html():
    def handler(request):
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})

    with pytest.raises(FetchError, match="(?i)paste"):
        fetch_posting_text("https://jobs.example.com/1.pdf", transport=transport(handler))


def test_rejects_oversized_page():
    big = "<p>" + "x" * (3 * 1024 * 1024) + "</p>"
    with pytest.raises(FetchError, match="too large"):
        fetch_posting_text("https://jobs.example.com/1", transport=transport(lambda r: html(big)))


def test_http_error_status_is_reported():
    with pytest.raises(FetchError, match="404"):
        fetch_posting_text(
            "https://jobs.example.com/1", transport=transport(lambda r: html("", 404))
        )
