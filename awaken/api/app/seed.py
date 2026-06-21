"""Validate a YAML world, reset its SQL runtime state, and upsert HydraDB lore."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from . import hydra, models
from .config import settings
from .world_definition import WorldDefinition, load_world_definition


WORLD_DIR = Path(__file__).resolve().parents[2] / "worlds"
DEFAULT_WORLD_FILE = WORLD_DIR / "aelryn.yaml"


def _text(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _knowledge_sources(definition: WorldDefinition) -> list[dict[str, Any]]:
    world_key = definition.world.id
    sources: list[dict[str, Any]] = [
        {
            "id": f"world_{world_key}",
            "title": f"World: {definition.world.name}",
            "type": "custom",
            "content": {
                "text": f"{definition.world.description}\n\nCanonical lore:\n{_text(definition.world.lore)}"
            },
            "additional_metadata": {"source": "world_yaml", "world_key": world_key},
        }
    ]
    for key, faction in definition.factions.items():
        sources.append(
            {
                "id": f"faction_{world_key}_{key}",
                "title": f"Faction: {faction.name}",
                "type": "custom",
                "content": {
                    "text": (
                        f"{faction.description}\nLore: {_text(faction.lore)}\n"
                        f"Beliefs: {_text(faction.beliefs)}"
                    )
                },
                "additional_metadata": {
                    "source": "faction_yaml",
                    "world_key": world_key,
                    "faction_key": key,
                },
                "relations": {"ids": [f"world_{world_key}"]},
            }
        )
    for key, entity in definition.world.entities.items():
        faction_key = entity.get("faction")
        relation_ids = [f"world_{world_key}"]
        if faction_key:
            relation_ids.append(f"faction_{world_key}_{faction_key}")
        sources.append(
            {
                "id": f"entity_{world_key}_{key}",
                "title": f"Entity: {entity['name']}",
                "type": "custom",
                "content": {"text": _text(entity)},
                "additional_metadata": {
                    "source": "entity_yaml",
                    "world_key": world_key,
                    "entity_key": key,
                },
                "relations": {"ids": relation_ids},
            }
        )
    for key, quest in definition.quests.items():
        sources.append(
            {
                "id": f"quest_{world_key}_{key}",
                "title": f"Quest: {quest.name}",
                "type": "custom",
                "content": {
                    "text": (
                        f"{quest.description}\nObjectives: {_text(quest.objectives)}\n"
                        f"Completion: {_text(quest.completion.model_dump())}"
                    )
                },
                "additional_metadata": {
                    "source": "quest_yaml",
                    "world_key": world_key,
                    "quest_key": key,
                    "essential": quest.essential,
                },
                "relations": {"ids": [f"world_{world_key}"]},
            }
        )
    for key, npc in definition.npcs.items():
        sources.append(
            {
                "id": f"npc_{world_key}_{key}",
                "title": f"NPC: {npc.name}",
                "type": "custom",
                "content": {
                    "text": (
                        f"{npc.name} is the {npc.role}. {npc.behavioral_prompt}\n"
                        f"Personality: {_text(npc.personality.model_dump())}"
                    )
                },
                "additional_metadata": {
                    "source": "npc_yaml",
                    "world_key": world_key,
                    "npc_key": key,
                },
                "relations": {
                    "ids": [
                        f"world_{world_key}",
                        f"faction_{world_key}_{npc.faction}",
                        f"quest_{world_key}_{npc.quest}",
                    ]
                },
            }
        )
    for source in sources:
        source["tenant_id"] = settings.hydra_tenant_id
        source["sub_tenant_id"] = "default"
    return sources


def seed_demo(db: Session, path: Path = DEFAULT_WORLD_FILE) -> dict[str, Any]:
    definition = load_world_definition(path)

    existing = db.query(models.World).filter_by(stable_key=definition.world.id).first()
    if existing:
        # Collect old NPC IDs before cascade delete so we can wipe their HydraDB sub_tenants.
        # Also build the deterministic knowledge IDs that were seeded for this world.
        old_npc_ids = [n.id for n in db.query(models.NPC).filter_by(world_id=existing.id).all()]
        old_knowledge_ids = [src["id"] for src in _knowledge_sources(definition)]
        hydra.clear_world_context(existing.id, old_npc_ids, old_knowledge_ids)
        # Use a query-based delete to bypass ORM identity-map tracking issues.
        # ON DELETE CASCADE handles all child rows at the DB level.
        db.query(models.World).filter_by(stable_key=definition.world.id).delete(synchronize_session=False)
        db.commit()
        db.expire_all()

    world = models.World(
        stable_key=definition.world.id,
        name=definition.world.name,
        description=definition.world.description,
        lore_json={
            "lore": definition.world.lore,
            "event_rules": {
                key: value.model_dump() for key, value in definition.event_rules.items()
            },
        },
    )
    db.add(world)
    db.flush()

    factions: dict[str, models.Faction] = {}
    for key, item in definition.factions.items():
        faction = models.Faction(
            stable_key=key,
            world_id=world.id,
            name=item.name,
            description=item.description,
            behavior_prompt=item.interpretation_prompt,
            lore_json=item.lore,
            beliefs_json=item.beliefs,
        )
        db.add(faction)
        factions[key] = faction
    db.flush()

    quests: dict[str, models.Quest] = {}
    for key, item in definition.quests.items():
        quest = models.Quest(
            stable_key=key,
            world_id=world.id,
            title=item.name,
            description=item.description,
            essential=item.essential,
            priority=item.priority,
            objective_json={"steps": item.objectives},
            base_dialogue=item.base_dialogue,
            base_hint=item.hint,
            completion_event_json=item.completion.model_dump(),
        )
        db.add(quest)
        quests[key] = quest
    db.flush()

    npcs: dict[str, models.NPC] = {}
    for key, item in definition.npcs.items():
        npc = models.NPC(
            stable_key=key,
            world_id=world.id,
            faction_id=factions[item.faction].id,
            name=item.name,
            role=item.role,
            behavior_prompt=item.behavioral_prompt,
            personality_json=item.personality.model_dump(),
            tracks_json={track: value.model_dump() for track, value in item.tracks.items()},
            base_friendliness=0,
            gossipiness=item.personality.talkativeness,
            stubbornness=item.personality.stubbornness,
        )
        db.add(npc)
        npcs[key] = npc
    db.flush()

    for key, item in definition.world.entities.items():
        faction = factions.get(item.get("faction"))
        db.add(
            models.Entity(
                stable_key=key,
                world_id=world.id,
                faction_id=faction.id if faction else None,
                name=item["name"],
                entity_type=item["entity_type"],
                state_json={
                    "description": item.get("description", ""),
                    **item.get("initial_state", {}),
                },
            )
        )

    for key, item in definition.npcs.items():
        db.add(models.NPCQuest(npc_id=npcs[key].id, quest_id=quests[item.quest].id))

    for item in definition.relationships:
        db.add(
            models.NPCRelationship(
                from_npc_id=npcs[item.from_npc].id,
                to_npc_id=npcs[item.to_npc].id,
                relationship_type=item.relationship_type,
                trust=item.trust,
                affinity=item.affinity,
            )
        )

    db.commit()
    knowledge_ids = hydra.store_world_knowledge(_knowledge_sources(definition))
    return {
        "definition": str(path.name),
        "world_id": world.id,
        "world_key": world.stable_key,
        "factions": {key: value.id for key, value in factions.items()},
        "npcs": {key: value.id for key, value in npcs.items()},
        "quests": {key: value.id for key, value in quests.items()},
        "hydra_knowledge_ids": knowledge_ids,
    }
