from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}", tags=["quests"])


@router.post("/quests", response_model=schemas.QuestOut)
def create_quest(world_id: str, body: schemas.QuestCreate, db: Session = Depends(get_db)):
    if not db.get(models.World, world_id):
        raise HTTPException(404, "world not found")
    q = models.Quest(
        world_id=world_id,
        stable_key=body.title.lower().replace(" ", "_"),
        completion_event_json={},
        **body.model_dump(),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.get("/quests", response_model=list[schemas.QuestOut])
def list_quests(world_id: str, db: Session = Depends(get_db)):
    return db.query(models.Quest).filter_by(world_id=world_id).all()


@router.delete("/quests/{quest_id}")
def delete_quest(world_id: str, quest_id: str, db: Session = Depends(get_db)):
    q = db.get(models.Quest, quest_id)
    if q is None or q.world_id != world_id:
        raise HTTPException(404, "quest not found")
    db.delete(q)
    db.commit()
    return {"ok": True}


@router.post("/npcs/{npc_id}/quests/{quest_id}")
def assign_quest(
    world_id: str,
    npc_id: str,
    quest_id: str,
    body: schemas.NPCQuestAssign,
    db: Session = Depends(get_db),
):
    npc = db.get(models.NPC, npc_id)
    quest = db.get(models.Quest, quest_id)
    if npc is None or npc.world_id != world_id:
        raise HTTPException(404, "npc not found")
    if quest is None or quest.world_id != world_id:
        raise HTTPException(404, "quest not found")
    existing = db.get(models.NPCQuest, (npc_id, quest_id))
    if not existing:
        db.add(models.NPCQuest(npc_id=npc_id, quest_id=quest_id))
    db.commit()
    return {"ok": True}


@router.delete("/npcs/{npc_id}/quests/{quest_id}")
def unassign_quest(world_id: str, npc_id: str, quest_id: str, db: Session = Depends(get_db)):
    a = db.get(models.NPCQuest, (npc_id, quest_id))
    if a is None:
        raise HTTPException(404, "assignment not found")
    db.delete(a)
    db.commit()
    return {"ok": True}
