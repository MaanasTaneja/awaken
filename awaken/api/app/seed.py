"""Seed the demo world: 1 world, 3 factions, 6 NPCs, relationships, entities, quests."""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import models


def seed_demo(db: Session) -> dict:
    # Wipe any existing demo world named 'Aelryn'.
    existing = db.query(models.World).filter_by(name="Aelryn").first()
    if existing:
        db.delete(existing)
        db.commit()

    world = models.World(name="Aelryn", description="A small kingdom on the brink.")
    db.add(world)
    db.flush()

    temple = models.Faction(
        world_id=world.id,
        name="Ashen Temple",
        description="A stern religious order.",
        behavior_prompt=(
            "The Ashen Temple values religious obedience and tradition. "
            "It distrusts outsiders, thieves, forbidden magic, and the Mages Guild. "
            "Its members strongly condemn the theft of sacred objects."
        ),
    )
    mages = models.Faction(
        world_id=world.id,
        name="Mages Guild",
        description="Curious arcanists who collect knowledge.",
        behavior_prompt=(
            "The Mages Guild values knowledge, experimentation, and personal liberty. "
            "It dislikes superstition, censorship, and the Ashen Temple."
        ),
    )
    merchants = models.Faction(
        world_id=world.id,
        name="Merchant House",
        description="Pragmatic traders who follow the coin.",
        behavior_prompt=(
            "The Merchant House values profit, contracts honored, and stability. "
            "It dislikes thieves and chaos."
        ),
    )
    db.add_all([temple, mages, merchants])
    db.flush()

    # --- NPCs ---
    varyon = models.NPC(
        world_id=world.id, faction_id=temple.id, name="Varyon", role="Priest",
        behavior_prompt="Proud, judgmental, deeply loyal to the Temple. Distrusts the Mages Guild.",
        base_friendliness=-10, gossipiness=0.4, stubbornness=0.8,
    )
    cassian = models.NPC(
        world_id=world.id, faction_id=temple.id, name="Cassian", role="Temple Guard",
        behavior_prompt="Vigilant, dutiful, suspicious of strangers near the relic.",
        base_friendliness=0, gossipiness=0.6, stubbornness=0.5,
    )
    elara = models.NPC(
        world_id=world.id, faction_id=mages.id, name="Elara", role="Archmage",
        behavior_prompt="Curious, witty, dismissive of religious dogma.",
        base_friendliness=10, gossipiness=0.7, stubbornness=0.4,
    )
    pell = models.NPC(
        world_id=world.id, faction_id=mages.id, name="Pell", role="Apprentice",
        behavior_prompt="Nervous, eager to please, hero-worships Elara.",
        base_friendliness=20, gossipiness=0.9, stubbornness=0.2,
    )
    mira = models.NPC(
        world_id=world.id, faction_id=merchants.id, name="Mira", role="Merchant",
        behavior_prompt="Shrewd, friendly to anyone with coin, careful about thieves.",
        base_friendliness=15, gossipiness=0.5, stubbornness=0.3,
    )
    bren = models.NPC(
        world_id=world.id, faction_id=merchants.id, name="Bren", role="Serf",
        behavior_prompt="Tired, gossipy, repeats whatever the market is saying.",
        base_friendliness=5, gossipiness=0.95, stubbornness=0.1,
    )
    npcs = [varyon, cassian, elara, pell, mira, bren]
    db.add_all(npcs)
    db.flush()

    # --- Relationships (directed) ---
    def rel(a, b, trust, affinity):
        db.add(models.NPCRelationship(
            from_npc_id=a.id, to_npc_id=b.id, trust=trust, affinity=affinity
        ))
    rel(varyon, cassian, 0.9, 0.6)
    rel(cassian, varyon, 0.5, 0.5)
    rel(varyon, bren, 0.2, 0.0)
    rel(elara, pell, 0.7, 0.6)
    rel(pell, elara, 0.95, 0.9)
    rel(mira, bren, 0.6, 0.3)
    rel(bren, mira, 0.4, 0.2)
    rel(cassian, mira, 0.5, 0.2)

    # --- Entities ---
    db.add_all([
        models.Entity(world_id=world.id, faction_id=temple.id,
                      name="Sacred Relic", entity_type="item",
                      state_json={"location": "temple", "stolen": False}),
        models.Entity(world_id=world.id, faction_id=temple.id,
                      name="Temple Door", entity_type="door",
                      state_json={"locked": True}),
        models.Entity(world_id=world.id, faction_id=mages.id,
                      name="Mage's Crystal", entity_type="item",
                      state_json={"powered": True}),
        models.Entity(world_id=world.id, faction_id=merchants.id,
                      name="Merchant Chest", entity_type="container",
                      state_json={"gold": 250}),
    ])

    # --- Quests ---
    recover = models.Quest(
        world_id=world.id, title="Recover the Sacred Relic",
        description="Find and return the stolen relic to the Temple.",
        essential=True, priority=100,
        base_dialogue="The relic must be returned. Search the ruined shrine.",
        base_hint="A hidden entrance lies behind the western altar.",
    )
    deliver = models.Quest(
        world_id=world.id, title="Deliver Sealed Letter",
        description="Carry a sealed letter from Mira to Elara.",
        essential=False, priority=10,
        base_dialogue="Take this to Elara at the Mages Guild. Don't open it.",
    )
    db.add_all([recover, deliver])
    db.flush()

    db.add(models.NPCQuest(npc_id=varyon.id, quest_id=recover.id))
    db.add(models.NPCQuest(npc_id=cassian.id, quest_id=recover.id))
    db.add(models.NPCQuest(
        npc_id=mira.id, quest_id=deliver.id,
        minimum_affinity=10, minimum_trust=0,
        blocked_tags_json=["PLAYER_MAY_BE_THIEF", "PLAYER_IS_THIEF"],
    ))

    db.commit()
    return {
        "world_id": world.id,
        "factions": [temple.id, mages.id, merchants.id],
        "npcs": {n.name: n.id for n in npcs},
        "quests": {recover.title: recover.id, deliver.title: deliver.id},
    }
