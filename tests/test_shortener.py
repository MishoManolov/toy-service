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


def test_link_expires_at_exact_ttl_moment() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    clock.now += 10
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


@pytest.mark.parametrize("alias", ["", "a", "ab", "has space", "a/b", "ünï", "x" * 33])
def test_invalid_alias_rejected(alias: str) -> None:
    with pytest.raises(InvalidAliasError):
        Shortener().shorten("https://example.com", alias=alias)


@pytest.mark.parametrize("alias", ["abc", "x" * 32])
def test_alias_length_boundaries_accepted(alias: str) -> None:
    assert Shortener().shorten("https://example.com", alias=alias).code == alias


def test_non_string_alias_rejected() -> None:
    with pytest.raises(InvalidAliasError):
        Shortener().shorten("https://example.com", alias=123)  # type: ignore[arg-type]


def test_no_alias_uses_code_factory() -> None:
    s = Shortener(code_factory=lambda: "gen123")
    assert s.shorten("https://example.com").code == "gen123"


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "file:///etc/passwd", "http://", "https:///path", "ftp://example.com"],
)
def test_non_web_url_rejected(url: str) -> None:
    with pytest.raises(InvalidUrlError):
        Shortener().shorten(url)


def test_surrounding_whitespace_is_stripped() -> None:
    s = Shortener()
    link = s.shorten(" \thttps://example.com/a \n")
    assert link.url == "https://example.com/a"
    assert s.resolve(link.code) == "https://example.com/a"


def test_collision_in_random_code_keeps_first_link() -> None:
    """When code_factory returns a code already in use, both links should work."""
    codes = ["ABC123", "ABC123", "XYZ789"]  # Collision on second call
    code_iter = iter(codes)

    def fixed_code_factory() -> str:
        return next(code_iter)

    s = Shortener(code_factory=fixed_code_factory)
    link1 = s.shorten("https://example.com/first")
    link2 = s.shorten("https://example.com/second")

    # Both links should work; link1 should keep the original code
    assert link1.code == "ABC123"
    assert link1.url == "https://example.com/first"
    assert s.resolve("ABC123") == "https://example.com/first"

    # link2 should get a different code (regenerated after collision)
    assert link2.code == "XYZ789"
    assert link2.url == "https://example.com/second"
    assert s.resolve("XYZ789") == "https://example.com/second"


def test_expired_link_does_not_count_hits() -> None:
    clock = Clock()
    s = Shortener(clock=clock)
    link = s.shorten("https://example.com", ttl=10)
    # Resolve before expiration - should count as hit
    s.resolve(link.code)
    assert s.stats(link.code).hits == 1
    # Advance past expiration
    clock.now += 10
    # Try to resolve - should raise UnknownCodeError
    with pytest.raises(UnknownCodeError):
        s.resolve(link.code)
    # Hit count should still be 1, not 2
    assert s.stats(link.code).hits == 1
