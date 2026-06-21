from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import hydra
from .db import get_db, init_db
from .routers import entities, events, factions, npcs, quests, relationships, talk, worlds
from .seed import seed_demo

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


@app.get("/")
def root():
    return {"name": "Awaken", "docs": "/docs"}


@app.get("/health")
def health():
    return {"ok": True}


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
