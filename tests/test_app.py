from __future__ import annotations

import json

from tests.helpers import call
from toy_service.app import create_app
from toy_service.shortener import Shortener


def test_create_and_redirect() -> None:
    app = create_app(Shortener())
    body = json.dumps({"url": "https://example.com/x"}).encode()
    status, _, data = call(app, "POST", "/shorten", body)
    assert status.startswith("201")
    assert data is not None
    status, headers, _ = call(app, "GET", f"/{data['code']}")
    assert status.startswith("302")
    assert headers["Location"] == "https://example.com/x"


def test_unknown_code_is_404() -> None:
    status, _, _ = call(create_app(Shortener()), "GET", "/missing")
    assert status.startswith("404")


def test_invalid_url_is_400() -> None:
    body = json.dumps({"url": "nope"}).encode()
    status, _, _ = call(create_app(Shortener()), "POST", "/shorten", body)
    assert status.startswith("400")


def test_empty_body_is_400() -> None:
    status, _, _ = call(create_app(Shortener()), "POST", "/shorten", b"")
    assert status.startswith("400")
