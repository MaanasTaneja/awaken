"""HydraDB memory store.

The official HydraDB SDK can be dropped in here. For the MVP we keep an
in-process fallback so the API runs end-to-end without external credentials.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import settings


class _InMemoryHydra:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def _key(self, world_id: str, npc_id: str) -> str:
        return f"{world_id}:{npc_id}"

    def store(self, world_id: str, npc_id: str, memories: list[dict[str, Any]]) -> None:
        for m in memories:
            self._store[self._key(world_id, npc_id)].append(m)

    def recall(
        self, world_id: str, npc_id: str, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        items = self._store.get(self._key(world_id, npc_id), [])
        q = (query or "").lower()
        scored = sorted(
            items,
            key=lambda m: (
                int(any(t in m.get("text", "").lower() for t in q.split())),
                m.get("importance", 0.0),
            ),
            reverse=True,
        )
        return scored[:limit]


_client = _InMemoryHydra()


def store_memories(world_id: str, npc_id: str, memories: list[dict[str, Any]]) -> None:
    if not memories:
        return
    # TODO: when settings.hydra_api_key is set, call the real SDK here.
    _client.store(world_id, npc_id, memories)


def recall_memories(
    world_id: str, npc_id: str, query: str, limit: int = 5
) -> list[dict[str, Any]]:
    return _client.recall(world_id, npc_id, query, limit)
