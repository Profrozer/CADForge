import { useMemo, useState } from "react";
import { listModels, testKey } from "../api.js";
import { providerConfig } from "../settings.js";

export default function SettingsModal({ catalog, settings, onSave, onClose }) {
  const [draft, setDraft] = useState(() => JSON.parse(JSON.stringify(settings)));
  const [selected, setSelected] = useState(draft.defaultProvider);
  const [keyStatus, setKeyStatus] = useState(null); // {ok, error} | "testing"
  const [models, setModels] = useState(null);

  const info = useMemo(
    () => catalog.find((p) => p.name === selected) ?? catalog[0],
    [catalog, selected],
  );
  const cfg = providerConfig(draft, info.name);

  const patchProvider = (patch) => {
    setDraft((d) => ({
      ...d,
      providers: { ...d.providers, [info.name]: { ...providerConfig(d, info.name), ...patch } },
    }));
    setKeyStatus(null);
  };

  const runTest = async () => {
    setKeyStatus("testing");
    const res = await testKey({
      provider: info.name,
      api_key: cfg.apiKey || null,
      base_url: cfg.baseUrl || null,
      model: cfg.model || null,
    });
    setKeyStatus(res);
  };

  const fetchModels = async () => {
    setModels("loading");
    const res = await listModels({
      provider: info.name,
      api_key: cfg.apiKey || null,
      base_url: cfg.baseUrl || null,
    });
    setModels(res.models?.length ? res.models : info.models);
  };

  const modelOptions = models && models !== "loading" ? models : info.models;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-abyss/70 backdrop-blur-sm p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="glass glass-hot w-full max-w-2xl max-h-[90vh] overflow-y-auto p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold tracking-[0.22em] text-sm">
            SETTINGS
          </h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="text-muted hover:text-ink px-2 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* provider tabs */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {catalog.map((p) => (
            <button
              key={p.name}
              onClick={() => {
                setSelected(p.name);
                setKeyStatus(null);
                setModels(null);
              }}
              className={`font-mono text-[11px] px-2.5 py-1 rounded border transition-colors ${
                selected === p.name
                  ? "border-line/60 text-line bg-line/8"
                  : "border-line/12 text-muted hover:border-line/35"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="space-y-3 border border-line/10 rounded-lg p-4 bg-abyss/30">
          {info.requires_key ? (
            <Field label={`${info.label} API key`}>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={cfg.apiKey ?? ""}
                  onChange={(e) => patchProvider({ apiKey: e.target.value })}
                  placeholder="sk-…  (stored only in this browser)"
                  className="flex-1 input"
                />
                <button onClick={runTest} className="btn-secondary" disabled={keyStatus === "testing"}>
                  {keyStatus === "testing" ? "TESTING…" : "TEST"}
                </button>
              </div>
              {keyStatus && keyStatus !== "testing" && (
                <p className={`font-mono text-[11px] mt-1.5 ${keyStatus.ok ? "text-line" : "text-danger"}`}>
                  {keyStatus.ok ? "✓ key verified — a live round-trip succeeded" : `✗ ${keyStatus.error}`}
                </p>
              )}
            </Field>
          ) : (
            <div className="flex items-center gap-3">
              <p className="font-mono text-[11px] text-muted flex-1">
                {info.name === "ollama"
                  ? "No key needed — CADForge talks to your local Ollama server."
                  : "No key needed — this provider runs offline."}
              </p>
              <button onClick={runTest} className="btn-secondary" disabled={keyStatus === "testing"}>
                {keyStatus === "testing" ? "TESTING…" : "TEST CONNECTION"}
              </button>
              {keyStatus && keyStatus !== "testing" && (
                <span className={`font-mono text-[11px] ${keyStatus.ok ? "text-line" : "text-danger"}`}>
                  {keyStatus.ok ? "✓ reachable" : `✗ ${keyStatus.error}`}
                </span>
              )}
            </div>
          )}

          {(info.supports_base_url || info.default_base_url) && (
            <Field label="Base URL">
              <input
                type="text"
                value={cfg.baseUrl ?? ""}
                onChange={(e) => patchProvider({ baseUrl: e.target.value })}
                placeholder={info.default_base_url ?? ""}
                className="w-full input"
              />
            </Field>
          )}

          <Field label="Model">
            <div className="flex gap-2">
              <input
                type="text"
                list={`models-${info.name}`}
                value={cfg.model ?? ""}
                onChange={(e) => patchProvider({ model: e.target.value })}
                placeholder={info.default_model}
                className="flex-1 input"
              />
              <datalist id={`models-${info.name}`}>
                {modelOptions.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
              <button onClick={fetchModels} className="btn-secondary" disabled={models === "loading"}>
                {models === "loading" ? "…" : "FETCH MODELS"}
              </button>
            </div>
            {Array.isArray(models) && (
              <p className="font-mono text-[10px] text-muted mt-1">
                {models.length} models available — type to filter the list.
              </p>
            )}
          </Field>
        </div>

        {/* generation parameters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <Field label="Default provider">
            <select
              value={draft.defaultProvider}
              onChange={(e) => setDraft({ ...draft, defaultProvider: e.target.value })}
              className="w-full input"
            >
              {catalog.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Self-correct retries">
            <input
              type="number"
              min={0}
              max={5}
              value={draft.maxRetries}
              onChange={(e) => setDraft({ ...draft, maxRetries: Number(e.target.value) })}
              className="w-full input"
            />
          </Field>
          <Field label="Default units">
            <select
              value={draft.units}
              onChange={(e) => setDraft({ ...draft, units: e.target.value })}
              className="w-full input"
            >
              <option value="mm">millimeters</option>
              <option value="inch">inches</option>
            </select>
          </Field>
          <Field label="Exec timeout (s)">
            <input
              type="number"
              min={10}
              max={300}
              value={draft.timeoutSeconds}
              onChange={(e) => setDraft({ ...draft, timeoutSeconds: Number(e.target.value) })}
              className="w-full input"
            />
          </Field>
        </div>

        <p className="font-mono text-[10px] text-muted mt-4 leading-relaxed">
          Keys are stored in this browser's localStorage only and sent to your
          local backend per request — never persisted or logged server-side.
        </p>

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary">
            CANCEL
          </button>
          <button
            onClick={() => {
              onSave(draft);
              onClose();
            }}
            className="font-display text-xs font-semibold tracking-[0.2em] px-5 py-2 rounded border border-line/60 text-line hover:bg-line/12 transition-colors"
          >
            SAVE
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block font-mono text-[10px] tracking-[0.2em] text-muted uppercase mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
