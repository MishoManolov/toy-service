from __future__ import annotations

import pytest

from toy_service.shortener import (
    AliasTakenError,
    InvalidAliasError,
    InvalidUrlError,
    Shortener,
    UnknownCodeError,
)


class Clock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_shorten_and_resolve() -> None:
    s = Shortener()
    link = s.shorten("https://example.com/a")
    assert s.resolve(link.code) == "https://example.com/a"


def test_missing_scheme_rejected() -> None:
    with pytest.raises(InvalidUrlError):
        Shortener().shorten("example.com")


def test_unknown_code() -> None:
    with pytest.raises(UnknownCodeError):
        Shortener().resolve("nope")


def test_delete() -> None:
    s = Shortener()
    link = s.shorten("https://example.com")
    s.delete(link.code)
    with pytest.raises(UnknownCodeError):
        s.resolve(link.code)


def test_hits_are_counted() -> None:
    s = Shortener()
    link = s.shorten("https://example.com")
    s.resolve(link.code)
    s.resolve(link.code)
    assert s.stats(link.code).hits == 2


def test_link_expires_well_after_ttl() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    clock.now += 100
    with pytest.raises(UnknownCodeError):
        s.resolve(link.code)


def test_alias_used_as_code_and_resolves() -> None:
    s = Shortener()
    link = s.shorten("https://example.com/a", alias="my-link_1")
    assert link.code == "my-link_1"
    assert s.resolve("my-link_1") == "https://example.com/a"


def test_duplicate_alias_raises_and_keeps_original() -> None:
    s = Shortener()
    s.shorten("https://example.com/a", alias="taken")
    with pytest.raises(AliasTakenError):
        s.shorten("https://example.com/b", alias="taken")
    assert s.resolve("taken") == "https://example.com/a"


def test_expired_alias_is_still_taken() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    s.shorten("https://example.com/a", ttl=10, alias="old")
    clock.now += 100
    with pytest.raises(AliasTakenError):
        s.shorten("https://example.com/b", alias="old")
    assert s.stats("old").url == "https://example.com/a"


@pytest.mark.parametrize("alias", ["", "has space", "a/b", "ünï", "x" * 33])
def test_invalid_alias_rejected(alias: str) -> None:
    with pytest.raises(InvalidAliasError):
        Shortener().shorten("https://example.com", alias=alias)


def test_non_string_alias_rejected() -> None:
    with pytest.raises(InvalidAliasError):
        Shortener().shorten("https://example.com", alias=123)  # type: ignore[arg-type]


def test_no_alias_uses_code_factory() -> None:
    s = Shortener(code_factory=lambda: "gen123")
    assert s.shorten("https://example.com").code == "gen123"
