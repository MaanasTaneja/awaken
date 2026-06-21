from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}/factions", tags=["factions"])


@router.post("", response_model=schemas.FactionOut)
def create_faction(world_id: str, body: schemas.FactionCreate, db: Session = Depends(get_db)):
    if not db.get(models.World, world_id):
        raise HTTPException(404, "world not found")
    f = models.Faction(
        stable_key=body.name.lower().replace(" ", "_"),
        world_id=world_id,
        name=body.name,
        description=body.description,
        behavior_prompt=body.behavior_prompt,
        lore_json=[],
        beliefs_json={},
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.get("", response_model=list[schemas.FactionOut])
def list_factions(world_id: str, db: Session = Depends(get_db)):
    return db.query(models.Faction).filter_by(world_id=world_id).all()


@router.get("/{faction_id}", response_model=schemas.FactionOut)
def get_faction(world_id: str, faction_id: str, db: Session = Depends(get_db)):
    f = db.get(models.Faction, faction_id)
    if f is None or f.world_id != world_id:
        raise HTTPException(404, "faction not found")
    return f


@router.delete("/{faction_id}")
def delete_faction(world_id: str, faction_id: str, db: Session = Depends(get_db)):
    f = db.get(models.Faction, faction_id)
    if f is None or f.world_id != world_id:
        raise HTTPException(404, "faction not found")
    db.delete(f)
    db.commit()
    return {"ok": True}
