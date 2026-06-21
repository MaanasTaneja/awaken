import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.post("", response_model=schemas.WorldOut)
def create_world(body: schemas.WorldCreate, db: Session = Depends(get_db)):
    w = models.World(
        stable_key=f"world_{uuid.uuid4().hex}",
        name=body.name,
        description=body.description,
        lore_json={},
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


@router.get("", response_model=list[schemas.WorldOut])
def list_worlds(db: Session = Depends(get_db)):
    return db.query(models.World).all()


@router.get("/{world_id}", response_model=schemas.WorldOut)
def get_world(world_id: str, db: Session = Depends(get_db)):
    w = db.get(models.World, world_id)
    if w is None:
        raise HTTPException(404, "world not found")
    return w


@router.delete("/{world_id}")
def delete_world(world_id: str, db: Session = Depends(get_db)):
    w = db.get(models.World, world_id)
    if w is None:
        raise HTTPException(404, "world not found")
    db.delete(w)
    db.commit()
    return {"ok": True}
