from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, simulation
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}", tags=["events"])


def _apply_quest_completions(db: Session, event: models.FactionEvent) -> None:
    payload = event.payload_json or {}
    for quest in db.query(models.Quest).filter_by(world_id=event.world_id).all():
        rule = quest.completion_event_json or {}
        if rule.get("event_type") != event.event_type:
            continue
        if any(payload.get(key) != value for key, value in (rule.get("filters") or {}).items()):
            continue
        player_id = event.actor_id or "player_1"
        player_quest = db.get(models.PlayerQuest, (player_id, quest.id))
        if player_quest is None:
            player_quest = models.PlayerQuest(
                player_id=player_id, quest_id=quest.id, status="COMPLETED"
            )
            db.add(player_quest)
        else:
            player_quest.status = "COMPLETED"


@router.post("/events", response_model=schemas.EventOut)
def create_event(world_id: str, body: schemas.EventCreate, db: Session = Depends(get_db)):
    faction = db.get(models.Faction, body.faction_id)
    if faction is None or faction.world_id != world_id:
        raise HTTPException(400, "faction does not belong to this world")
    ev = models.FactionEvent(
        world_id=world_id,
        **body.model_dump(),
    )
    db.add(ev)
    db.flush()
    _apply_quest_completions(db, ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/factions/{faction_id}/events", response_model=list[schemas.EventOut])
def list_events(
    world_id: str, faction_id: str, limit: int = 100, db: Session = Depends(get_db)
):
    return (
        db.query(models.FactionEvent)
        .filter_by(world_id=world_id, faction_id=faction_id)
        .order_by(models.FactionEvent.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/tick")
def tick_world(world_id: str, db: Session = Depends(get_db)):
    if not db.get(models.World, world_id):
        raise HTTPException(404, "world not found")
    results = []
    for npc in db.query(models.NPC).filter_by(world_id=world_id).all():
        results.append(simulation.sync_npc(db, npc.id))
    db.commit()
    return {"world_id": world_id, "updated_npcs": results}
