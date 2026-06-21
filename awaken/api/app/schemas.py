from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------- World ----------

class WorldCreate(BaseModel):
    name: str
    description: str | None = None


class WorldOut(BaseModel):
    id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


# ---------- Faction ----------

class FactionCreate(BaseModel):
    name: str
    description: str | None = None
    behavior_prompt: str = ""


class FactionOut(FactionCreate):
    id: str
    world_id: str

    class Config:
        from_attributes = True


# ---------- NPC ----------

class NPCCreate(BaseModel):
    faction_id: str
    name: str
    role: str = ""
    behavior_prompt: str = ""
    base_friendliness: int = 0
    gossipiness: float = 0.5
    stubbornness: float = 0.5


class NPCUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    behavior_prompt: str | None = None
    base_friendliness: int | None = None
    gossipiness: float | None = None
    stubbornness: float | None = None


class NPCOut(BaseModel):
    id: str
    world_id: str
    faction_id: str
    name: str
    role: str
    behavior_prompt: str
    base_friendliness: int
    gossipiness: float
    stubbornness: float

    class Config:
        from_attributes = True


# ---------- Relationships ----------

class RelationshipCreate(BaseModel):
    from_npc_id: str
    to_npc_id: str
    relationship_type: str | None = None
    trust: float = 0.0
    affinity: float = 0.0


class RelationshipOut(RelationshipCreate):
    id: str

    class Config:
        from_attributes = True


# ---------- Entity ----------

class EntityCreate(BaseModel):
    name: str
    entity_type: str
    faction_id: str | None = None
    state_json: dict[str, Any] | None = None


class EntityUpdate(BaseModel):
    name: str | None = None
    faction_id: str | None = None
    state_json: dict[str, Any] | None = None


class EntityOut(BaseModel):
    id: str
    world_id: str
    faction_id: str | None
    name: str
    entity_type: str
    state_json: dict[str, Any] | None

    class Config:
        from_attributes = True


# ---------- Events ----------

Visibility = Literal["PUBLIC", "DIRECT", "SECRET"]


class EventCreate(BaseModel):
    faction_id: str
    event_type: str
    actor_id: str | None = None
    target_id: str | None = None
    target_npc_id: str | None = None
    visibility: Visibility = "PUBLIC"
    summary: str
    payload_json: dict[str, Any] | None = None
    importance: float = 0.5


class EventOut(BaseModel):
    id: int
    world_id: str
    faction_id: str
    event_type: str
    actor_id: str | None
    target_id: str | None
    target_npc_id: str | None
    visibility: str
    summary: str
    importance: float

    class Config:
        from_attributes = True


# ---------- Player State ----------

class PlayerStateOut(BaseModel):
    npc_id: str
    player_id: str
    affinity: int
    trust: int
    fear: int
    respect: int
    belief_tags_json: list[str] = Field(default_factory=list)
    belief_summary: str

    class Config:
        from_attributes = True


class PlayerStatePatch(BaseModel):
    affinity: int | None = None
    trust: int | None = None
    fear: int | None = None
    respect: int | None = None
    belief_tags: list[str] | None = None
    belief_summary: str | None = None


# ---------- Quests ----------

class QuestCreate(BaseModel):
    title: str
    description: str = ""
    essential: bool = False
    priority: int = 0
    objective_json: dict[str, Any] = Field(default_factory=dict)
    base_dialogue: str = ""
    base_hint: str | None = None


class QuestOut(QuestCreate):
    id: str
    world_id: str

    class Config:
        from_attributes = True


class NPCQuestAssign(BaseModel):
    minimum_affinity: int = -100
    minimum_trust: int = -100
    required_tags: list[str] = Field(default_factory=list)
    blocked_tags: list[str] = Field(default_factory=list)


# ---------- Interactions ----------

class TalkQuest(BaseModel):
    id: str
    title: str
    essential: bool
    status: str


TrackId = Literal["greeting", "identity", "quest", "opinion", "world_lore"]


class TrackOut(BaseModel):
    id: TrackId
    player_text: str
    guidance: str


class InteractionRequest(BaseModel):
    player_id: str = "player_1"
    track: TrackId


class InteractionResponse(BaseModel):
    session_id: str
    npc_id: str
    track: TrackId
    repeat_count: int
    dialogue: str
    tone: str
    quest: TalkQuest | None = None
    quest_decision: str | None = None
    quest_reason: str | None = None
    hints_provided: list[str] = Field(default_factory=list)
    debug: dict[str, Any] | None = None


# ---------- Sync ----------

class SyncResult(BaseModel):
    npc_id: str
    events_processed: int
    new_state: PlayerStateOut
