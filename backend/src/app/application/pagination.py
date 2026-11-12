from dataclasses import dataclass


@dataclass(frozen=True)
class PageParams:
    limit: int = 20
    offset: int = 0


@dataclass
class Page[T]:
    items: list[T]
    total: int
    limit: int
    offset: int
