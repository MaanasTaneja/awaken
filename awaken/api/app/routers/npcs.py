from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import hydra, models, schemas, simulation
from ..db import get_db

router = APIRouter(prefix="/worlds/{world_id}/npcs", tags=["npcs"])


@router.post("", response_model=schemas.NPCOut)
def create_npc(world_id: str, body: schemas.NPCCreate, db: Session = Depends(get_db)):
    if not db.get(models.World, world_id):
        raise HTTPException(404, "world not found")
    faction = db.get(models.Faction, body.faction_id)
    if faction is None or faction.world_id != world_id:
        raise HTTPException(400, "faction does not belong to this world")
    n = models.NPC(
        world_id=world_id,
        stable_key=body.name.lower().replace(" ", "_"),
        personality_json={},
        tracks_json={},
        **body.model_dump(),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


@router.get("", response_model=list[schemas.NPCOut])
def list_npcs(world_id: str, db: Session = Depends(get_db)):
    return db.query(models.NPC).filter_by(world_id=world_id).all()


@router.get("/{npc_id}", response_model=schemas.NPCOut)
def get_npc(world_id: str, npc_id: str, db: Session = Depends(get_db)):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    return n


@router.patch("/{npc_id}", response_model=schemas.NPCOut)
def update_npc(world_id: str, npc_id: str, body: schemas.NPCUpdate, db: Session = Depends(get_db)):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return n


@router.delete("/{npc_id}")
def delete_npc(world_id: str, npc_id: str, db: Session = Depends(get_db)):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


# --- player-state inspection / override ---

@router.get("/{npc_id}/player-state", response_model=schemas.PlayerStateOut)
def get_player_state(
    world_id: str, npc_id: str, player_id: str = "player_1", db: Session = Depends(get_db)
):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    state = simulation.get_or_create_state(db, npc_id, player_id)
    db.commit()
    return state


@router.patch("/{npc_id}/player-state", response_model=schemas.PlayerStateOut)
def patch_player_state(
    world_id: str,
    npc_id: str,
    body: schemas.PlayerStatePatch,
    player_id: str = "player_1",
    db: Session = Depends(get_db),
):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    state = simulation.get_or_create_state(db, npc_id, player_id)
    data = body.model_dump(exclude_unset=True)
    for k in ("affinity", "trust", "fear", "respect", "belief_summary"):
        if k in data:
            setattr(state, k, data[k])
    if "belief_tags" in data:
        state.belief_tags_json = data["belief_tags"]
    db.commit()
    db.refresh(state)
    return state


# --- sync one NPC ---

@router.post("/{npc_id}/sync")
def sync_one(world_id: str, npc_id: str, db: Session = Depends(get_db)):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    result = simulation.sync_npc(db, npc_id)
    db.commit()
    return result


# --- read-only memory inspection for the disposable game tester ---

@router.get("/{npc_id}/memories")
def recall_npc_memories(
    world_id: str,
    npc_id: str,
    query: str = "important experiences with the player",
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    n = db.get(models.NPC, npc_id)
    if n is None or n.world_id != world_id:
        raise HTTPException(404, "npc not found")
    return {
        "npc_id": npc_id,
        "query": query,
        "memories": hydra.recall_memories(world_id, npc_id, query, limit),
    }
