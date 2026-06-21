"""LLM-backed belief updates and dialogue.

Both functions degrade gracefully when ``OPENAI_API_KEY`` is not set, so the
API works end-to-end out of the box (useful for local dev and CI). Swap the
stubs for real model calls when wiring an LLM provider.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


# --------------------------------------------------------------------------- #
# Belief update
# --------------------------------------------------------------------------- #

def form_npc_beliefs(
    *,
    npc: dict[str, Any],
    faction: dict[str, Any],
    current_state: dict[str, Any],
    events: list[dict[str, Any]],
    gossip: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a structured belief update for the NPC.

    Shape:
        {
          "affinity_delta": int,
          "trust_delta": int,
          "fear_delta": int,
          "respect_delta": int,
          "add_belief_tags": [str],
          "remove_belief_tags": [str],
          "belief_summary": str,
          "memories": [{text, importance, source}],
        }
    """
    if settings.openai_api_key:
        return _llm_form_beliefs(npc, faction, current_state, events, gossip)
    return _stub_form_beliefs(npc, current_state, events, gossip)


def _stub_form_beliefs(npc, current_state, events, gossip) -> dict[str, Any]:
    aff = trust = fear = respect = 0
    add_tags: list[str] = []
    memories: list[dict[str, Any]] = []

    for ev in events:
        t = ev.get("event_type", "")
        summary = ev.get("summary", "")
        if t == "ITEM_STOLEN":
            aff -= 15
            trust -= 20
            add_tags.append("PLAYER_MAY_BE_THIEF")
        elif t == "QUEST_COMPLETED":
            aff += 10
            trust += 8
            respect += 5
        elif t == "PLAYER_HELPED":
            aff += 8
            trust += 6
        elif t == "PLAYER_ATTACKED":
            aff -= 25
            fear += 15
            add_tags.append("PLAYER_IS_HOSTILE")
        memories.append(
            {"text": summary, "importance": ev.get("importance", 0.5), "source": "event"}
        )

    for g in gossip:
        weight = float(g.get("trust", 0)) * 0.5
        if "thief" in (g.get("belief_summary") or "").lower():
            trust -= int(10 * weight)
            add_tags.append("HEARSAY_THIEF")
        memories.append(
            {
                "text": f"Heard from a contact: {g.get('belief_summary','')}",
                "importance": 0.3,
                "source": "gossip",
            }
        )

    summary = (current_state.get("belief_summary") or "") or (
        f"{npc.get('name','The NPC')} has not yet formed strong opinions about the player."
    )
    if add_tags:
        summary = f"{npc.get('name','NPC')} now suspects: {', '.join(sorted(set(add_tags)))}."

    return {
        "affinity_delta": _clamp(aff, -20, 20),
        "trust_delta": _clamp(trust, -20, 20),
        "fear_delta": _clamp(fear, -20, 20),
        "respect_delta": _clamp(respect, -20, 20),
        "add_belief_tags": sorted(set(add_tags)),
        "remove_belief_tags": [],
        "belief_summary": summary,
        "memories": memories,
    }


def _llm_form_beliefs(npc, faction, current_state, events, gossip) -> dict[str, Any]:
    system = (
        "You update the internal beliefs of an RPG NPC. "
        "Return STRICT JSON only, no prose."
    )
    user = json.dumps(
        {
            "npc": {
                "name": npc.get("name"),
                "role": npc.get("role"),
                "behavior_prompt": npc.get("behavior_prompt"),
            },
            "faction": {
                "name": faction.get("name"),
                "behavior_prompt": faction.get("behavior_prompt"),
            },
            "current_state": current_state,
            "new_events": events,
            "hearsay": gossip,
            "schema": {
                "affinity_delta": "int in [-20,20]",
                "trust_delta": "int in [-20,20]",
                "fear_delta": "int in [-20,20]",
                "respect_delta": "int in [-20,20]",
                "add_belief_tags": "list[str]",
                "remove_belief_tags": "list[str]",
                "belief_summary": "str",
                "memories": "list[{text,importance,source}]",
            },
        }
    )
    data = _openai_json(system, user)
    # Defensive clamping happens at the caller too.
    for k in ("affinity_delta", "trust_delta", "fear_delta", "respect_delta"):
        data[k] = _clamp(int(data.get(k, 0)), -20, 20)
    data.setdefault("add_belief_tags", [])
    data.setdefault("remove_belief_tags", [])
    data.setdefault("belief_summary", "")
    data.setdefault("memories", [])
    return data


# --------------------------------------------------------------------------- #
# Dialogue
# --------------------------------------------------------------------------- #

def generate_dialogue(
    *,
    npc: dict[str, Any],
    faction: dict[str, Any],
    state: dict[str, Any],
    memories: list[dict[str, Any]],
    player_message: str | None,
    quest: dict[str, Any] | None,
) -> dict[str, Any]:
    if settings.openai_api_key:
        return _llm_generate_dialogue(npc, faction, state, memories, player_message, quest)
    return _stub_generate_dialogue(npc, state, player_message, quest)


def _tone_for(state: dict[str, Any]) -> str:
    aff = state.get("affinity", 0)
    fear = state.get("fear", 0)
    if fear >= 40:
        return "afraid"
    if aff >= 30:
        return "friendly"
    if aff <= -30:
        return "hostile"
    if aff <= -10:
        return "cold"
    return "neutral"


def _stub_generate_dialogue(npc, state, player_message, quest) -> dict[str, Any]:
    tone = _tone_for(state)
    name = npc.get("name", "The NPC")

    if player_message is None:
        opener = {
            "friendly": f"{name} smiles warmly. \"Ah, good to see you again.\"",
            "neutral": f"{name} nods. \"What brings you here?\"",
            "cold": f"{name} barely looks up. \"Make it quick.\"",
            "hostile": f"{name} glares. \"You. I had hoped never to see you again.\"",
            "afraid": f"{name} flinches. \"P–please, I want no trouble.\"",
        }[tone]
        dialogue = opener
    else:
        dialogue = {
            "friendly": f"\"Of course. {quest['title']}\" — happy to help." if quest else "\"Glad to talk.\"",
            "neutral": f"\"There is work: {quest['title']}.\"" if quest else "\"I have nothing for you.\"",
            "cold": f"\"Fine. {quest['title']}. Don't expect more.\"" if quest else "\"No work for the likes of you.\"",
            "hostile": f"\"I have no choice but to involve you. {quest['title']}.\"" if quest else "\"Leave.\"",
            "afraid": f"\"Just… just do this and go. {quest['title']}.\"" if quest else "\"Please leave me alone.\"",
        }[tone]

    return {
        "dialogue": dialogue,
        "tone": tone,
        "event_summary": f"The player spoke with {name}.",
        "mentioned_quest": quest is not None,
        "hints_provided": [],
    }


def _llm_generate_dialogue(npc, faction, state, memories, player_message, quest) -> dict[str, Any]:
    system = (
        "You are generating dialogue for an RPG NPC. You may alter tone, style, "
        "politeness, and optional hints. You may NOT change quest objectives, "
        "rewards, required locations, characters, essential quest availability, "
        "or established world facts. Return STRICT JSON only."
    )
    user = json.dumps(
        {
            "npc": npc,
            "faction": faction,
            "state": state,
            "memories": memories,
            "player_message": player_message,
            "quest": quest,
            "schema": {
                "dialogue": "str",
                "tone": "friendly|neutral|cold|hostile|afraid",
                "event_summary": "str",
                "mentioned_quest": "bool",
                "hints_provided": "list[str]",
            },
        }
    )
    return _openai_json(system, user)


# --------------------------------------------------------------------------- #
# OpenAI helper (chat completions, JSON mode)
# --------------------------------------------------------------------------- #

def _openai_json(system: str, user: str) -> dict[str, Any]:
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)
