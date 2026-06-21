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

RESPONSE_SCHEMA = _object(
    {
        "dialogue": {"type": "string"},
        "tone": {
            "type": "string",
            "enum": ["warm", "neutral", "cold", "hostile", "afraid", "amused", "guarded"],
        },
        # stable_key of the quest the NPC chose to offer, or null if none offered
        "quest_offered": {"anyOf": [{"type": "string"}, {"type": "null"}]},
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
    historical_context: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _openai_structured(
        name="npc_belief_update",
        schema=BELIEF_SCHEMA,
        system=(
            "You are the private belief processor for an RPG NPC. Interpret events subjectively through "
            "the NPC's personality, faction worldview, existing beliefs, and trusted hearsay. Be willing "
            "to form surprising, biased, mistaken, forgiving, obsessive, or contradictory opinions when "
            "the full history supports them. "
            "CRITICAL RULES: "
            "(1) The NPC's behavioral_prompt describes personality traits and tendencies — it is NOT a description of what the player has already done. Do not infer tags or apply negative deltas based on the behavioral_prompt alone. "
            "(2) Do not invent patterns (e.g. 'repeated questions', 'persistence') from a single event. A pattern requires multiple events showing the same behaviour. "
            "(3) If there is only one neutral event (like a first greeting), deltas should be close to zero and no strong tags should be added. "
            "Deltas must each be between -20 and 20. Memories are subjective interpretations, not copies of every event. Never place output inside a schema or wrapper object."
        ),
        payload={
            "npc": npc,
            "faction": faction,
            "current_state": current_state,
            "new_events": events,
            "trusted_hearsay": gossip,
            "retrieved_history": historical_context,
        },
    )
    for key in ("affinity_delta", "trust_delta", "fear_delta", "respect_delta"):
        result[key] = _clamp(int(result[key]), -20, 20)
    for memory in result["memories"]:
        memory["importance"] = max(0.0, min(1.0, float(memory["importance"])))
    return result


def generate_npc_response(
    *,
    track_id: str,
    track: dict[str, Any],
    npc: dict[str, Any],
    faction: dict[str, Any],
    player_state: dict[str, Any],
    context: list[dict[str, Any]],
    essential_quests: list[dict[str, Any]],
    optional_quests: list[dict[str, Any]],
    quest_status_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Single LLM call that generates NPC dialogue.

    The LLM is given everything — NPC persona, faction, player beliefs,
    retrieved memories/lore — and responds freely. For essential quests the
    NPC MUST weave the base_dialogue into the response. For optional quests
    the NPC decides entirely based on its beliefs about the player.
    """
    quest_instructions: list[str] = []
    if essential_quests:
        lines = ["ESSENTIAL QUESTS (you MUST work each of these into your response, preserving all objectives and locations):"]
        for q in essential_quests:
            lines.append(
                f"  - [{q['key']}] {q['title']}: \"{q['base_dialogue']}\"\n"
                f"    Objectives: {q['objectives']}"
            )
        quest_instructions.append("\n".join(lines))
    if optional_quests:
        lines = ["OPTIONAL QUESTS (offer one ONLY if it genuinely fits how you feel about this player — you may ignore them entirely):"]
        for q in optional_quests:
            lines.append(
                f"  - [{q['key']}] {q['title']}: {q['description']}\n"
                f"    Objectives: {q['objectives']}"
            )
        quest_instructions.append("\n".join(lines))

    all_quest_keys = [q["key"] for q in essential_quests + optional_quests]
    quest_key_hint = (
        f"If you offer a quest, set quest_offered to its key (one of: {all_quest_keys}). "
        "Otherwise set quest_offered to null."
    ) if all_quest_keys else "Set quest_offered to null."

    # quest_status track: NPC reports on what's happened, never offers new quests
    if quest_status_context is not None:
        status_lines = ["ACTIVE QUESTS FOR STATUS REPORT (do NOT offer new quests — only report on progress):"]
        for q in quest_status_context:
            status_lines.append(
                f"  - [{q['key']}] {q['title']} (player status: {q['player_status']})\n"
                f"    Objectives: {q['objectives']}"
            )
        status_block = "\n".join(status_lines)
        system = (
            "You are an RPG NPC giving a status update on an active quest. "
            "Report on what the player has or hasn't done based solely on your memories and faction events — "
            "do NOT offer new quests. "
            "Respond in your character's voice. "
            "Do not invent lore not present in the retrieved context. "
            "LENGTH: ONE short paragraph, 2 to 4 sentences. "
            "End with a clear statement about where things stand (e.g. 'Bring it back when you have it.' / "
            "'The relic is returned. You have my grudging respect.').\n\n"
            + status_block
            + "\n\nSet quest_offered to null."
        )
        return _openai_structured(
            name="npc_response",
            schema=RESPONSE_SCHEMA,
            system=system,
            payload={
                "track_id": track_id,
                "track_definition": track,
                "npc": npc,
                "faction": faction,
                "player_state": player_state,
                "retrieved_world_knowledge_and_memories": context,
            },
        )

    has_quests = bool(essential_quests or optional_quests)
    quest_ending = (
        "Your final sentence MUST be a clear first-person decision about the quest: "
        "either committing to give it (e.g. 'I will give you this task.', 'Find the relic and bring it back.') "
        "or refusing it (e.g. 'I have nothing for you.', 'You are not ready for this.'). "
        "Do not ask a question or leave the quest outcome ambiguous."
    ) if has_quests else (
        "Do not end with a question. Close with a statement or a clear reaction."
    )

    system = (
        "You are an RPG NPC generating a single in-character response. "
        "Respond naturally based on your personality, your beliefs about the player, "
        "your faction's worldview, and everything you recall from memory and world knowledge. "
        "Your response may be warm, evasive, irritated, funny, hostile, frightened, biased, "
        "or unexpectedly compassionate — whatever the full context warrants. "
        "Do not invent canonical lore not present in the retrieved context. "
        "LENGTH: Keep it to ONE short paragraph — 2 to 4 sentences maximum. Do not ramble. "
        + quest_ending
        + ("\n\n" + "\n\n".join(quest_instructions) if quest_instructions else "")
        + f"\n\n{quest_key_hint}"
    )

    return _openai_structured(
        name="npc_response",
        schema=RESPONSE_SCHEMA,
        system=system,
        payload={
            "track_id": track_id,
            "track_definition": track,
            "npc": npc,
            "faction": faction,
            "player_state": player_state,
            "retrieved_world_knowledge_and_memories": context,
        },
    )
