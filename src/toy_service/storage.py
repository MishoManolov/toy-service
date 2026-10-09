from __future__ import annotations

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
