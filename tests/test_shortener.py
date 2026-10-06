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


def test_alias_becomes_code() -> None:
    link = Shortener().shorten("https://example.com", alias="my-link_1")
    assert link.code == "my-link_1"


@pytest.mark.parametrize("n", [3, 32])
def test_alias_valid_boundaries(n: int) -> None:
    assert Shortener().shorten("https://example.com", alias="a" * n).code == "a" * n


@pytest.mark.parametrize("alias", ["a" * 2, "a" * 33, "", "bad alias", "a/b!", "abc\n", "héllo"])
def test_invalid_alias_rejected(alias: str) -> None:
    s = Shortener()
    with pytest.raises(InvalidAliasError):
        s.shorten("https://example.com", alias=alias)
    assert s._links == {}


def test_invalid_url_with_alias_stores_nothing() -> None:
    s = Shortener()
    with pytest.raises(InvalidUrlError):
        s.shorten("example.com", alias="good")
    assert s._links == {}


def test_duplicate_alias_raises() -> None:
    s = Shortener()
    first = s.shorten("https://example.com/a", alias="taken")
    with pytest.raises(AliasTakenError):
        s.shorten("https://example.com/b", alias="taken")
    assert s.resolve("taken") == first.url


def test_alias_equal_to_random_code_raises() -> None:
    s = Shortener(code_factory=lambda: "abc123")
    s.shorten("https://example.com/a")
    with pytest.raises(AliasTakenError):
        s.shorten("https://example.com/b", alias="abc123")


def test_expired_alias_still_taken() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    s.shorten("https://example.com", ttl=1, alias="gone")
    clock.now += 10
    with pytest.raises(AliasTakenError):
        s.shorten("https://example.com", alias="gone")


def test_code_factory_collision_retries() -> None:
    codes = iter(["dup", "dup", "fresh"])
    s = Shortener(code_factory=lambda: next(codes))
    first = s.shorten("https://example.com/a")
    second = s.shorten("https://example.com/b")
    assert (first.code, second.code) == ("dup", "fresh")
    assert s.resolve("dup") == "https://example.com/a"
