from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import hydra, models, schemas, simulation
from ..db import get_db
from ..dialogue import generate_dialogue

router = APIRouter(prefix="/worlds/{world_id}/npcs/{npc_id}", tags=["talk"])


@router.post("/talk", response_model=schemas.TalkResponse)
def talk(
    world_id: str,
    npc_id: str,
    body: schemas.TalkRequest,
    debug: bool = Query(False),
    db: Session = Depends(get_db),
):
    npc = db.get(models.NPC, npc_id)
    if npc is None or npc.world_id != world_id:
        raise HTTPException(404, "npc not found")
    faction = db.get(models.Faction, npc.faction_id)

    # 1. Process any new events queued for this NPC before we speak.
    simulation.sync_npc(db, npc.id, body.player_id)

    state = simulation.get_or_create_state(db, npc.id, body.player_id)
    quest = simulation.select_quest_for_npc(db, npc.id, body.player_id)

    memories = hydra.recall_memories(
        world_id, npc.id, body.message or "initial greeting", limit=5
    )

    quest_dict = (
        {
            "id": quest.id,
            "title": quest.title,
            "description": quest.description,
            "essential": quest.essential,
            "base_dialogue": quest.base_dialogue,
            "base_hint": quest.base_hint,
        }
        if quest
        else None
    )

    response = generate_dialogue(
        npc={
            "name": npc.name,
            "role": npc.role,
            "behavior_prompt": npc.behavior_prompt,
        },
        faction={
            "name": faction.name if faction else "",
            "behavior_prompt": faction.behavior_prompt if faction else "",
        },
        state={
            "affinity": state.affinity,
            "trust": state.trust,
            "fear": state.fear,
            "respect": state.respect,
            "belief_tags": state.belief_tags_json or [],
            "belief_summary": state.belief_summary,
        },
        memories=memories,
        player_message=body.message,
        quest=quest_dict,
    )

    convo = models.Conversation(
        npc_id=npc.id,
        player_id=body.player_id,
        player_message=body.message,
        npc_response=response["dialogue"],
    )
    db.add(convo)

    # Emit a DIRECT faction event so other NPCs in the faction can hear about it.
    db.add(
        models.FactionEvent(
            world_id=world_id,
            faction_id=npc.faction_id,
            event_type="PLAYER_CONVERSATION",
            actor_id=body.player_id,
            target_npc_id=npc.id,
            visibility="DIRECT",
            summary=response.get("event_summary", f"The player spoke with {npc.name}."),
        )
    )

    quest_payload = None
    if quest:
        pq = db.get(models.PlayerQuest, (body.player_id, quest.id))
        if pq is None:
            pq = models.PlayerQuest(
                player_id=body.player_id, quest_id=quest.id, status="OFFERED"
            )
            db.add(pq)
        quest_payload = schemas.TalkQuest(
            id=quest.id, title=quest.title, essential=quest.essential, status=pq.status
        )

    db.commit()
    db.refresh(convo)

    return schemas.TalkResponse(
        session_id=convo.id,
        npc_id=npc.id,
        dialogue=response["dialogue"],
        tone=response.get("tone", "neutral"),
        quest=quest_payload,
        hints_provided=response.get("hints_provided", []),
        debug=(
            {
                "affinity": state.affinity,
                "trust": state.trust,
                "fear": state.fear,
                "respect": state.respect,
                "belief_tags": state.belief_tags_json or [],
                "belief_summary": state.belief_summary,
            }
            if debug
            else None
        ),
    )
