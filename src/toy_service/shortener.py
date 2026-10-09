from __future__ import annotations

import secrets
import string
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from toy_service.storage import InMemoryLinkStore, LinkStore

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
ALIAS_ALPHABET = ALPHABET + "-_"
MIN_ALIAS_LENGTH = 3
MAX_ALIAS_LENGTH = 32
MAX_CODE_ATTEMPTS = 10


class InvalidUrlError(ValueError):
    pass


class UnknownCodeError(KeyError):
    pass


class InvalidAliasError(ValueError):
    pass


class AliasTakenError(ValueError):
    pass


@dataclass
class Link:
    code: str
    url: str
    created_at: float
    expires_at: float | None = None
    hits: int = 0


def random_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


class Shortener:
    def __init__(
        self,
        clock: Callable[[], float] = time.time,
        code_factory: Callable[[], str] = random_code,
        store: LinkStore | None = None,
    ) -> None:
        self._store: LinkStore = store if store is not None else InMemoryLinkStore()
        self._clock = clock
        self._code_factory = code_factory

    @property
    def _links(self) -> dict[str, Link]:
        # Kept for tests that inspect the in-memory store directly.
        return getattr(self._store, "_links", {})

    def shorten(self, url: str, ttl: float | None = None, alias: str | None = None) -> Link:
        if isinstance(url, str):
            url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise InvalidUrlError(url)
        if alias is not None:
            if (
                not isinstance(alias, str)
                or len(alias) < MIN_ALIAS_LENGTH
                or len(alias) > MAX_ALIAS_LENGTH
                or any(c not in ALIAS_ALPHABET for c in alias)
            ):
                raise InvalidAliasError(alias)
        now = self._clock()
        expires_at = now + ttl if ttl is not None else None
        if alias is not None:
            link = Link(alias, url, now, expires_at)
            if not self._store.add(link):
                raise AliasTakenError(alias)
            return link
        for _ in range(MAX_CODE_ATTEMPTS):
            link = Link(self._code_factory(), url, now, expires_at)
            if self._store.add(link):
                return link
        raise RuntimeError("could not generate a unique code")

    def resolve(self, code: str) -> str:
        link = self._get(code)
        if link.expires_at is not None and self._clock() >= link.expires_at:
            raise UnknownCodeError(code)
        self._store.record_hit(code)
        return link.url

    def stats(self, code: str) -> Link:
        link = self._get(code)
        if link.expires_at is not None and self._clock() >= link.expires_at:
            raise UnknownCodeError(code)
        return link

    def delete(self, code: str) -> None:
        self._get(code)
        self._store.delete(code)

    def _get(self, code: str) -> Link:
        link = self._store.get(code)
        if link is None:
            raise UnknownCodeError(code)
        return link
