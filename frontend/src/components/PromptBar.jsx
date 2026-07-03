import { useState } from "react";

const STAGE_LABELS = {
  normalizing: "NORMALIZING PROMPT",
  spec: "SPEC LOCKED",
  generating: "GENERATING GEOMETRY CODE",
  executing: "VALIDATING SOLID",
  retrying: "SELF-CORRECTING",
  exporting: "RENDERING + EXPORTS",
};

export default function PromptBar({ busy, currentVersion, onSubmit, onNewPart }) {
  const [text, setText] = useState("");
  const iterating = currentVersion != null;

  const submit = () => {
    const prompt = text.trim();
    if (!prompt || busy) return;
    setText("");
    onSubmit(prompt);
  };

  return (
    <div className={`glass ${busy ? "glass-hot" : ""} p-3`}>
      {busy && (
        <div className="mb-2.5">
          <div className="flex items-center gap-3 font-mono text-[11px] text-line">
            <span className="relative inline-block w-24 h-[3px] bg-line/10 overflow-hidden rounded">
              <span className="scanline absolute inset-y-0 w-1/3 bg-line/80 rounded" />
            </span>
            <span className="tracking-[0.25em]">
              {STAGE_LABELS[busy.stage] ?? busy.stage.toUpperCase()}
            </span>
            {busy.detail && <span className="text-muted normal-case tracking-normal truncate">{busy.detail}</span>}
          </div>
        </div>
      )}
      <div className="flex items-end gap-3">
        <div className="flex-1">
          {iterating && (
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-[10px] text-amber tracking-widest">
                ITERATING ON v{currentVersion}
              </span>
              <button
                onClick={onNewPart}
                className="font-mono text-[10px] text-muted hover:text-line underline underline-offset-2 transition-colors"
              >
                start a new part instead
              </button>
            </div>
          )}
          <textarea
            rows={2}
            value={text}
            disabled={Boolean(busy)}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={
              iterating
                ? 'Refine this part — e.g. "make the holes 8mm" or "add a 90 degree bend"'
                : 'Describe a part — e.g. "L-bracket, 80mm x 60mm, 5mm thick, two 6mm bolt holes 40mm apart, 3mm fillets on outer corners"'
            }
            className="w-full resize-none bg-abyss/50 border border-line/15 rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted/60 focus:border-line/50 focus:outline-none disabled:opacity-50 transition-colors"
          />
        </div>
        <button
          onClick={submit}
          disabled={Boolean(busy) || !text.trim()}
          className="font-display font-semibold tracking-[0.2em] text-sm px-6 py-2.5 mb-1 rounded-lg border border-line/50 text-line hover:bg-line/12 hover:shadow-[0_0_18px_rgba(103,224,255,0.25)] disabled:opacity-35 disabled:cursor-not-allowed disabled:shadow-none transition-all"
        >
          {busy ? "FORGING…" : iterating ? "REFORGE" : "FORGE"}
        </button>
      </div>
    </div>
  );
}
