from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}/relationships", tags=["relationships"])


@router.post("", response_model=schemas.RelationshipOut)
def create_rel(world_id: str, body: schemas.RelationshipCreate, db: Session = Depends(get_db)):
    for nid in (body.from_npc_id, body.to_npc_id):
        n = db.get(models.NPC, nid)
        if n is None or n.world_id != world_id:
            raise HTTPException(400, f"npc {nid} not in world")
    r = models.NPCRelationship(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("", response_model=list[schemas.RelationshipOut])
def list_rels(world_id: str, db: Session = Depends(get_db)):
    npc_ids = [n.id for n in db.query(models.NPC).filter_by(world_id=world_id)]
    return (
        db.query(models.NPCRelationship)
        .filter(models.NPCRelationship.from_npc_id.in_(npc_ids))
        .all()
    )


@router.delete("/{rel_id}")
def delete_rel(world_id: str, rel_id: str, db: Session = Depends(get_db)):
    r = db.get(models.NPCRelationship, rel_id)
    if r is None:
        raise HTTPException(404, "relationship not found")
    db.delete(r)
    db.commit()
    return {"ok": True}
