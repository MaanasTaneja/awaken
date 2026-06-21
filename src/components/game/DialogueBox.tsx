import { useState } from "react";
import { NPC } from "@/constants/npcs";
import { api, TrackId, InteractResponse, WorldContext } from "@/hooks/useAwakenAPI";

const TONE_COLOR: Record<string, string> = {
  friendly: "bg-emerald-700/80 text-emerald-100 border-emerald-400",
  neutral:  "bg-slate-700/80 text-slate-100 border-slate-400",
  cold:     "bg-sky-800/80 text-sky-100 border-sky-400",
  hostile:  "bg-red-800/80 text-red-100 border-red-400",
  afraid:   "bg-purple-800/80 text-purple-100 border-purple-400",
};

const TRACKS: { id: TrackId; label: string }[] = [
  { id: "greeting",   label: "Greetings"        },
  { id: "identity",   label: "Who are you?"     },
  { id: "quest",      label: "Any work for me?" },
  { id: "opinion",    label: "What do you think of me?" },
  { id: "world_lore", label: "Tell me of Aelryn" },
];

const MOCK_REPLIES: Record<string, Record<TrackId, string>> = {
  varyon:  {
    greeting:   "May the Ashen flame guide you, traveler.",
    identity:   "I am Varyon, Priest of the Ashen Temple. I tend the sacred fire.",
    quest:      "The Sacred Relic was stolen. Find it, and the Temple will reward you well.",
    opinion:    "You carry yourself with purpose. Whether that is virtue or arrogance remains to be seen.",
    world_lore: "Aelryn was built on the bones of a forgotten god. The flame keeps the dark at bay.",
  },
  cassian: {
    greeting:   "State your business. The Temple is watching.",
    identity:   "Cassian. Temple Guard. That is all you need to know.",
    quest:      "Not my place to hand out quests. Talk to Varyon.",
    opinion:    "I've seen a hundred strangers like you. Most regret it.",
    world_lore: "Stay out of trouble and Aelryn will treat you fine.",
  },
  elara: {
    greeting:   "Ah, a new face. The arcane always draws curious souls.",
    identity:   "Elara, Archmage of the Mages Guild. Knowledge is my craft.",
    quest:      "I could use a capable hand. The old observatory holds secrets I cannot reach alone.",
    opinion:    "There's a flicker of potential in you. Don't waste it on petty squabbles.",
    world_lore: "The ley lines under Aelryn are restless. Something stirs beneath the cobblestones.",
  },
  mira: {
    greeting:   "Welcome, welcome! Finest goods in all of Aelryn, right here.",
    identity:   "Mira, merchant. I deal in anything worth dealing in.",
    quest:      "I need a letter delivered to the Mages Guild. Discreetly. There's coin in it.",
    opinion:    "You look like someone who gets things done. I like that in a customer.",
    world_lore: "Trade's been rough with all this Temple drama. Bad for business, all of it.",
  },
  bren: {
    greeting:   "Morning. Or... afternoon. I've lost track.",
    identity:   "Bren. I carry things. That's about it.",
    quest:      "Please, I just want a quiet day. No quests.",
    opinion:    "You seem... intense. Please don't break anything.",
    world_lore: "The cobblestones are uneven near the well. Watch your step.",
  },
};

interface Line {
  track: TrackId;
  trackLabel: string;
  playerText: string;
  npcText: string;
  tone: string;
  quest?: InteractResponse["quest"];
}

interface Props {
  npc: NPC;
  ctx: WorldContext | null;
  offline: boolean;
  onClose: () => void;
  onTalk: (npcId: string) => void;
}

export function DialogueBox({ npc, ctx, offline, onClose, onTalk }: Props) {
  const [lines, setLines] = useState<Line[]>([]);
  const [pending, setPending] = useState(false);
  const [tone, setTone] = useState<string>("neutral");
  const [usedTracks, setUsedTracks] = useState<Set<TrackId>>(new Set());

  async function selectTrack(trackId: TrackId) {
    if (pending) return;
    const trackDef = TRACKS.find((t) => t.id === trackId)!;
    setPending(true);

    try {
      let npcText: string;
      let responseTone = "neutral";
      let quest: InteractResponse["quest"] = null;

      if (offline || !ctx) {
        await new Promise((r) => setTimeout(r, 350));
        npcText = MOCK_REPLIES[npc.id]?.[trackId] ?? "...";
      } else {
        const res = await api.interact(ctx, npc.id, trackId);
        npcText = res.dialogue;
        responseTone = res.tone || "neutral";
        quest = res.quest ?? null;
        onTalk(npc.id);
      }

      setTone(responseTone);
      setUsedTracks((s) => new Set([...s, trackId]));
      setLines((l) => [
        ...l,
        {
          track: trackId,
          trackLabel: trackDef.label,
          playerText: trackDef.label,
          npcText,
          tone: responseTone,
          quest,
        },
      ]);
    } catch {
      setLines((l) => [
        ...l,
        { track: trackId, trackLabel: trackDef.label, playerText: trackDef.label, npcText: "(...silence.)", tone: "neutral", quest: null },
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="pointer-events-auto fixed inset-x-0 bottom-0 z-30 flex justify-center px-4 pb-6">
      <div
        className="w-full max-w-3xl border-2 border-amber-600/70 bg-black/90 p-4 text-amber-50 shadow-[0_0_0_2px_#000,0_0_0_4px_#7a5a1c,0_0_30px_rgba(0,0,0,0.8)]"
        style={{ imageRendering: "pixelated" }}
      >
        <div className="flex gap-4">
          {/* Portrait */}
          <div
            className="relative h-36 w-28 shrink-0 overflow-hidden border-2 border-amber-700/80 bg-gradient-to-b from-stone-800 to-black"
            style={{ boxShadow: "inset 0 0 18px rgba(0,0,0,0.9)" }}
          >
            <img
              src={npc.sprite}
              alt={npc.name}
              className="absolute inset-0 h-full w-full object-cover object-top"
              style={{ filter: "contrast(1.1) saturate(0.9)" }}
            />
          </div>

          {/* Right side */}
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            {/* Header */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-baseline gap-3">
                <h2 className="font-serif text-xl tracking-wide text-amber-200" style={{ fontFamily: "Cinzel, serif" }}>
                  {npc.name}
                </h2>
                <span className="text-xs uppercase tracking-widest text-amber-100/50">{npc.factionLabel}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`border px-2 py-0.5 text-[10px] uppercase tracking-widest ${TONE_COLOR[tone] ?? TONE_COLOR.neutral}`}>
                  {tone}
                </span>
                <button
                  onClick={onClose}
                  className="border border-amber-700/70 bg-black/60 px-2 text-amber-300 hover:bg-amber-900/40"
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="my-1 h-px bg-gradient-to-r from-transparent via-amber-700/50 to-transparent" />

            {/* NPC response area */}
            <div className="max-h-28 min-h-[5rem] overflow-y-auto pr-1 text-sm leading-relaxed">
              {lines.length === 0 && pending && (
                <div className="text-amber-300/50 italic">...</div>
              )}
              {lines.map((l, i) => (
                <div key={i} className="mb-2">
                  <div className="text-amber-200/50 text-xs italic mb-0.5">› {l.playerText}</div>
                  <div className="text-amber-50">{l.npcText}</div>
                  {l.quest && (
                    <div className="mt-1 border-l-2 border-amber-600 pl-2 text-xs text-amber-300">
                      Quest: <strong>{l.quest.title}</strong> [{l.quest.status}]
                    </div>
                  )}
                </div>
              ))}
              {lines.length > 0 && pending && (
                <div className="text-amber-300/50 italic">...</div>
              )}
            </div>

            <div className="my-1 h-px bg-gradient-to-r from-transparent via-amber-700/30 to-transparent" />

            {/* Topic buttons */}
            <div className="flex flex-wrap gap-1.5">
              {TRACKS.map((t) => (
                <button
                  key={t.id}
                  disabled={pending}
                  onClick={() => selectTrack(t.id)}
                  className={`border px-2.5 py-1 font-serif text-xs transition disabled:opacity-40 ${
                    usedTracks.has(t.id)
                      ? "border-amber-800/40 bg-black/40 text-amber-400/60 hover:border-amber-600 hover:text-amber-300"
                      : "border-amber-600/70 bg-amber-950/60 text-amber-100 hover:border-amber-400 hover:text-amber-50"
                  }`}
                  style={{ fontFamily: "Cinzel, serif" }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
