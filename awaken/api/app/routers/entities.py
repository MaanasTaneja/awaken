from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}/entities", tags=["entities"])


@router.post("", response_model=schemas.EntityOut)
def create_entity(world_id: str, body: schemas.EntityCreate, db: Session = Depends(get_db)):
    if not db.get(models.World, world_id):
        raise HTTPException(404, "world not found")
    e = models.Entity(
        world_id=world_id,
        stable_key=body.name.lower().replace(" ", "_"),
        **body.model_dump(),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.get("", response_model=list[schemas.EntityOut])
def list_entities(world_id: str, db: Session = Depends(get_db)):
    return db.query(models.Entity).filter_by(world_id=world_id).all()


@router.patch("/{entity_id}", response_model=schemas.EntityOut)
def update_entity(
    world_id: str, entity_id: str, body: schemas.EntityUpdate, db: Session = Depends(get_db)
):
    e = db.get(models.Entity, entity_id)
    if e is None or e.world_id != world_id:
        raise HTTPException(404, "entity not found")

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(e, k, v)

    # Auto-emit an ENTITY_UPDATED faction event so the simulation reacts.
    if e.faction_id:
        ev = models.FactionEvent(
            world_id=world_id,
            faction_id=e.faction_id,
            event_type="ENTITY_UPDATED",
            target_id=e.id,
            visibility="PUBLIC",
            summary=f"{e.name} was changed.",
            payload_json={"changes": data},
        )
        db.add(ev)

    db.commit()
    db.refresh(e)
    return e


@router.delete("/{entity_id}")
def delete_entity(world_id: str, entity_id: str, db: Session = Depends(get_db)):
    e = db.get(models.Entity, entity_id)
    if e is None or e.world_id != world_id:
        raise HTTPException(404, "entity not found")
    db.delete(e)
    db.commit()
    return {"ok": True}
