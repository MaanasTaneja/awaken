from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import hydra, models, schemas, simulation
from ..db import SessionLocal, get_db
from ..dialogue import generate_npc_response


router = APIRouter(prefix="/worlds/{world_id}/npcs/{npc_id}", tags=["interactions"])
TRACK_ORDER = ["greeting", "identity", "quest", "quest_status", "opinion", "world_lore"]


def _sync_npc_in_background(npc_id: str, player_id: str) -> None:
    """Run NPC belief sync after the response is sent, with its own DB session."""
    db = SessionLocal()
    try:
        simulation.sync_npc(db, npc_id, player_id)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _load_npc(db: Session, world_id: str, npc_id: str) -> models.NPC:
    npc = db.get(models.NPC, npc_id)
    if npc is None or npc.world_id != world_id:
        raise HTTPException(404, "npc not found")
    return npc


def _state_dict(state: models.NPCPlayerState) -> dict:
    return {
        "affinity": state.affinity,
        "trust": state.trust,
        "fear": state.fear,
        "respect": state.respect,
        "belief_tags": state.belief_tags_json or [],
        "belief_summary": state.belief_summary,
    }


def _npc_dict(npc: models.NPC) -> dict:
    return {
        "key": npc.stable_key,
        "name": npc.name,
        "role": npc.role,
        "behavioral_prompt": npc.behavior_prompt,
        "personality": npc.personality_json,
    }


def _faction_dict(faction: models.Faction | None) -> dict:
    return {
        "key": faction.stable_key if faction else "",
        "name": faction.name if faction else "",
        "description": faction.description if faction else "",
        "lore": faction.lore_json if faction else [],
        "beliefs": faction.beliefs_json if faction else {},
        "interpretation_prompt": faction.behavior_prompt if faction else "",
    }


def _quest_dict(quest: models.Quest) -> dict:
    return {
        "key": quest.stable_key,
        "title": quest.title,
        "description": quest.description,
        "objectives": (quest.objective_json or {}).get("steps", []),
        "essential": quest.essential,
        "base_dialogue": quest.base_dialogue or "",
        "hint": quest.base_hint,
    }


@router.get("/tracks", response_model=list[schemas.TrackOut])
def list_tracks(world_id: str, npc_id: str, db: Session = Depends(get_db)):
    npc = _load_npc(db, world_id, npc_id)
    return [
        schemas.TrackOut(id=track_id, **npc.tracks_json[track_id])
        for track_id in TRACK_ORDER
        if track_id in npc.tracks_json
    ]


@router.post("/interact", response_model=schemas.InteractionResponse)
async def interact(
    world_id: str,
    npc_id: str,
    body: schemas.InteractionRequest,
    debug: bool = Query(False),
    db: Session = Depends(get_db),
):
    npc = _load_npc(db, world_id, npc_id)
    faction = db.get(models.Faction, npc.faction_id)

    if body.track == "custom":
        if not body.custom_query or not body.custom_query.strip():
            raise HTTPException(400, "custom_query is required when track is 'custom'")
        track = {
            "player_text": body.custom_query.strip(),
            "guidance": "Answer freely based on your knowledge, memories, and beliefs about the player.",
        }
    else:
        track = npc.tracks_json.get(body.track)
        if track is None:
            raise HTTPException(400, "track is not configured for this NPC")

    # Log the interaction as a faction event so other NPCs can learn about it
    db.add(
        models.FactionEvent(
            world_id=world_id,
            faction_id=npc.faction_id,
            event_type="PLAYER_ASKED_TRACK",
            actor_id=body.player_id,
            target_npc_id=npc.id,
            visibility="DIRECT",
            summary=f"The player asked {npc.name} '{track['player_text']}'.",
            payload_json={"track_id": body.track},
            importance=0.4,
        )
    )
    db.commit()

    # Load state and quests before sync so we can build the recall query immediately.
    # We use the pre-sync belief_summary to enrich the recall query (minor trade-off:
    # one component of the query uses the previous summary, which is fine).
    state = simulation.get_or_create_state(db, npc.id, body.player_id)

    # Fetch quests first so their titles enrich the recall query
    all_quests = simulation.assigned_quests_for_npc(db, npc.id, body.player_id)
    essential_quests = [_quest_dict(q) for q in all_quests if q.essential]
    optional_quests = [_quest_dict(q) for q in all_quests if not q.essential]

    # Build a rich recall query: what was asked + NPC role + belief summary + quest topics
    recall_parts = [track["player_text"], f"{npc.name} {npc.role}"]
    if state.belief_summary:
        recall_parts.append(state.belief_summary)
    if all_quests:
        recall_parts.append(" ".join(q.title for q in all_quests))

    # Run sync_npc (own session/thread) and recall_context in parallel.
    # sync_npc commits its own changes; we refresh state afterwards to get fresh values.
    _, context = await asyncio.gather(
        asyncio.to_thread(_sync_npc_in_background, npc.id, body.player_id),
        asyncio.to_thread(hydra.recall_context, world_id, npc.id, " ".join(recall_parts), 12),
    )

    # Refresh state so the response and debug panel reflect the just-committed sync.
    db.refresh(state)
    state_payload = _state_dict(state)

    is_quest_track = body.track == "quest"
    is_status_track = body.track == "quest_status"

    # For quest_status: build a list of assigned quests with the player's current status
    quest_status_context = None
    if is_status_track:
        quest_status_context = []
        for q in all_quests:
            pq = db.get(models.PlayerQuest, (body.player_id, q.id))
            quest_status_context.append({
                **_quest_dict(q),
                "player_status": pq.status if pq else "NOT_STARTED",
            })

    # Single LLM call — NPC decides everything
    # Run in a thread so the blocking httpx call doesn't stall the event loop
    result = await asyncio.to_thread(
        generate_npc_response,
        track_id=body.track,
        track=track,
        npc=_npc_dict(npc),
        faction=_faction_dict(faction),
        player_state=state_payload,
        context=context,
        essential_quests=essential_quests if is_quest_track else [],
        optional_quests=optional_quests if is_quest_track else [],
        quest_status_context=quest_status_context,
    )

    # If the LLM offered a quest, record it in PlayerQuest
    offered_quest = None
    quest_key_offered = result.get("quest_offered")
    if quest_key_offered:
        matched = next((q for q in all_quests if q.stable_key == quest_key_offered), None)
        if matched:
            pq = db.get(models.PlayerQuest, (body.player_id, matched.id))
            if pq is None:
                pq = models.PlayerQuest(
                    player_id=body.player_id, quest_id=matched.id, status="OFFERED"
                )
                db.add(pq)
            offered_quest = schemas.TalkQuest(
                id=matched.id,
                title=matched.title,
                essential=matched.essential,
                status=pq.status,
            )

    conversation = models.Conversation(
        npc_id=npc.id,
        player_id=body.player_id,
        track_id=body.track,
        player_message=track["player_text"],
        npc_response=result["dialogue"],
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return schemas.InteractionResponse(
        session_id=conversation.id,
        npc_id=npc.id,
        track=body.track,
        dialogue=result["dialogue"],
        tone=result["tone"],
        quest=offered_quest,
        debug=(
            {
                **state_payload,
                "retrieved_context": context,
                "essential_quests": essential_quests,
                "optional_quests": optional_quests,
            }
            if debug
            else None
        ),
    )
