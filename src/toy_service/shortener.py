from __future__ import annotations

import secrets
import string
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
ALIAS_ALPHABET = ALPHABET + "-_"
MAX_ALIAS_LENGTH = 32


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
    ) -> None:
        self._links: dict[str, Link] = {}
        self._clock = clock
        self._code_factory = code_factory

    def shorten(self, url: str, ttl: float | None = None, alias: str | None = None) -> Link:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise InvalidUrlError(url)
        if alias is not None:
            if (
                not isinstance(alias, str)
                or not alias
                or len(alias) > MAX_ALIAS_LENGTH
                or any(c not in ALIAS_ALPHABET for c in alias)
            ):
                raise InvalidAliasError(alias)
            if alias in self._links:
                raise AliasTakenError(alias)
        now = self._clock()
        code = alias if alias is not None else self._code_factory()
        expires_at = now + ttl if ttl is not None else None
        link = Link(code, url, now, expires_at)
        self._links[code] = link
        return link

    def resolve(self, code: str) -> str:
        link = self._get(code)
        link.hits += 1
        if link.expires_at is not None and self._clock() > link.expires_at:
            raise UnknownCodeError(code)
        return link.url

    def stats(self, code: str) -> Link:
        return self._get(code)

    def delete(self, code: str) -> None:
        self._get(code)
        del self._links[code]

    def _get(self, code: str) -> Link:
        try:
            return self._links[code]
        except KeyError:
            raise UnknownCodeError(code) from None
