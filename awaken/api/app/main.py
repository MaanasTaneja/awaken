from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import hydra, models
from .db import SessionLocal, get_db, init_db
from .routers import entities, events, factions, npcs, quests, relationships, talk, worlds
from .seed import DEFAULT_WORLD_FILE, seed_demo

app = FastAPI(title="Awaken API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    hydra.validate_connection()
    db = SessionLocal()
    try:
        seed_demo(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {"name": "Awaken", "docs": "/docs"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/seed")
def get_seed(db: Session = Depends(get_db)):
    """Return the current world context (IDs only) without re-seeding."""
    from .world_definition import load_world_definition
    definition = load_world_definition(DEFAULT_WORLD_FILE)
    world = db.query(models.World).filter_by(stable_key=definition.world.id).first()
    if world is None:
        raise HTTPException(503, "World not seeded yet")
    npc_rows = db.query(models.NPC).filter_by(world_id=world.id).all()
    faction_rows = db.query(models.Faction).filter_by(world_id=world.id).all()
    quest_rows = db.query(models.Quest).filter_by(world_id=world.id).all()
    return {
        "world_id": world.id,
        "world_key": world.stable_key,
        "npcs": {n.stable_key: n.id for n in npc_rows},
        "factions": {f.stable_key: f.id for f in faction_rows},
        "quests": {q.stable_key: q.id for q in quest_rows},
    }


@app.post("/seed")
def seed(db: Session = Depends(get_db)):
    return seed_demo(db)


app.include_router(worlds.router)
app.include_router(factions.router)
app.include_router(npcs.router)
app.include_router(relationships.router)
app.include_router(entities.router)
app.include_router(events.router)
app.include_router(quests.router)
app.include_router(talk.router)
