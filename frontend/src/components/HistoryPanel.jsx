import { fileUrl } from "../api.js";

function timeAgo(ts) {
  const s = Math.max(1, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function HistoryPanel({ history, currentPartId, onSelect, onDelete }) {
  return (
    <aside className="glass w-72 shrink-0 hidden lg:flex flex-col min-h-0">
      <div className="px-4 py-3 border-b border-line/10 flex items-baseline justify-between">
        <h2 className="font-display text-sm font-semibold tracking-[0.22em]">
          ARCHIVE
        </h2>
        <span className="font-mono text-[10px] text-muted">
          {history.length} PART{history.length === 1 ? "" : "S"}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {history.length === 0 && (
          <p className="text-xs text-muted p-3 leading-relaxed">
            Nothing forged yet. Every generation lands here with a thumbnail —
            click one later to reload it for further iteration or re-download.
          </p>
        )}
        {history.map((item) => {
          const active = item.part_id === currentPartId;
          return (
            <div
              key={item.part_id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(item)}
              onKeyDown={(e) => e.key === "Enter" && onSelect(item)}
              className={`group relative flex gap-2.5 p-2 rounded-lg border cursor-pointer transition-colors ${
                active
                  ? "border-line/45 bg-line/8"
                  : "border-line/8 hover:border-line/25 hover:bg-line/4"
              }`}
            >
              <div className="size-14 shrink-0 rounded bg-abyss/70 border border-line/10 overflow-hidden flex items-center justify-center">
                {item.thumbnail ? (
                  <img
                    src={fileUrl(item.part_id, item.version, "png")}
                    alt=""
                    className="size-full object-cover"
                    onError={(e) => (e.target.style.display = "none")}
                  />
                ) : (
                  <span className="font-mono text-[9px] text-muted">v{item.version}</span>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs leading-snug line-clamp-2 text-ink/90">
                  {item.prompt}
                </p>
                <p className="font-mono text-[9px] text-muted mt-1 truncate">
                  <span className="text-amber/90">{item.model}</span>
                  {" · v"}
                  {item.version}
                  {" · "}
                  {timeAgo(item.created_at)}
                </p>
              </div>
              <button
                aria-label="Delete part"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(item.part_id);
                }}
                className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 text-muted hover:text-danger text-xs px-1 transition-opacity"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
