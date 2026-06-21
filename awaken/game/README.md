# Awaken API Tester

Disposable browser UI for exercising the Awaken simulation without curl.

Start the full stack from `awaken/`:

```bash
docker compose up --build -d
```

Open <http://localhost:3000>. The page talks to the FastAPI service at
`http://localhost:8000` and can seed the YAML world, select one of each NPC's
five authored tracks, emit quest and faction events, sync NPCs, inspect belief
state and HydraDB memories, and compare repeated-track responses.

To remove the tester later, delete `game/`, remove the `game` service from
`docker-compose.yml`, and remove the temporary `GET .../memories` route from
`api/app/routers/npcs.py`.
