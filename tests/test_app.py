from __future__ import annotations

import json

import pytest

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


def _post(app, payload: dict) -> tuple:  # type: ignore[no-untyped-def]
    return call(app, "POST", "/shorten", json.dumps(payload).encode())


def test_custom_alias_created_and_redirects() -> None:
    app = create_app(Shortener())
    status, _, data = _post(app, {"url": "https://example.com/x", "alias": "my-link"})
    assert status.startswith("201")
    assert data is not None
    assert data["code"] == "my-link"
    assert data["short_url"].endswith("/my-link")
    status, headers, _ = call(app, "GET", "/my-link")
    assert status.startswith("302")
    assert headers["Location"] == "https://example.com/x"


def test_duplicate_alias_is_409_and_original_resolves() -> None:
    app = create_app(Shortener())
    _post(app, {"url": "https://example.com/a", "alias": "dup"})
    status, _, data = _post(app, {"url": "https://example.com/b", "alias": "dup"})
    assert status.startswith("409")
    assert data == {"error": "alias taken"}
    _, headers, _ = call(app, "GET", "/dup")
    assert headers["Location"] == "https://example.com/a"


def test_invalid_alias_is_400() -> None:
    app = create_app(Shortener())
    for alias in ["bad alias", "", "a" * 33, "a/b", 123, ["x"], True]:
        status, _, data = _post(app, {"url": "https://example.com", "alias": alias})
        assert status.startswith("400"), alias
        assert data == {"error": "invalid alias"}


def test_no_alias_still_works() -> None:
    status, _, data = _post(create_app(Shortener()), {"url": "https://example.com"})
    assert status.startswith("201")
    assert data is not None
    assert data["code"]


@pytest.mark.parametrize(
    "body",
    [b"{not json", b"", b"[1, 2]", b'{"nope": 1}', b"\xff\xfe\x00", b'"text"', b"null"],
)
def test_bad_request_bodies_are_400(body: bytes) -> None:
    status, _, payload = call(create_app(Shortener()), "POST", "/shorten", body)
    assert status.startswith("400")
    assert payload == {"error": "invalid request"}
