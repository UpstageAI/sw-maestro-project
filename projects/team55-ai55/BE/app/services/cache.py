from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar


T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class MemoryTTLCache(Generic[T]):
    def __init__(self):
        self._items: dict[Hashable, _CacheEntry[T]] = {}

    async def get(self, key: Hashable) -> T | None:
        item = self._items.get(key)
        if item is None:
            return None
        if item.expires_at < time.monotonic():
            self._items.pop(key, None)
            return None
        return item.value

    async def put(self, key: Hashable, value: T, ttl: int) -> None:
        self._items[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    async def find_analyze_by_hash(self, project_id: str, snapshot_hash: str) -> T | None:
        return await self.get(("analyze", project_id, snapshot_hash))


analyze_cache: MemoryTTLCache = MemoryTTLCache()
milestone_cache: MemoryTTLCache = MemoryTTLCache()
health_cache: MemoryTTLCache = MemoryTTLCache()

