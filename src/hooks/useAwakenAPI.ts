const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PLAYER_ID = "player_1";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// ── Shapes returned by the API ─────────────────────────────────────────────

export interface SeedResult {
  world_id: string;
  factions: Record<string, string>;   // stable_key → uuid
  npcs: Record<string, string>;        // stable_key → uuid
}

export interface NPCState {
  npc_id: string;
  affinity: number;
  trust: number;
  fear: number;
  respect: number;
  belief_tags: string[];               // remapped from belief_tags_json
  belief_summary: string;
  tone?: string;
}

export type TrackId = "greeting" | "identity" | "quest" | "opinion" | "world_lore";

export interface InteractResponse {
  session_id: string;
  npc_id: string;
  track: TrackId;
  dialogue: string;
  tone: string;
  quest?: { id: string; title: string; essential: boolean; status: string } | null;
  hints_provided?: string[];
}

// ── Context object threaded through the game ──────────────────────────────

export interface WorldContext {
  worldId: string;
  npcIds: Record<string, string>;      // stable_key → uuid  (e.g. varyon → uuid)
  factionIds: Record<string, string>;  // stable_key → uuid  (e.g. ashen_temple → uuid)
}

// ── API calls ──────────────────────────────────────────────────────────────

export const api = {
  /** Call once on mount. Re-seeds the world and returns IDs. */
  async seed(): Promise<SeedResult> {
    return req<SeedResult>("/seed", { method: "POST", body: "{}" });
  },

  /** GET /worlds/{worldId}/npcs/{npcUUID}/player-state */
  async getNpcState(ctx: WorldContext, npcKey: string): Promise<NPCState> {
    const npcId = ctx.npcIds[npcKey];
    if (!npcId) throw new Error(`unknown npc key: ${npcKey}`);
    const raw = await req<{
      npc_id: string; affinity: number; trust: number; fear: number;
      respect: number; belief_tags_json: string[]; belief_summary: string;
    }>(`/worlds/${ctx.worldId}/npcs/${npcId}/player-state?player_id=${PLAYER_ID}`);
    return {
      npc_id: raw.npc_id,
      affinity: raw.affinity,
      trust: raw.trust,
      fear: raw.fear,
      respect: raw.respect,
      belief_tags: raw.belief_tags_json ?? [],
      belief_summary: raw.belief_summary,
    };
  },

  /** POST /worlds/{worldId}/npcs/{npcUUID}/interact  — track-based dialogue */
  async interact(ctx: WorldContext, npcKey: string, track: TrackId): Promise<InteractResponse> {
    const npcId = ctx.npcIds[npcKey];
    if (!npcId) throw new Error(`unknown npc key: ${npcKey}`);
    return req<InteractResponse>(`/worlds/${ctx.worldId}/npcs/${npcId}/interact`, {
      method: "POST",
      body: JSON.stringify({ player_id: PLAYER_ID, track }),
    });
  },

  /** POST /worlds/{worldId}/events — requires faction_id */
  async fireEvent(
    ctx: WorldContext,
    factionKey: string,
    payload: { event_type: string; summary: string; importance: number; visibility: string },
  ) {
    const faction_id = ctx.factionIds[factionKey];
    if (!faction_id) throw new Error(`unknown faction key: ${factionKey}`);
    return req(`/worlds/${ctx.worldId}/events`, {
      method: "POST",
      body: JSON.stringify({ faction_id, ...payload }),
    });
  },

  /** POST /worlds/{worldId}/tick */
  async tick(ctx: WorldContext) {
    return req(`/worlds/${ctx.worldId}/tick`, { method: "POST", body: "{}" });
  },
};

export { BASE as API_BASE };
