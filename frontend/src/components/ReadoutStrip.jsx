import { fileUrl } from "../api.js";

const FORMATS = ["step", "stl", "dxf", "obj"];

// CMM-style readout: live dimensions + persistent export cluster.
export default function ReadoutStrip({ current, versions, onSelectVersion }) {
  const stats = current?.stats ?? {};
  const bbox = stats.bbox_mm;
  const volume = stats.volume_mm3;

  return (
    <div className="glass flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 font-mono text-xs">
      <Readout label="BBOX [MM]" value={bbox ? bbox.join(" × ") : "— × — × —"} />
      <Readout
        label="VOLUME"
        value={volume != null ? `${(volume / 1000).toFixed(2)} cm³` : "—"}
      />
      {versions.length > 1 && (
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] tracking-[0.25em] text-muted">REV</span>
          {versions.map((v) => (
            <button
              key={v.version}
              onClick={() => onSelectVersion(v)}
              className={`px-1.5 py-0.5 rounded border text-[10px] transition-colors ${
                current?.version === v.version
                  ? "border-amber/70 text-amber"
                  : "border-line/15 text-muted hover:border-line/40"
              }`}
            >
              v{v.version}
            </button>
          ))}
        </div>
      )}
      <div className="flex-1" />
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] tracking-[0.25em] text-muted mr-1">EXPORT</span>
        {FORMATS.map((fmt) => {
          const available = Boolean(current?.exports?.[fmt]);
          return available ? (
            <a
              key={fmt}
              href={fileUrl(current.part_id, current.version, fmt)}
              download
              className="px-2.5 py-1 rounded border border-line/30 text-line hover:bg-line/10 hover:border-line/60 uppercase tracking-widest text-[10px] transition-colors"
            >
              {fmt}
            </a>
          ) : (
            <span
              key={fmt}
              title={
                current
                  ? `${fmt.toUpperCase()} not available for this part` +
                    (fmt === "dxf" ? " (flat/sheet parts only)" : "")
                  : "Generate a part first"
              }
              className="px-2.5 py-1 rounded border border-line/8 text-muted/40 uppercase tracking-widest text-[10px] cursor-not-allowed select-none"
            >
              {fmt}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function Readout({ label, value }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[9px] tracking-[0.25em] text-muted">{label}</span>
      <span className="text-amber text-[11px]">{value}</span>
    </div>
  );
}
