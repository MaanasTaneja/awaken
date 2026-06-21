"""NPC sync loop: read unprocessed faction events + configured relationships' beliefs,
ask the LLM to form an updated belief, write it back to SQL, store narrative
memories in HydraDB, advance the cursor.
"""
from __future__ import annotations

import threading
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import hydra, models
from .dialogue import form_npc_beliefs


def _clamp(v: int, lo: int = -100, hi: int = 100) -> int:
    return max(lo, min(hi, v))


def get_or_create_state(db: Session, npc_id: str, player_id: str = "player_1") -> models.NPCPlayerState:
    state = db.get(models.NPCPlayerState, (npc_id, player_id))
    if state is None:
        state = models.NPCPlayerState(npc_id=npc_id, player_id=player_id)
        db.add(state)
        db.flush()
    return state


def get_or_create_cursor(db: Session, npc_id: str) -> models.NPCEventCursor:
    cur = db.get(models.NPCEventCursor, npc_id)
    if cur is None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(models.NPCEventCursor).values(
            npc_id=npc_id, last_processed_event_id=0
        ).on_conflict_do_nothing(index_elements=["npc_id"])
        db.execute(stmt)
        db.flush()
        cur = db.get(models.NPCEventCursor, npc_id)
    return cur


def unprocessed_events(
    db: Session, npc: models.NPC, after_id: int, limit: int = 20
) -> list[models.FactionEvent]:
    stmt = (
        select(models.FactionEvent)
        .where(
            models.FactionEvent.faction_id == npc.faction_id,
            models.FactionEvent.id > after_id,
            or_(
                models.FactionEvent.visibility == "PUBLIC",
                models.FactionEvent.target_npc_id == npc.id,
            ),
        )
        .order_by(models.FactionEvent.id.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def relationship_beliefs(db: Session, npc: models.NPC, player_id: str):
    """Return hearsay only from explicitly authored directed relationships.

    There is deliberately no trust cutoff or top-k rule here. Relationship type,
    trust, and affinity are context for the belief model, which decides whether
    this NPC accepts, doubts, resents, or ignores what the other NPC believes.
    """
    # Single JOIN query instead of N+1 individual lookups
    stmt = (
        select(models.NPCRelationship, models.NPCPlayerState, models.NPC)
        .outerjoin(
            models.NPCPlayerState,
            (models.NPCPlayerState.npc_id == models.NPCRelationship.to_npc_id)
            & (models.NPCPlayerState.player_id == player_id),
        )
        .outerjoin(models.NPC, models.NPC.id == models.NPCRelationship.to_npc_id)
        .where(models.NPCRelationship.from_npc_id == npc.id)
        .order_by(models.NPCRelationship.trust.desc())
    )
    out = []
    for r, st, source_npc in db.execute(stmt):
        if st is None or not st.belief_summary:
            continue
        out.append(
            {
                "source_npc_id": r.to_npc_id,
                "source_npc_name": source_npc.name if source_npc else r.to_npc_id,
                "relationship_type": r.relationship_type,
                "trust": r.trust,
                "affinity": r.affinity,
                "belief_summary": st.belief_summary,
                "belief_tags": st.belief_tags_json or [],
            }
        )
    return out


def sync_npc(db: Session, npc_id: str, player_id: str = "player_1") -> dict[str, Any]:
    npc = db.get(models.NPC, npc_id)
    if npc is None:
        raise ValueError(f"NPC {npc_id} not found")
    faction = db.get(models.Faction, npc.faction_id)
    world = db.get(models.World, npc.world_id)
    state = get_or_create_state(db, npc.id, player_id)
    cursor = get_or_create_cursor(db, npc.id)

    events = unprocessed_events(db, npc, cursor.last_processed_event_id)
    gossip = relationship_beliefs(db, npc, player_id)

    event_dicts = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "target_id": e.target_id,
            "summary": e.summary,
            "importance": e.importance,
            "payload": e.payload_json or {},
            "interpretation_guidance": (
                ((world.lore_json or {}).get("event_rules") or {})
                .get(e.event_type, {})
                .get("interpretation_guidance", "")
                if world
                else ""
            ),
        }
        for e in events
    ]
    current = {
        "affinity": state.affinity,
        "trust": state.trust,
        "fear": state.fear,
        "respect": state.respect,
        "belief_tags": list(state.belief_tags_json or []),
        "belief_summary": state.belief_summary,
    }

    if not events and not gossip:
        return {"npc_id": npc.id, "events_processed": 0, "state": current}

    # Objective episodic memory never depends on model behavior. Stable Hydra IDs
    # make retries idempotent if interpretation fails later in this sync.
    hydra.store_memories(
        npc.world_id,
        npc.id,
        [
            {
                "text": event["summary"],
                "importance": event["importance"],
                "source": f"observed_event:{event['id']}",
            }
            for event in event_dicts
        ],
    )
    historical_context = hydra.recall_context(
        npc.world_id,
        npc.id,
        " ".join(event["summary"] for event in event_dicts)
        or state.belief_summary
        or "the player's history with this NPC",
        limit=8,
    )

    update = form_npc_beliefs(
        npc={
            "key": npc.stable_key,
            "name": npc.name,
            "role": npc.role,
            "behavior_prompt": npc.behavior_prompt,
            "personality": npc.personality_json,
        },
        faction={
            "name": faction.name if faction else "",
            "behavior_prompt": faction.behavior_prompt if faction else "",
            "beliefs": faction.beliefs_json if faction else {},
            "lore": faction.lore_json if faction else [],
        },
        current_state=current,
        events=event_dicts,
        gossip=gossip,
        historical_context=historical_context,
    )

    state.affinity = _clamp(state.affinity + int(update.get("affinity_delta", 0)))
    state.trust = _clamp(state.trust + int(update.get("trust_delta", 0)))
    state.fear = _clamp(state.fear + int(update.get("fear_delta", 0)), 0, 100)
    state.respect = _clamp(state.respect + int(update.get("respect_delta", 0)))

    tags = set(state.belief_tags_json or [])
    tags.update(update.get("add_belief_tags", []) or [])
    tags.difference_update(update.get("remove_belief_tags", []) or [])
    state.belief_tags_json = sorted(tags)
    if update.get("belief_summary"):
        state.belief_summary = update["belief_summary"]

    if events:
        cursor.last_processed_event_id = events[-1].id

    # Belief memories are only needed by future syncs — store asynchronously so we
    # don't block this sync waiting for HydraDB to finish indexing them.
    threading.Thread(
        target=hydra.store_memories,
        args=(npc.world_id, npc.id, update["memories"]),
        daemon=True,
    ).start()

    db.flush()
    return {
        "npc_id": npc.id,
        "events_processed": len(events),
        "state": {
            "affinity": state.affinity,
            "trust": state.trust,
            "fear": state.fear,
            "respect": state.respect,
            "belief_tags": state.belief_tags_json,
            "belief_summary": state.belief_summary,
        },
    }


def assigned_quests_for_npc(
    db: Session, npc_id: str, player_id: str = "player_1"
) -> list[models.Quest]:
    """Return all quests assigned to this NPC, excluding ones the player has already completed."""
    # Single JOIN query instead of 1+2N individual lookups
    stmt = (
        select(models.Quest, models.PlayerQuest)
        .join(models.NPCQuest, models.NPCQuest.quest_id == models.Quest.id)
        .outerjoin(
            models.PlayerQuest,
            (models.PlayerQuest.quest_id == models.Quest.id)
            & (models.PlayerQuest.player_id == player_id),
        )
        .where(models.NPCQuest.npc_id == npc_id)
    )
    quests = []
    for quest, pq in db.execute(stmt):
        if pq is not None and pq.status == "COMPLETED":
            continue
        quests.append(quest)
    quests.sort(key=lambda q: (q.essential, q.priority), reverse=True)
    return quests
