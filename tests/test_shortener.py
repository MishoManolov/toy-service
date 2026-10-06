from __future__ import annotations

import pytest

from toy_service.shortener import InvalidUrlError, Shortener, UnknownCodeError


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


def test_link_valid_just_before_ttl() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    clock.now += 9.9
    assert s.resolve(link.code) == "https://example.com"


def test_link_expires_at_exact_ttl() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    clock.now += 10
    with pytest.raises(UnknownCodeError):
        s.resolve(link.code)


def test_link_expires_well_after_ttl() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    clock.now += 100
    with pytest.raises(UnknownCodeError):
        s.resolve(link.code)
