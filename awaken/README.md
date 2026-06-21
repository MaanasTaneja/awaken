# Awaken

Emergent faction/NPC simulation with YAML-authored worlds, PostgreSQL runtime
state, HydraDB world knowledge and NPC memories, and LLM-generated beliefs and
dialogue constrained by five authored interaction tracks.

## Run locally

The schema changed during the YAML/track migration, so reset the development
database once:

```bash
cp .env.example .env
docker compose down -v
docker compose up --build -d
```

Required `.env` values:

```dotenv
OPENAI_API_KEY=...
HYDRA_DB_API_KEY=...
HYDRA_TENANT_ID=awaken
```

The HydraDB tenant must already exist and report `ready_for_ingestion=true`.

- Tester: <http://localhost:3000>
- FastAPI: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>

Press **Seed / Reset YAML World** in the tester. Seeding validates
[`worlds/aelryn.yaml`](worlds/aelryn.yaml), resets that world's SQL runtime
state, and upserts canonical lore, factions, entities, quests, and NPC
biographies into HydraDB Knowledge.

## Authored world contract

The YAML definition contains:

- world description, lore, locations, and entities;
- faction lore, beliefs, fears, prejudices, and interpretation prompts;
- quests, essential flags, objectives, completion event/filter rules, and
  protected offered/refused/active/completed base statements;
- NPC faction/quest assignments, personality dimensions, behavior prompts,
  relationships, and exactly five tracks;
- event interpretation guidance.

Every NPC exposes `greeting`, `identity`, `quest`, `opinion`, and `world_lore`.
The browser sends a track ID, never arbitrary dialogue text.

## Runtime flow

1. Selecting a track appends a targeted `PLAYER_ASKED_TRACK` event containing
   its repetition count.
2. The NPC processes new faction events and hearsay from explicitly configured
   directed relationships. There is no fixed trust threshold; the model sees
   relationship type, trust, and affinity and interprets the hearsay.
3. Objective event memories are persisted to HydraDB independently of the LLM.
4. A strict structured-output belief call updates subjective state and may add
   interpreted memories.
5. HydraDB retrieves shared world Knowledge and that NPC's private Memory.
6. For the quest track, essential quests always choose the offer branch;
   optional quests receive an emergent `OFFER`/`REFUSE` model decision.
7. A strict dialogue call personalizes the selected track. Protected quest
   facts and the selected branch cannot be reversed.

## Main endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /seed` | Load YAML and upsert HydraDB world knowledge |
| `GET /worlds/{world}/npcs/{npc}/tracks` | Return the five authored tracks |
| `POST /worlds/{world}/npcs/{npc}/interact` | Run one track |
| `POST /worlds/{world}/events` | Append a world/faction event and apply quest completion rules |
| `POST /worlds/{world}/npcs/{npc}/sync` | Process unseen events for one NPC |
| `POST /worlds/{world}/tick` | Process unseen events for every NPC |
| `GET /worlds/{world}/npcs/{npc}/player-state` | Inspect subjective player beliefs |
| `GET /worlds/{world}/npcs/{npc}/memories` | Inspect retrieved NPC memories |

## Tests

```bash
docker compose run --rm --no-deps api python -m unittest discover -s tests -v
```

Tests cover YAML completeness, strict structured belief output, HydraDB memory
scope, and world-knowledge upsert payloads.
