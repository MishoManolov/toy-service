from __future__ import annotations

import json
from pathlib import Path

from tests.helpers import call
from toy_service.app import create_app
from toy_service.shortener import Shortener
from toy_service.storage import SqliteLinkStore


def test_links_survive_restart(tmp_path: Path) -> None:
    db = str(tmp_path / "links.db")
    url = "https://example.com/x"
    with SqliteLinkStore(db) as store:
        app = create_app(Shortener(store=store))
        _, _, gen = call(app, "POST", "/shorten", json.dumps({"url": url}).encode())
        body = json.dumps({"url": url, "alias": "my-alias"}).encode()
        call(app, "POST", "/shorten", body)
    assert gen is not None
    with SqliteLinkStore(db) as store:
        app = create_app(Shortener(store=store))
        for code in (gen["code"], "my-alias"):
            status, headers, _ = call(app, "GET", f"/{code}")
            assert status.startswith("302")
            assert headers["Location"] == url
        status, _, _ = call(app, "POST", "/shorten", body)
        assert status.startswith("409")
