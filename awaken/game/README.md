# Awaken — Game Client

Placeholder. The client will be a Vite app (Phaser or three.js) that talks to the API at `http://localhost:8000`.

Planned scaffold:

```
game/
├── index.html
├── package.json
├── vite.config.ts
└── src/
    ├── main.ts
    ├── api.ts          # typed client for /worlds, /npcs, /talk, /tick
    ├── scenes/
    │   ├── Temple.ts
    │   ├── MageGuild.ts
    │   └── MerchantHall.ts
    └── ui/
        ├── DialogueBox.ts
        ├── OpinionInspector.ts
        └── EventLog.ts
```
