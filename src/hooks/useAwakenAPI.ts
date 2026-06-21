const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WORLD = 1;
const PLAYER_ID = "player_1";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<T>;
}

export interface NPCState {
  npc_id: string;
  affinity: number;
  trust: number;
  fear: number;
  respect: number;
  belief_tags: string[];
  belief_summary: string;
  tone?: string;
}

export interface TalkResponse {
  npc_id: string;
  response: string;
  tone: string;
}

export const api = {
  async getNpcState(npcId: string): Promise<NPCState> {
    return req<NPCState>(`/worlds/${WORLD}/npcs/${npcId}/state`);
  },
  async talk(npcId: string, message: string): Promise<TalkResponse> {
    return req<TalkResponse>(`/worlds/${WORLD}/npcs/${npcId}/talk`, {
      method: "POST",
      body: JSON.stringify({ player_id: PLAYER_ID, message }),
    });
  },
  async fireEvent(payload: { event_type: string; summary: string; importance: number; visibility: string }) {
    return req(`/worlds/${WORLD}/events`, { method: "POST", body: JSON.stringify(payload) });
  },
  async tick() {
    return req(`/worlds/${WORLD}/tick`, { method: "POST", body: "{}" });
  },
};

export { BASE as API_BASE };
