import { useEffect, useState } from "react";
import { NPC } from "@/constants/npcs";
import { api, TalkResponse } from "@/hooks/useAwakenAPI";

const TONE_COLOR: Record<string, string> = {
  friendly: "bg-emerald-700/80 text-emerald-100 border-emerald-400",
  neutral:  "bg-slate-700/80 text-slate-100 border-slate-400",
  cold:     "bg-sky-800/80 text-sky-100 border-sky-400",
  hostile:  "bg-red-800/80 text-red-100 border-red-400",
  afraid:   "bg-purple-800/80 text-purple-100 border-purple-400",
};

interface Line { from: "npc" | "player"; text: string; tone?: string }

interface Props {
  npc: NPC;
  offline: boolean;
  onClose: () => void;
  onTalk: (npcId: string) => void;
}

export function DialogueBox({ npc, offline, onClose, onTalk }: Props) {
  const [lines, setLines] = useState<Line[]>([
    { from: "player", text: "Hello." },
  ]);
  const [pending, setPending] = useState(true);
  const [input, setInput] = useState("");
  const [tone, setTone] = useState<string>("neutral");

  // initial greeting
  useEffect(() => {
    void send("Hello");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send(message: string) {
    setPending(true);
    try {
      let res: TalkResponse;
      if (offline) {
        res = { npc_id: npc.id, response: mockReply(npc.id, message), tone: "neutral" };
      } else {
        res = await api.talk(npc.id, message);
      }
      setTone(res.tone || "neutral");
      setLines((l) => [...l, { from: "npc", text: res.response, tone: res.tone }]);
      onTalk(npc.id);
    } catch {
      setLines((l) => [...l, { from: "npc", text: "(...the world seems silent.)", tone: "neutral" }]);
    } finally {
      setPending(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || pending) return;
    setLines((l) => [...l, { from: "player", text: msg }]);
    setInput("");
    void send(msg);
  }

  const initial = npc.name.charAt(0);

  return (
    <div className="pointer-events-auto fixed inset-x-0 bottom-0 z-30 flex justify-center px-4 pb-6">
      <div
        className="w-full max-w-3xl border-2 border-amber-600/70 bg-black/85 p-4 text-amber-50 shadow-[0_0_0_2px_#000,0_0_0_4px_#7a5a1c,0_0_30px_rgba(0,0,0,0.8)]"
        style={{ imageRendering: "pixelated" }}
      >
        <div className="flex gap-4">
          {/* Portrait */}
          <div
            className="relative h-28 w-28 shrink-0 overflow-hidden border-2 border-amber-700/80 bg-gradient-to-b from-stone-800 to-black"
            style={{ boxShadow: "inset 0 0 18px rgba(0,0,0,0.9)" }}
          >
            <img
              src={npc.sprite}
              alt={npc.name}
              className="absolute inset-0 h-full w-full object-cover object-top"
              style={{ filter: "contrast(1.1) saturate(0.9)" }}
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black/70 px-1 py-0.5 text-center font-serif text-xs text-amber-200">
              {initial}
            </div>
          </div>

          {/* Body */}
          <div className="flex min-w-0 flex-1 flex-col">
            <div className="mb-1 flex items-center justify-between gap-3">
              <div className="flex items-baseline gap-3">
                <h2 className="font-serif text-xl tracking-wide text-amber-200" style={{ fontFamily: "Cinzel, serif" }}>
                  {npc.name}
                </h2>
                <span className="text-xs uppercase tracking-widest text-amber-100/60">{npc.factionLabel}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`border px-2 py-0.5 text-[10px] uppercase tracking-widest ${TONE_COLOR[tone] || TONE_COLOR.neutral}`}>
                  {tone}
                </span>
                <button
                  onClick={onClose}
                  className="border border-amber-700/70 bg-black/60 px-2 text-amber-300 hover:bg-amber-900/40"
                  aria-label="Close dialogue"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="my-2 h-px bg-gradient-to-r from-transparent via-amber-700/60 to-transparent" />

            <div className="max-h-40 min-h-[6rem] overflow-y-auto pr-1 text-sm leading-relaxed">
              {lines.map((l, i) => (
                <div key={i} className={l.from === "npc" ? "text-amber-50" : "text-amber-200/70 italic"}>
                  <span className="mr-2 text-amber-500/60">{l.from === "npc" ? "»" : ">"}</span>
                  {l.text}
                </div>
              ))}
              {pending && <div className="text-amber-300/50 italic">...</div>}
            </div>

            <form onSubmit={submit} className="mt-3 flex gap-2">
              <input
                autoFocus
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Speak..."
                className="flex-1 border border-amber-700/60 bg-black/70 px-3 py-2 font-serif text-amber-100 placeholder:text-amber-100/30 focus:border-amber-400 focus:outline-none"
              />
              <button
                type="submit"
                disabled={pending}
                className="border border-amber-600 bg-amber-900/40 px-4 py-2 font-serif uppercase tracking-widest text-amber-200 hover:bg-amber-800/60 disabled:opacity-40"
              >
                Say
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function mockReply(id: string, msg: string): string {
  const lower = msg.toLowerCase();
  if (lower.includes("relic")) return "The Sacred Relic is not a toy, traveler.";
  if (lower.includes("gold") || lower.includes("buy")) return "Coin speaks louder than words around here.";
  const replies: Record<string, string> = {
    varyon:  "May the Ash bless your path, stranger.",
    cassian: "Move along. The Temple watches.",
    elara:   "Curious. You carry a faint resonance.",
    pell:    "Oh! Hello! Are you... are you a real adventurer?",
    mira:    "Looking to trade? I've got wares worth a king's ransom.",
    bren:    "Please, sir, I haven't done nothin'.",
  };
  return replies[id] || "...";
}
