"""Strictly structured belief interpretation and track-based NPC dialogue."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": False,
    }


MEMORY_SCHEMA = _object(
    {
        "text": {"type": "string"},
        "importance": {"type": "number"},
        "source": {"type": "string"},
    }
)

BELIEF_SCHEMA = _object(
    {
        "affinity_delta": {"type": "integer"},
        "trust_delta": {"type": "integer"},
        "fear_delta": {"type": "integer"},
        "respect_delta": {"type": "integer"},
        "add_belief_tags": {"type": "array", "items": {"type": "string"}},
        "remove_belief_tags": {"type": "array", "items": {"type": "string"}},
        "belief_summary": {"type": "string"},
        "memories": {"type": "array", "items": MEMORY_SCHEMA},
    }
)

QUEST_DECISION_SCHEMA = _object(
    {
        "decision": {"type": "string", "enum": ["OFFER", "REFUSE"]},
        "reason": {"type": "string"},
    }
)

DIALOGUE_SCHEMA = _object(
    {
        "dialogue": {"type": "string"},
        "tone": {
            "type": "string",
            "enum": ["warm", "neutral", "cold", "hostile", "afraid", "amused", "guarded"],
        },
        "event_summary": {"type": "string"},
        "hints_provided": {"type": "array", "items": {"type": "string"}},
    }
)


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _openai_structured(
    *, name: str, schema: dict[str, Any], system: str, payload: dict[str, Any]
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for emergent belief and dialogue generation")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload)},
            ],
        },
        timeout=60.0,
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    if message.get("refusal"):
        raise RuntimeError(f"Model refused structured generation: {message['refusal']}")
    return json.loads(message["content"])


def form_npc_beliefs(
    *,
    npc: dict[str, Any],
    faction: dict[str, Any],
    current_state: dict[str, Any],
    events: list[dict[str, Any]],
    gossip: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _openai_structured(
        name="npc_belief_update",
        schema=BELIEF_SCHEMA,
        system=(
            "You are the private belief processor for an RPG NPC. Interpret events subjectively through "
            "the NPC's personality, faction worldview, existing beliefs, and trusted hearsay. Be willing "
            "to form surprising, biased, mistaken, forgiving, obsessive, or contradictory opinions when "
            "the context supports them. Repeated questions may cause affection, suspicion, amusement, or "
            "anger. Deltas must each be between -20 and 20. Memories are subjective interpretations, not "
            "copies of every event. Never place output inside a schema or wrapper object."
        ),
        payload={
            "npc": npc,
            "faction": faction,
            "current_state": current_state,
            "new_events": events,
            "trusted_hearsay": gossip,
        },
    )
    for key in ("affinity_delta", "trust_delta", "fear_delta", "respect_delta"):
        result[key] = _clamp(int(result[key]), -20, 20)
    for memory in result["memories"]:
        memory["importance"] = max(0.0, min(1.0, float(memory["importance"])))
    return result


def decide_optional_quest(
    *,
    npc: dict[str, Any],
    faction: dict[str, Any],
    state: dict[str, Any],
    context: list[dict[str, Any]],
    quest: dict[str, Any],
    guidance: str,
) -> dict[str, str]:
    return _openai_structured(
        name="optional_quest_decision",
        schema=QUEST_DECISION_SCHEMA,
        system=(
            "Decide whether this NPC willingly entrusts the player with an optional quest. This is a "
            "subjective character decision, not a numeric threshold check. Use personality, faction, "
            "beliefs, memories, hearsay, risk, and quest sensitivity. Return OFFER or REFUSE and the NPC's reason."
        ),
        payload={
            "npc": npc,
            "faction": faction,
            "player_state": state,
            "retrieved_context": context,
            "quest": quest,
            "npc_specific_guidance": guidance,
        },
    )


def generate_track_dialogue(
    *,
    track_id: str,
    track: dict[str, Any],
    npc: dict[str, Any],
    faction: dict[str, Any],
    state: dict[str, Any],
    context: list[dict[str, Any]],
    repeat_count: int,
    quest_decision: str | None,
    quest_reason: str | None,
    protected_base_statement: str | None,
    protected_quest_facts: dict[str, Any] | None,
) -> dict[str, Any]:
    return _openai_structured(
        name="npc_track_dialogue",
        schema=DIALOGUE_SCHEMA,
        system=(
            "Generate one in-character RPG NPC response for the selected interaction track. The response "
            "should feel emergent and may be warm, evasive, irritated, funny, hostile, frightened, biased, "
            "or unexpectedly compassionate. Ground it in retrieved world knowledge and private memories. "
            "The player selected a fixed track; do not answer a different track. If a protected base statement "
            "is supplied, preserve its quest decision, objectives, people, items, and locations exactly while "
            "personalizing how the NPC delivers it. Never reverse OFFER, REFUSE, ACTIVE, or COMPLETED lifecycle "
            "state, and never describe a completed quest as unfinished. Repetition count matters: the "
            "NPC can explicitly react to being asked again according to personality. Do not invent canonical lore."
        ),
        payload={
            "track_id": track_id,
            "track_definition": track,
            "repeat_count": repeat_count,
            "npc": npc,
            "faction": faction,
            "player_state": state,
            "retrieved_world_knowledge_and_memories": context,
            "quest_decision": quest_decision,
            "quest_reason": quest_reason,
            "protected_base_statement": protected_base_statement,
            "protected_quest_facts": protected_quest_facts,
        },
    )
