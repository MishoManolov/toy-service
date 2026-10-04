from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any
from wsgiref.types import StartResponse, WSGIEnvironment

from toy_service.shortener import InvalidUrlError, Shortener, UnknownCodeError

WsgiApp = Callable[[WSGIEnvironment, StartResponse], Iterable[bytes]]


def _respond(
    start_response: StartResponse,
    status: str,
    body: dict[str, Any] | None = None,
    headers: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    payload = json.dumps(body).encode() if body is not None else b""
    out = [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))]
    start_response(status, out + (headers or []))
    return [payload]


def create_app(shortener: Shortener, base_url: str = "http://localhost:8000") -> WsgiApp:
    def shorten(environ: WSGIEnvironment, start_response: StartResponse) -> list[bytes]:
        size = int(environ.get("CONTENT_LENGTH") or 0)
        payload = json.loads(environ["wsgi.input"].read(size))
        try:
            link = shortener.shorten(payload["url"], payload.get("ttl"))
        except InvalidUrlError:
            return _respond(start_response, "400 Bad Request", {"error": "invalid url"})
        body = {"code": link.code, "short_url": f"{base_url}/{link.code}"}
        return _respond(start_response, "201 Created", body)

    def redirect(code: str, start_response: StartResponse) -> list[bytes]:
        try:
            url = shortener.resolve(code)
        except UnknownCodeError:
            return _respond(start_response, "404 Not Found", {"error": "unknown code"})
        return _respond(start_response, "302 Found", None, [("Location", url)])

    def app(environ: WSGIEnvironment, start_response: StartResponse) -> list[bytes]:
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
        if method == "POST" and path == "/shorten":
            return shorten(environ, start_response)
        if method == "GET" and path.count("/") == 1 and len(path) > 1:
            return redirect(path[1:], start_response)
        return _respond(start_response, "404 Not Found", {"error": "not found"})

    return app
