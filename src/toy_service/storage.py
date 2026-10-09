from __future__ import annotations

import sqlite3
from types import TracebackType
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from toy_service.shortener import Link


class LinkStore(Protocol):
    def get(self, code: str) -> Link | None: ...

    def add(self, link: Link) -> bool:
        """Store the link; return False, without overwriting, if the code exists."""
        ...

    def record_hit(self, code: str) -> None: ...

    def delete(self, code: str) -> None: ...


class InMemoryLinkStore:
    def __init__(self) -> None:
        self._links: dict[str, Link] = {}

    def get(self, code: str) -> Link | None:
        return self._links.get(code)

    def add(self, link: Link) -> bool:
        if link.code in self._links:
            return False
        self._links[link.code] = link
        return True

    def record_hit(self, code: str) -> None:
        self._links[code].hits += 1

    def delete(self, code: str) -> None:
        self._links.pop(code, None)


MIGRATIONS: list[str] = [
    """
    CREATE TABLE links (
        code TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL,
        hits INTEGER NOT NULL DEFAULT 0
    )
    """,
]


class SqliteLinkStore:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, isolation_level=None)
        try:
            self._migrate()
        except BaseException:
            self._db.close()
            raise

    def _migrate(self) -> None:
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version > len(MIGRATIONS):
            raise RuntimeError(
                f"database schema version {version} is newer than supported "
                f"version {len(MIGRATIONS)}"
            )
        if version == len(MIGRATIONS):
            return
        self._db.execute("BEGIN IMMEDIATE")
        try:
            # Re-read inside the write lock in case another opener migrated.
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            for i in range(version, len(MIGRATIONS)):
                self._db.execute(MIGRATIONS[i])
            self._db.execute(f"PRAGMA user_version = {len(MIGRATIONS)}")
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    def get(self, code: str) -> Link | None:
        from toy_service.shortener import Link

        row = self._db.execute(
            "SELECT code, url, created_at, expires_at, hits FROM links WHERE code = ?",
            (code,),
        ).fetchone()
        return Link(*row) if row else None

    def add(self, link: Link) -> bool:
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO links (code, url, created_at, expires_at, hits) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (link.code, link.url, link.created_at, link.expires_at, link.hits),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def record_hit(self, code: str) -> None:
        with self._db:
            self._db.execute("UPDATE links SET hits = hits + 1 WHERE code = ?", (code,))

    def delete(self, code: str) -> None:
        with self._db:
            self._db.execute("DELETE FROM links WHERE code = ?", (code,))

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> SqliteLinkStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
