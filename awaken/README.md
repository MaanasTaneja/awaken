# Awaken

Faction-based NPC memory API. NPCs independently consume faction events, form beliefs about the player, hear distorted hearsay from trusted friends, and alter quest dialogue and availability.

## Structure

```
awaken/
├── api/           # FastAPI backend (Postgres + Redis)
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── simulation.py     # NPC sync loop, event cursors, gossip
│   │   ├── dialogue.py       # LLM dialogue generation
│   │   ├── hydra.py          # HydraDB memory store (stub)
│   │   ├── seed.py           # Seed demo world
│   │   └── routers/
│   ├── Dockerfile
│   └── requirements.txt
├── game/          # Vite + Phaser/three.js client (to be added)
└── docker-compose.yml
```

## Quick start

```bash
cd awaken
cp .env.example .env
docker compose up --build
```

API → http://localhost:8000 — Swagger at `/docs`.

Seed the demo world:

```bash
curl -X POST http://localhost:8000/seed
```

## Architecture notes

- **Faction event log**, not a queue. Each NPC has its own `last_processed_event_id` cursor over the faction's append-only log.
- **SQLite-style schema on Postgres** — deterministic state (factions, NPCs, relationships, entities, events, cursors, opinions, quests) lives here.
- **HydraDB** — subjective NPC memory ("why does Varyon dislike the player"). Stubbed in `hydra.py`; swap with the official SDK.
- **Redis** — optional queue for background `tick_world`. The MVP exposes a synchronous `POST /worlds/{id}/tick` endpoint so the demo button works without a worker.
- **LLM dialogue / belief updates** — wire to your provider in `dialogue.py` (`OPENAI_API_KEY` env). Falls back to a deterministic stub when no key is set, so the API runs end-to-end out of the box.

## Endpoints (MVP)

| | |
|---|---|
| Worlds, factions, NPCs, relationships, entities, quests | full CRUD |
| `POST /worlds/{id}/events` | manually emit an event |
| `POST /worlds/{id}/npcs/{id}/sync` | sync one NPC |
| `POST /worlds/{id}/tick` | sync all NPCs in the world |
| `POST /worlds/{id}/npcs/{id}/talk` | converse with an NPC |
| `PATCH /worlds/{id}/npcs/{id}/player-state` | demo: force an opinion |

See `docs/` (via Swagger) for full schemas.
