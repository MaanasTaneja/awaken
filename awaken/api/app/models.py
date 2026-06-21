from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class World(Base):
    __tablename__ = "worlds"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stable_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lore_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Faction(Base):
    __tablename__ = "factions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stable_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    behavior_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lore_json: Mapped[list] = mapped_column(JSONB, default=list)
    beliefs_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class NPC(Base):
    __tablename__ = "npcs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stable_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    faction_id: Mapped[str] = mapped_column(ForeignKey("factions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="")
    behavior_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    personality_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    tracks_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    quest_rules_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    base_friendliness: Mapped[int] = mapped_column(Integer, default=0)
    gossipiness: Mapped[float] = mapped_column(Float, default=0.5)
    stubbornness: Mapped[float] = mapped_column(Float, default=0.5)


class NPCRelationship(Base):
    __tablename__ = "npc_relationships"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"))
    to_npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"))
    relationship_type: Mapped[str | None] = mapped_column(String)
    trust: Mapped[float] = mapped_column(Float, default=0.0)
    affinity: Mapped[float] = mapped_column(Float, default=0.0)


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stable_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    state_json: Mapped[dict | None] = mapped_column(JSONB)


class FactionEvent(Base):
    __tablename__ = "faction_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    faction_id: Mapped[str] = mapped_column(ForeignKey("factions.id", ondelete="CASCADE"), index=True)

    event_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String)
    target_id: Mapped[str | None] = mapped_column(String)
    target_npc_id: Mapped[str | None] = mapped_column(String, index=True)

    visibility: Mapped[str] = mapped_column(String, nullable=False, default="PUBLIC")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB)

    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NPCEventCursor(Base):
    __tablename__ = "npc_event_cursors"
    npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"), primary_key=True)
    last_processed_event_id: Mapped[int] = mapped_column(Integer, default=0)


class NPCPlayerState(Base):
    __tablename__ = "npc_player_state"
    npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"), primary_key=True)
    player_id: Mapped[str] = mapped_column(String, primary_key=True, default="player_1")

    affinity: Mapped[int] = mapped_column(Integer, default=0)
    trust: Mapped[int] = mapped_column(Integer, default=0)
    fear: Mapped[int] = mapped_column(Integer, default=0)
    respect: Mapped[int] = mapped_column(Integer, default=0)

    belief_tags_json: Mapped[list] = mapped_column(JSONB, default=list)
    belief_summary: Mapped[str] = mapped_column(Text, default="")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Quest(Base):
    __tablename__ = "quests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    stable_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    essential: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    objective_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    base_dialogue: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_hint: Mapped[str | None] = mapped_column(Text)
    completion_event_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    quest_dialogue_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class NPCQuest(Base):
    __tablename__ = "npc_quests"
    npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"), primary_key=True)
    quest_id: Mapped[str] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"), primary_key=True)

    minimum_affinity: Mapped[int] = mapped_column(Integer, default=-100)
    minimum_trust: Mapped[int] = mapped_column(Integer, default=-100)

    required_tags_json: Mapped[list] = mapped_column(JSONB, default=list)
    blocked_tags_json: Mapped[list] = mapped_column(JSONB, default=list)


class PlayerQuest(Base):
    __tablename__ = "player_quests"
    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    quest_id: Mapped[str] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="LOCKED")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    npc_id: Mapped[str] = mapped_column(ForeignKey("npcs.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[str] = mapped_column(String, index=True)
    track_id: Mapped[str | None] = mapped_column(String, index=True)
    player_message: Mapped[str | None] = mapped_column(Text)
    npc_response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
