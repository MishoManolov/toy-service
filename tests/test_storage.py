import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from toy_service import storage
from toy_service.shortener import Link
from toy_service.storage import InMemoryLinkStore, LinkStore, SqliteLinkStore


@pytest.fixture(params=["memory", "sqlite"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[LinkStore]:
    if request.param == "memory":
        yield InMemoryLinkStore()
    else:
        with SqliteLinkStore(str(tmp_path / "l.db")) as s:
            yield s


def test_get_missing(store: LinkStore) -> None:
    assert store.get("nope") is None


def test_add_and_get(store: LinkStore) -> None:
    assert store.add(Link("a", "http://x", 1.0, 5.0))
    assert store.get("a") == Link("a", "http://x", 1.0, 5.0, 0)


def test_add_duplicate_does_not_overwrite(store: LinkStore) -> None:
    store.add(Link("a", "http://x", 1.0))
    assert not store.add(Link("a", "http://y", 2.0))
    link = store.get("a")
    assert link is not None and link.url == "http://x"


def test_record_hit(store: LinkStore) -> None:
    store.add(Link("a", "http://x", 1.0))
    store.record_hit("a")
    store.record_hit("a")
    link = store.get("a")
    assert link is not None and link.hits == 2


def test_delete(store: LinkStore) -> None:
    store.add(Link("a", "http://x", 1.0))
    store.delete("a")
    store.delete("a")
    assert store.get("a") is None


def test_persists_across_instances(tmp_path: Path) -> None:
    path = str(tmp_path / "l.db")
    with SqliteLinkStore(path) as s:
        s.add(Link("a", "http://x", 1.0, 9.5))
        s.record_hit("a")
    with SqliteLinkStore(path) as s:
        assert s.get("a") == Link("a", "http://x", 1.0, 9.5, 1)


def test_reopen_does_not_rerun_migrations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = str(tmp_path / "l.db")
    SqliteLinkStore(path).close()
    # A non-idempotent migration would fail if applied again.
    monkeypatch.setattr(storage, "MIGRATIONS", list(storage.MIGRATIONS))
    with SqliteLinkStore(path) as s:
        assert s.get("a") is None


def test_new_migration_applied_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = str(tmp_path / "l.db")
    SqliteLinkStore(path).close()
    extra = [*storage.MIGRATIONS, "ALTER TABLE links ADD COLUMN note TEXT"]
    monkeypatch.setattr(storage, "MIGRATIONS", extra)
    SqliteLinkStore(path).close()
    SqliteLinkStore(path).close()
    db = sqlite3.connect(path)
    assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    db.close()


def test_newer_schema_rejected(tmp_path: Path) -> None:
    path = str(tmp_path / "l.db")
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version = 99")
    db.close()
    with pytest.raises(RuntimeError, match="newer"):
        SqliteLinkStore(path)
