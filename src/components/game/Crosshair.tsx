export function Crosshair() {
  return (
    <div className="pointer-events-none fixed inset-0 z-10 flex items-center justify-center">
      <div className="font-mono text-xl text-white/70 drop-shadow-[0_0_3px_rgba(0,0,0,0.9)]">+</div>
    </div>
  );
}
