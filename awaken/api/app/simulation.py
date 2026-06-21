"""NPC sync loop: read unprocessed faction events + trusted friends' beliefs,
ask the LLM to form an updated belief, write it back to SQL, store narrative
memories in HydraDB, advance the cursor.
"""
from __future__ import annotations

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
        cur = models.NPCEventCursor(npc_id=npc_id, last_processed_event_id=0)
        db.add(cur)
        db.flush()
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


def friend_beliefs(db: Session, npc: models.NPC, top_k: int = 2, min_trust: float = 0.4):
    rels = list(
        db.scalars(
            select(models.NPCRelationship)
            .where(
                models.NPCRelationship.from_npc_id == npc.id,
                models.NPCRelationship.trust >= min_trust,
            )
            .order_by(models.NPCRelationship.trust.desc())
            .limit(top_k)
        )
    )
    out = []
    for r in rels:
        st = db.get(models.NPCPlayerState, (r.to_npc_id, "player_1"))
        if st is None:
            continue
        out.append(
            {
                "source_npc": r.to_npc_id,
                "trust": r.trust,
                "belief_summary": st.belief_summary,
            }
        )
    return out


def sync_npc(db: Session, npc_id: str, player_id: str = "player_1") -> dict[str, Any]:
    npc = db.get(models.NPC, npc_id)
    if npc is None:
        raise ValueError(f"NPC {npc_id} not found")
    faction = db.get(models.Faction, npc.faction_id)
    state = get_or_create_state(db, npc.id, player_id)
    cursor = get_or_create_cursor(db, npc.id)

    events = unprocessed_events(db, npc, cursor.last_processed_event_id)
    gossip = friend_beliefs(db, npc)

    event_dicts = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "target_id": e.target_id,
            "summary": e.summary,
            "importance": e.importance,
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

    update = form_npc_beliefs(
        npc={
            "name": npc.name,
            "role": npc.role,
            "behavior_prompt": npc.behavior_prompt,
        },
        faction={
            "name": faction.name if faction else "",
            "behavior_prompt": faction.behavior_prompt if faction else "",
        },
        current_state=current,
        events=event_dicts,
        gossip=gossip,
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

    hydra.store_memories(npc.world_id, npc.id, update.get("memories", []) or [])

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


# --------------------------------------------------------------------------- #
# Quest selection (deterministic)
# --------------------------------------------------------------------------- #

def select_quest_for_npc(
    db: Session, npc_id: str, player_id: str = "player_1"
) -> models.Quest | None:
    state = get_or_create_state(db, npc_id, player_id)
    assignments = list(
        db.scalars(select(models.NPCQuest).where(models.NPCQuest.npc_id == npc_id))
    )
    tags = set(state.belief_tags_json or [])

    eligible: list[tuple[models.Quest, models.NPCQuest]] = []
    for a in assignments:
        quest = db.get(models.Quest, a.quest_id)
        if quest is None:
            continue
        pq = db.get(models.PlayerQuest, (player_id, quest.id))
        if pq and pq.status == "COMPLETED":
            continue
        if quest.essential:
            eligible.append((quest, a))
            continue
        if state.affinity < a.minimum_affinity:
            continue
        if state.trust < a.minimum_trust:
            continue
        req = set(a.required_tags_json or [])
        blk = set(a.blocked_tags_json or [])
        if req and not req.issubset(tags):
            continue
        if blk & tags:
            continue
        eligible.append((quest, a))

    if not eligible:
        return None
    eligible.sort(key=lambda pair: (pair[0].essential, pair[0].priority), reverse=True)
    return eligible[0][0]
