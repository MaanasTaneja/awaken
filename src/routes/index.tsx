import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { GameCanvas } from "@/components/game/GameCanvas";
import { Crosshair } from "@/components/game/Crosshair";
import { NPCPanel } from "@/components/game/NPCPanel";
import { ActionHUD } from "@/components/game/ActionHUD";
import { DialogueBox } from "@/components/game/DialogueBox";
import { useNPCStates } from "@/hooks/useNPCStates";
import { NPCS } from "@/constants/npcs";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Aelryn — A Living Town" },
      { name: "description", content: "A demo dark-fantasy RPG town where NPC beliefs evolve as you act." },
    ],
  }),
  component: AelrynPage,
});

function AelrynPage() {
  const [nearby, setNearby] = useState<string | null>(null);
  const [activeNpc, setActiveNpc] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const { states, offline, changed, refreshAll, refreshOne } = useNPCStates();

  const onInteract = useCallback((id: string) => setActiveNpc(id), []);

  // ESC closes dialogue
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Escape") setActiveNpc(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const activeNpcObj = activeNpc ? NPCS.find((n) => n.id === activeNpc) ?? null : null;
  const paused = activeNpc !== null;

  return (
    <div className="fixed inset-0 overflow-hidden bg-black text-amber-50">
      <GameCanvas paused={paused} onNearbyChange={setNearby} onInteract={onInteract} />

      <Crosshair />

      {/* Talk prompt */}
      {nearby && !activeNpc && (
        <div className="pointer-events-none fixed left-1/2 top-[58%] z-10 -translate-x-1/2">
          <div
            className="border border-amber-500 bg-black/80 px-3 py-1.5 font-serif text-sm uppercase tracking-widest text-amber-200"
            style={{ fontFamily: "Cinzel, serif" }}
          >
            [E] Talk to {NPCS.find((n) => n.id === nearby)?.name}
          </div>
        </div>
      )}

      <ActionHUD offline={offline} onAfterEvent={refreshAll} />
      <NPCPanel states={states} changed={changed} offline={offline} />

      {/* Top-left title + offline toast */}
      <div className="pointer-events-none fixed left-4 top-4 z-10">
        <h1
          className="font-serif text-2xl tracking-[0.4em] text-amber-300 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]"
          style={{ fontFamily: "Cinzel, serif" }}
        >
          AELRYN
        </h1>
        <p className="mt-1 font-serif text-[10px] uppercase tracking-widest text-amber-100/60">
          WASD · Mouse Look · [E] Talk · [ESC] Free Cursor
        </p>
        {offline && (
          <div className="pointer-events-auto mt-2 inline-block border border-red-700 bg-black/80 px-2 py-1 text-[10px] uppercase tracking-widest text-red-300">
            API offline — running in demo mode
          </div>
        )}
      </div>

      {/* Start veil */}
      {!started && (
        <div
          onClick={() => setStarted(true)}
          className="fixed inset-0 z-40 flex cursor-pointer flex-col items-center justify-center bg-black/85 backdrop-blur-sm"
        >
          <h1
            className="mb-2 font-serif text-6xl tracking-[0.5em] text-amber-300"
            style={{ fontFamily: "Cinzel, serif", textShadow: "0 0 30px rgba(255,180,80,0.4)" }}
          >
            AELRYN
          </h1>
          <p className="mb-8 font-serif text-sm uppercase tracking-[0.4em] text-amber-100/70">
            A town that remembers.
          </p>
          <div className="border border-amber-600 bg-black/70 px-5 py-2 font-serif text-amber-200">
            ▸ Click to enter
          </div>
          <div className="mt-10 text-xs uppercase tracking-widest text-amber-100/40">
            WASD move · Mouse look · E to speak · ESC to release cursor
          </div>
        </div>
      )}

      {activeNpcObj && (
        <DialogueBox
          npc={activeNpcObj}
          offline={offline}
          onClose={() => setActiveNpc(null)}
          onTalk={refreshOne}
        />
      )}
    </div>
  );
}
