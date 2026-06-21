import { useState } from "react";
import { NPCS } from "@/constants/npcs";
import { NPCState } from "@/hooks/useAwakenAPI";

interface Props {
  states: Record<string, NPCState>;
  changed: Record<string, number>;
  offline: boolean;
}

function Bar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.abs(value));
  const positive = value >= 0;
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[10px] uppercase tracking-widest text-amber-100/60">
        <span>{label}</span>
        <span className={positive ? "text-emerald-300" : "text-red-300"}>{value > 0 ? `+${value}` : value}</span>
      </div>
      <div className="relative h-1.5 w-full overflow-hidden bg-black/60">
        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-amber-700/40" />
        <div
          className={`absolute top-0 bottom-0 ${positive ? "bg-emerald-500/80 left-1/2" : "bg-red-500/80 right-1/2"}`}
          style={{ width: `${pct / 2}%` }}
        />
      </div>
    </div>
  );
}

function tagColor(tag: string) {
  const t = tag.toLowerCase();
  if (t.includes("help") || t.includes("hero") || t.includes("gift") || t.includes("donat")) return "border-emerald-500 bg-emerald-900/40 text-emerald-200";
  if (t.includes("thief") || t.includes("attack") || t.includes("scary") || t.includes("hostile")) return "border-red-500 bg-red-900/40 text-red-200";
  return "border-amber-700 bg-amber-900/30 text-amber-200";
}

export function NPCPanel({ states, changed, offline }: Props) {
  const [open, setOpen] = useState(false);

  const panel = (
    <aside
      className="pointer-events-auto fixed right-0 top-0 z-20 hidden h-full w-[320px] overflow-y-auto border-l-2 border-amber-700/50 bg-black/80 p-3 backdrop-blur md:block"
      style={{ boxShadow: "inset 0 0 60px rgba(0,0,0,0.8)" }}
    >
      <Header offline={offline} />
      <div className="space-y-3">
        {NPCS.map((npc) => {
          const s = states[npc.id];
          const pulse = changed[npc.id] && Date.now() - changed[npc.id] < 2000;
          return (
            <article
              key={npc.id}
              className={`border bg-gradient-to-b from-black/60 to-black/90 p-3 transition ${pulse ? "animate-pulse border-amber-300" : "border-amber-800/60"}`}
              style={{ boxShadow: pulse ? `0 0 20px ${npc.color}55` : "none" }}
            >
              <header className="mb-2 flex items-center gap-2">
                <span className="inline-block h-3 w-3 rounded-full" style={{ background: npc.color, boxShadow: `0 0 8px ${npc.color}` }} />
                <h3 className="flex-1 truncate font-serif text-sm text-amber-100" style={{ fontFamily: "Cinzel, serif" }}>
                  {npc.name}
                </h3>
              </header>
              {s ? (
                <>
                  <div className="space-y-1.5">
                    <Bar label="Affinity" value={s.affinity} />
                    <Bar label="Trust"    value={s.trust} />
                    <Bar label="Fear"     value={s.fear} />
                    <Bar label="Respect"  value={s.respect} />
                  </div>
                  {s.belief_tags?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {s.belief_tags.map((t) => (
                        <span key={t} className={`border px-1.5 py-0.5 text-[9px] uppercase tracking-wider ${tagColor(t)}`}>{t}</span>
                      ))}
                    </div>
                  )}
                  {s.belief_summary && (
                    <p className="mt-2 border-t border-amber-900/40 pt-2 text-xs italic text-amber-100/70">"{s.belief_summary}"</p>
                  )}
                </>
              ) : (
                <p className="text-xs text-amber-100/40">Loading…</p>
              )}
            </article>
          );
        })}
      </div>
    </aside>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="pointer-events-auto fixed right-3 top-3 z-30 border border-amber-600 bg-black/80 px-3 py-2 font-serif text-xs uppercase tracking-widest text-amber-200 md:hidden"
      >
        {open ? "Close" : "NPCs"}
      </button>
      {open && (
        <aside className="pointer-events-auto fixed inset-y-0 right-0 z-20 w-[85vw] max-w-[320px] overflow-y-auto border-l-2 border-amber-700/50 bg-black/95 p-3 md:hidden">
          <Header offline={offline} />
          {NPCS.map((npc) => {
            const s = states[npc.id];
            return (
              <div key={npc.id} className="mb-3 border border-amber-800/60 bg-black/60 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded-full" style={{ background: npc.color }} />
                  <h3 className="font-serif text-sm text-amber-100">{npc.name}</h3>
                </div>
                {s && (
                  <div className="space-y-1.5">
                    <Bar label="Affinity" value={s.affinity} />
                    <Bar label="Trust" value={s.trust} />
                    <Bar label="Fear" value={s.fear} />
                    <Bar label="Respect" value={s.respect} />
                  </div>
                )}
              </div>
            );
          })}
        </aside>
      )}
      {panel}
    </>
  );
}

function Header({ offline }: { offline: boolean }) {
  return (
    <div className="mb-3 border-b border-amber-700/50 pb-2">
      <h2 className="text-center font-serif text-sm uppercase tracking-[0.3em] text-amber-300" style={{ fontFamily: "Cinzel, serif" }}>
        NPC Belief States
      </h2>
      {offline && (
        <p className="mt-1 text-center text-[10px] uppercase tracking-widest text-red-400">Demo Mode · API Offline</p>
      )}
    </div>
  );
}
