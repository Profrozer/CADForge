export default function TopBar({ providerLabel, model, onOpenSettings }) {
  return (
    <header className="glass flex items-center gap-4 px-4 py-2.5">
      <div className="flex items-center gap-2.5">
        <svg width="26" height="26" viewBox="0 0 24 24">
          <path
            fill="none"
            stroke="#67E0FF"
            strokeWidth="1.4"
            d="M12 2 21 7v10l-9 5-9-5V7z M12 2v10 M21 7l-9 5-9-5"
          />
        </svg>
        <div>
          <h1 className="font-display font-bold text-lg leading-none tracking-[0.18em]">
            CADFORGE
          </h1>
          <p className="font-mono text-[9px] tracking-[0.3em] text-muted leading-tight mt-0.5">
            PROMPT → PARAMETRIC SOLID
          </p>
        </div>
      </div>
      <div className="flex-1" />
      <div
        className="hidden sm:flex items-center gap-2 font-mono text-xs px-3 py-1.5 rounded border border-line/15 bg-abyss/40"
        title="Active provider / model — change in Settings"
      >
        <span className="size-1.5 rounded-full bg-line/80 shadow-[0_0_6px_#67e0ff]" />
        <span className="text-muted">{providerLabel}</span>
        <span className="text-amber">{model}</span>
      </div>
      <button
        onClick={onOpenSettings}
        aria-label="Settings"
        className="p-2 rounded border border-line/15 hover:border-line/40 hover:bg-line/5 transition-colors"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d9e4f5" strokeWidth="1.6">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.01a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.01a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1z" />
        </svg>
      </button>
    </header>
  );
}
