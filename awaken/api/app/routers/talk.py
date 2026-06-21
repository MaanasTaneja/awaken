from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import hydra, models, schemas, simulation
from ..db import get_db
from ..dialogue import decide_optional_quest, generate_track_dialogue


router = APIRouter(prefix="/worlds/{world_id}/npcs/{npc_id}", tags=["interactions"])
TRACK_ORDER = ["greeting", "identity", "quest", "opinion", "world_lore"]


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


@router.get("/tracks", response_model=list[schemas.TrackOut])
def list_tracks(world_id: str, npc_id: str, db: Session = Depends(get_db)):
    npc = _load_npc(db, world_id, npc_id)
    return [
        schemas.TrackOut(id=track_id, **npc.tracks_json[track_id])
        for track_id in TRACK_ORDER
    ]


@router.post("/interact", response_model=schemas.InteractionResponse)
def interact(
    world_id: str,
    npc_id: str,
    body: schemas.InteractionRequest,
    background_tasks: BackgroundTasks,
    debug: bool = Query(False),
    db: Session = Depends(get_db),
):
    npc = _load_npc(db, world_id, npc_id)
    faction = db.get(models.Faction, npc.faction_id)
    track = npc.tracks_json.get(body.track)
    if track is None:
        raise HTTPException(400, "track is not configured for this NPC")

    repeat_count = (
        db.query(models.Conversation)
        .filter_by(npc_id=npc.id, player_id=body.player_id, track_id=body.track)
        .count()
        + 1
    )
    db.add(
        models.FactionEvent(
            world_id=world_id,
            faction_id=npc.faction_id,
            event_type="PLAYER_ASKED_TRACK",
            actor_id=body.player_id,
            target_npc_id=npc.id,
            visibility="DIRECT",
            summary=(
                f"The player asked {npc.name} '{track['player_text']}' "
                f"for the {repeat_count} time."
            ),
            payload_json={"track_id": body.track, "repeat_count": repeat_count},
            importance=min(0.35 + repeat_count * 0.08, 0.9),
        )
    )
    db.commit()

    # Get current state immediately (no LLM call) and kick off recall + sync in parallel.
    # sync_npc (LLM belief update) runs in background after response so dialogue is instant.
    state = simulation.get_or_create_state(db, npc.id, body.player_id)
    db.commit()
    state_payload = _state_dict(state)

    with ThreadPoolExecutor(max_workers=1) as pool:
        context_future = pool.submit(
            hydra.recall_context,
            world_id,
            npc.id,
            f"{track['player_text']} {state.belief_summary}",
            10,
        )
        context = context_future.result()

    def _bg_sync() -> None:
        from ..db import SessionLocal
        with SessionLocal() as bg_db:
            simulation.sync_npc(bg_db, npc.id, body.player_id)
            bg_db.commit()

    background_tasks.add_task(_bg_sync)

    quest = simulation.assigned_quest_for_npc(db, npc.id) if body.track == "quest" else None
    quest_decision = None
    quest_reason = None
    protected_base = None
    protected_facts = None
    quest_payload = None

    if quest:
        dialogue_branches = quest.quest_dialogue_json
        player_quest = db.get(models.PlayerQuest, (body.player_id, quest.id))
        if player_quest and player_quest.status == "COMPLETED":
            quest_decision = "COMPLETED"
            quest_reason = "The YAML-defined completion event has already occurred."
        elif player_quest and player_quest.status in {"OFFERED", "ACCEPTED", "ACTIVE"}:
            quest_decision = "ACTIVE"
            quest_reason = "The quest has already been offered and remains incomplete."
        elif quest.essential:
            quest_decision = "OFFER"
            quest_reason = "Essential quest progression cannot be blocked."
        else:
            decision = decide_optional_quest(
                npc=_npc_dict(npc),
                faction=_faction_dict(faction),
                state=state_payload,
                context=context,
                quest={
                    "key": quest.stable_key,
                    "title": quest.title,
                    "description": quest.description,
                    "objectives": quest.objective_json,
                },
                guidance=npc.quest_rules_json.get("guidance", ""),
            )
            quest_decision = decision["decision"]
            quest_reason = decision["reason"]

        branch = {
            "OFFER": "offered_base",
            "REFUSE": "refused_base",
            "ACTIVE": "active_base",
            "COMPLETED": "completed_base",
        }[quest_decision]
        protected_base = dialogue_branches.get(branch)
        protected_facts = {
            "quest_title": quest.title,
            "description": quest.description,
            "objectives": quest.objective_json,
            "hint": quest.base_hint,
        }
        if quest_decision == "OFFER":
            if player_quest is None:
                player_quest = models.PlayerQuest(
                    player_id=body.player_id, quest_id=quest.id, status="OFFERED"
                )
                db.add(player_quest)
        if player_quest is not None:
            quest_payload = schemas.TalkQuest(
                id=quest.id,
                title=quest.title,
                essential=quest.essential,
                status=player_quest.status,
            )

    result = generate_track_dialogue(
        track_id=body.track,
        track=track,
        npc=_npc_dict(npc),
        faction=_faction_dict(faction),
        state=state_payload,
        context=context,
        repeat_count=repeat_count,
        quest_decision=quest_decision,
        quest_reason=quest_reason,
        protected_base_statement=protected_base,
        protected_quest_facts=protected_facts,
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
        repeat_count=repeat_count,
        dialogue=result["dialogue"],
        tone=result["tone"],
        quest=quest_payload,
        quest_decision=quest_decision,
        quest_reason=quest_reason,
        hints_provided=result["hints_provided"],
        debug=(
            {
                **state_payload,
                "retrieved_context": context,
                "protected_base_statement": protected_base,
            }
            if debug
            else None
        ),
    )
