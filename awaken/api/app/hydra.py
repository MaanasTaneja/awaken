"""Persistent NPC memory backed by the HydraDB v2 Python SDK."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .config import settings


class HydraConfigurationError(RuntimeError):
    """Raised when the API cannot safely use its configured HydraDB tenant."""


_client: Any | None = None


def _get_client():
    global _client
    if not settings.hydra_db_api_key:
        raise HydraConfigurationError(
            "HYDRA_DB_API_KEY is required; the in-memory HydraDB fallback has been removed"
        )
    if not settings.hydra_tenant_id.strip():
        raise HydraConfigurationError("HYDRA_TENANT_ID must not be empty")
    if _client is None:
        from hydra_db import HydraDB

        _client = HydraDB(token=settings.hydra_db_api_key)
    return _client


def _sub_tenant_id(world_id: str, npc_id: str) -> str:
    """Keep every NPC's internal memories isolated inside the app tenant."""
    clean_world = "".join(c for c in world_id.lower() if c.isalnum() or c == "_")
    clean_npc = "".join(c for c in npc_id.lower() if c.isalnum() or c == "_")
    return f"world_{clean_world}__npc_{clean_npc}"


def validate_connection() -> None:
    """Fail startup when the configured tenant is missing or not ingest-ready."""
    client = _get_client()
    try:
        infra = client.tenants.status(tenant_id=settings.hydra_tenant_id).data.infra
    except Exception as exc:
        raise HydraConfigurationError(
            f"HydraDB tenant {settings.hydra_tenant_id!r} is unavailable. "
            "Create it before starting the API."
        ) from exc
    if not getattr(infra, "ready_for_ingestion", False):
        raise HydraConfigurationError(
            f"HydraDB tenant {settings.hydra_tenant_id!r} is still provisioning"
        )


def _memory_id(world_id: str, npc_id: str, memory: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "world_id": world_id,
            "npc_id": npc_id,
            "text": memory.get("text", ""),
            "source": memory.get("source", "simulation"),
        },
        sort_keys=True,
    )
    return f"awaken_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


def _wait_until_searchable(
    client: Any, sub_tenant_id: str | None, ids: list[str]
) -> None:
    deadline = time.monotonic() + settings.hydra_index_timeout_seconds
    while True:
        request = {"tenant_id": settings.hydra_tenant_id, "ids": ids}
        if sub_tenant_id is not None:
            request["sub_tenant_id"] = sub_tenant_id
        response = client.context.status(**request)
        statuses = response.data.statuses
        failed = [
            status
            for status in statuses
            if getattr(status, "indexing_status", None) in {"errored", "failed"}
        ]
        if failed:
            message = getattr(failed[0], "error_message", None) or "HydraDB indexing failed"
            raise RuntimeError(message)
        if statuses and all(
            getattr(status, "indexing_status", None) in {"graph_creation", "completed"}
            for status in statuses
        ):
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "HydraDB did not index memories within "
                f"{settings.hydra_index_timeout_seconds}s"
            )
        time.sleep(settings.hydra_index_poll_interval_seconds)


def store_memories(world_id: str, npc_id: str, memories: list[dict[str, Any]]) -> None:
    if not memories:
        return
    client = _get_client()
    sub_tenant_id = _sub_tenant_id(world_id, npc_id)
    payload = []
    for memory in memories:
        text = str(memory.get("text", "")).strip()
        if not text:
            continue
        payload.append(
            {
                "id": _memory_id(world_id, npc_id, memory),
                "title": f"NPC memory: {memory.get('source', 'simulation')}",
                "text": text,
                "infer": False,
                "additional_metadata": {
                    "world_id": world_id,
                    "npc_id": npc_id,
                    "source": memory.get("source", "simulation"),
                    "importance": float(memory.get("importance", 0.5)),
                },
            }
        )
    if not payload:
        return
    response = client.context.ingest(
        type="memory",
        tenant_id=settings.hydra_tenant_id,
        sub_tenant_id=sub_tenant_id,
        memories=json.dumps(payload),
    )
    ids = [result.id for result in response.data.results]
    if not ids:
        raise RuntimeError("HydraDB accepted the request but returned no ingestion IDs")
    _wait_until_searchable(client, sub_tenant_id, ids)


def clear_world_context(world_id: str, npc_ids: list[str], knowledge_ids: list[str]) -> None:
    """Wipe all HydraDB data for a world before re-seeding.

    - NPC memories are isolated per sub_tenant (UUID-based), so we delete each one.
    - World knowledge uses deterministic IDs that are passed in from _knowledge_sources().
    """
    client = _get_client()

    # Delete every NPC's private memory sub_tenant
    for npc_id in npc_ids:
        try:
            client.context.delete(
                tenant_id=settings.hydra_tenant_id,
                sub_tenant_id=_sub_tenant_id(world_id, npc_id),
                type="memory",
            )
        except Exception:
            pass  # sub_tenant may not exist on first run

    # Delete shared world knowledge by ID
    if knowledge_ids:
        try:
            client.context.delete(
                tenant_id=settings.hydra_tenant_id,
                ids=knowledge_ids,
                type="knowledge",
            )
        except Exception:
            pass


def store_world_knowledge(sources: list[dict[str, Any]]) -> list[str]:
    """Upsert canonical YAML world sources into HydraDB's knowledge collection."""
    if not sources:
        return []
    client = _get_client()
    response = client.context.ingest(
        type="knowledge",
        tenant_id=settings.hydra_tenant_id,
        app_knowledge=json.dumps(sources),
        upsert="true",
    )
    ids = [result.id for result in response.data.results]
    if not ids:
        raise RuntimeError("HydraDB accepted world knowledge but returned no ingestion IDs")
    _wait_until_searchable(client, None, ids)
    return ids


def _chunks_to_context(chunks: list[Any]) -> list[dict[str, Any]]:
    context = []
    for chunk in chunks:
        metadata = getattr(chunk, "additional_metadata", None) or {}
        context.append(
            {
                "text": chunk.chunk_content,
                "title": getattr(chunk, "source_title", None),
                "type": getattr(chunk, "source_type", None),
                "importance": float(metadata.get("importance", 0.5)),
                "source": metadata.get("source", getattr(chunk, "source_type", "hydradb")),
                "relevancy_score": getattr(chunk, "relevancy_score", None),
            }
        )
    return context


def recall_memories(
    world_id: str, npc_id: str, query: str, limit: int = 5
) -> list[dict[str, Any]]:
    client = _get_client()
    response = client.query(
        tenant_id=settings.hydra_tenant_id,
        sub_tenant_id=_sub_tenant_id(world_id, npc_id),
        query=query or "recent important experiences",
        type="memory",
        query_by="hybrid",
        mode="fast",
        max_results=limit,
        graph_context=False,
    )
    return _chunks_to_context(response.data.chunks)


def recall_context(
    world_id: str, npc_id: str, query: str, limit: int = 8
) -> list[dict[str, Any]]:
    """Retrieve shared world knowledge and this NPC's private memories together."""
    client = _get_client()
    response = client.query(
        tenant_id=settings.hydra_tenant_id,
        sub_tenant_id=_sub_tenant_id(world_id, npc_id),
        query=query,
        type="all",
        query_by="hybrid",
        mode="thinking",
        max_results=limit,
        graph_context=True,
    )
    return _chunks_to_context(response.data.chunks)
