import { useState } from "react";
import { EVENTS } from "@/constants/events";
import { api } from "@/hooks/useAwakenAPI";

interface Props {
  offline: boolean;
  onAfterEvent: () => void;
}

export function ActionHUD({ offline, onAfterEvent }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function fire(evId: string) {
    const ev = EVENTS.find((e) => e.id === evId)!;
    setBusy(evId);
    try {
      if (offline) {
        setToast(`(demo) ${ev.label}`);
      } else {
        await api.fireEvent({
          event_type: ev.event_type,
          summary: ev.summary,
          importance: ev.importance,
          visibility: ev.visibility,
        });
        await api.tick();
        setToast(`✓ ${ev.label}`);
      }
      onAfterEvent();
    } catch {
      setToast(`✗ Failed: ${ev.label}`);
    } finally {
      setBusy(null);
      setTimeout(() => setToast(null), 2500);
    }
  }

  return (
    <>
      <div
        className="pointer-events-auto fixed bottom-4 left-4 z-20 w-[260px] border-2 border-amber-700/60 bg-black/80 p-3"
        style={{ boxShadow: "0 0 0 2px #000, 0 0 0 4px #7a5a1c" }}
      >
        <h3
          className="mb-2 text-center font-serif text-[11px] uppercase tracking-[0.3em] text-amber-300"
          style={{ fontFamily: "Cinzel, serif" }}
        >
          Player Actions
        </h3>
        <div className="space-y-1.5">
          {EVENTS.map((e) => (
            <button
              key={e.id}
              disabled={busy !== null}
              onClick={() => fire(e.id)}
              className="block w-full border border-amber-800/70 bg-gradient-to-b from-amber-950/60 to-black/80 px-2 py-1.5 text-left font-serif text-xs text-amber-100 transition hover:border-amber-400 hover:text-amber-50 disabled:opacity-40"
            >
              <span className="mr-1 text-amber-500/70">›</span>
              {busy === e.id ? "..." : e.label}
            </button>
          ))}
        </div>
      </div>
      {toast && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-40 -translate-x-1/2 border border-amber-700 bg-black/90 px-4 py-2 font-serif text-sm text-amber-100">
          {toast}
        </div>
      )}
    </>
  );
}
