import { useCallback, useEffect, useRef, useState } from "react";
import { NPCS } from "@/constants/npcs";
import { api, NPCState, WorldContext } from "./useAwakenAPI";

function mockState(id: string): NPCState {
  const seeds: Record<string, Partial<NPCState>> = {
    varyon:  { affinity:  30, trust:  40, fear: -10, respect:  50, belief_tags: ["PLAYER_HELPED_TEMPLE"], belief_summary: "A pious soul, perhaps." },
    cassian: { affinity:  10, trust:  20, fear:   0, respect:  30, belief_tags: ["PLAYER_IS_NEW"],        belief_summary: "Watching this stranger." },
    elara:   { affinity:  -5, trust:  15, fear:   5, respect:  60, belief_tags: ["PLAYER_MAY_BE_GIFTED"], belief_summary: "There is potential here." },
    pell:    { affinity:  40, trust:  35, fear:  20, respect:  10, belief_tags: ["PLAYER_IS_HERO"],       belief_summary: "An idol to look up to." },
    mira:    { affinity:  20, trust:  10, fear:   0, respect:  20, belief_tags: ["PLAYER_HAS_COIN"],      belief_summary: "A potential customer." },
    bren:    { affinity:   5, trust:   0, fear:  30, respect:   0, belief_tags: ["PLAYER_IS_SCARY"],      belief_summary: "Best not to make eye contact." },
  };
  return { npc_id: id, affinity: 0, trust: 0, fear: 0, respect: 0, belief_tags: [], belief_summary: "Unknown.", ...seeds[id] };
}

export function useNPCStates(ctx: WorldContext | null) {
  const [states, setStates] = useState<Record<string, NPCState>>({});
  const [offline, setOffline] = useState(false);
  const [changed, setChanged] = useState<Record<string, number>>({});
  const prev = useRef<Record<string, NPCState>>({});

  const apply = useCallback((next: Record<string, NPCState>) => {
    const flags: Record<string, number> = {};
    for (const id of Object.keys(next)) {
      const a = prev.current[id];
      const b = next[id];
      if (
        !a ||
        a.affinity !== b.affinity ||
        a.trust !== b.trust ||
        a.fear !== b.fear ||
        a.respect !== b.respect ||
        (a.belief_tags?.join("|") !== b.belief_tags?.join("|"))
      ) {
        flags[id] = Date.now();
      }
    }
    prev.current = next;
    setStates(next);
    if (Object.keys(flags).length) setChanged((c) => ({ ...c, ...flags }));
  }, []);

  const refreshAll = useCallback(async () => {
    if (!ctx) return;
    try {
      const results = await Promise.all(
        NPCS.map((n) => api.getNpcState(ctx, n.id).catch(() => null))
      );
      if (results.every((r) => r === null)) throw new Error("all failed");
      const map: Record<string, NPCState> = {};
      results.forEach((r, i) => {
        map[NPCS[i].id] = r ?? mockState(NPCS[i].id);
      });
      setOffline(false);
      apply(map);
    } catch {
      setOffline(true);
      const map: Record<string, NPCState> = {};
      NPCS.forEach((n) => (map[n.id] = mockState(n.id)));
      apply(map);
    }
  }, [ctx, apply]);

  const refreshOne = useCallback(async (id: string) => {
    if (!ctx) return;
    try {
      const s = await api.getNpcState(ctx, id);
      apply({ ...prev.current, [id]: s });
      setOffline(false);
    } catch {
      // keep prior state
    }
  }, [ctx, apply]);

  // Seed mock data immediately so the panel isn't blank while loading
  useEffect(() => {
    if (!ctx) {
      const map: Record<string, NPCState> = {};
      NPCS.forEach((n) => (map[n.id] = mockState(n.id)));
      apply(map);
    }
  }, [ctx, apply]);

  useEffect(() => {
    if (!ctx) return;
    refreshAll();
    const t = setInterval(refreshAll, 5000);
    return () => clearInterval(t);
  }, [ctx, refreshAll]);

  return { states, offline, changed, refreshAll, refreshOne };
}
