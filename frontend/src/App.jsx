import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deletePart,
  fileUrl,
  generate,
  getHistory,
  getProviders,
  getVersions,
  postThumbnail,
} from "./api.js";
import { loadSettings, providerConfig, saveSettings } from "./settings.js";
import HistoryPanel from "./components/HistoryPanel.jsx";
import PromptBar from "./components/PromptBar.jsx";
import ReadoutStrip from "./components/ReadoutStrip.jsx";
import SettingsModal from "./components/SettingsModal.jsx";
import SpecCard from "./components/SpecCard.jsx";
import TopBar from "./components/TopBar.jsx";
import Viewport from "./components/Viewport.jsx";

export default function App() {
  const [catalog, setCatalog] = useState([]);
  const [settings, setSettings] = useState(loadSettings);
  const [history, setHistory] = useState([]);
  const [current, setCurrent] = useState(null); // active version record
  const [versions, setVersions] = useState([]);
  const [busy, setBusy] = useState(null); // {stage, detail} | null
  const [liveSpec, setLiveSpec] = useState(null); // spec streamed during generation
  const [error, setError] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  const refreshHistory = useCallback(() => {
    getHistory().then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    getProviders()
      .then(setCatalog)
      .catch(() => setBackendDown(true));
    refreshHistory();
  }, [refreshHistory]);

  const activeProvider = useMemo(
    () => catalog.find((p) => p.name === settings.defaultProvider),
    [catalog, settings.defaultProvider],
  );
  const activeCfg = providerConfig(settings, settings.defaultProvider);
  const activeModel = activeCfg.model || activeProvider?.default_model || "—";

  const applySettings = (next) => {
    setSettings(next);
    saveSettings(next);
  };

  const loadPart = async (item) => {
    const all = await getVersions(item.part_id);
    setVersions(all);
    setCurrent(all[all.length - 1]);
    setLiveSpec(null);
    setError(null);
  };

  const selectVersion = (v) => {
    setCurrent(v);
    setLiveSpec(null);
  };

  const newPart = () => {
    setCurrent(null);
    setVersions([]);
    setLiveSpec(null);
    setError(null);
  };

  const removePart = async (partId) => {
    await deletePart(partId);
    if (current?.part_id === partId) newPart();
    refreshHistory();
  };

  const onSubmit = async (prompt) => {
    setError(null);
    setLiveSpec(null);
    setBusy({ stage: "normalizing" });
    const body = {
      prompt,
      provider: settings.defaultProvider,
      model: activeCfg.model || null,
      api_key: activeCfg.apiKey || null,
      base_url: activeCfg.baseUrl || null,
      part_id: current?.part_id ?? null,
      base_version: current?.version ?? null,
      settings: {
        max_retries: settings.maxRetries,
        units: settings.units,
        timeout_seconds: settings.timeoutSeconds,
      },
    };
    try {
      await generate(body, (event) => {
        if (event.stage === "spec") {
          setLiveSpec(event.spec);
          setBusy({ stage: "generating" });
        } else if (event.stage === "done") {
          setCurrent(event.part);
          getVersions(event.part.part_id).then(setVersions).catch(() => {});
          setBusy(null);
          refreshHistory();
        } else if (event.stage === "error") {
          setError(event.error);
          setBusy(null);
        } else {
          setBusy({ stage: event.stage, detail: event.detail });
        }
      });
    } catch (e) {
      setError(String(e.message ?? e));
    } finally {
      setBusy(null);
    }
  };

  const onSnapshot = useCallback(
    (dataUrl) => {
      if (!current || current.thumbnail) return;
      postThumbnail(current.part_id, current.version, dataUrl)
        .then(() => refreshHistory())
        .catch(() => {});
      setCurrent((c) => (c ? { ...c, thumbnail: "thumb.png" } : c));
    },
    [current, refreshHistory],
  );

  const stlUrl =
    current?.exports?.stl != null
      ? fileUrl(current.part_id, current.version, "stl")
      : null;

  return (
    <div className="h-full flex flex-col gap-3 p-3 relative">
      <TopBar
        providerLabel={activeProvider?.label ?? settings.defaultProvider}
        model={activeModel}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <div className="flex-1 flex gap-3 min-h-0">
        <HistoryPanel
          history={history}
          currentPartId={current?.part_id}
          onSelect={loadPart}
          onDelete={removePart}
        />
        <main className="flex-1 flex flex-col gap-3 min-w-0">
          <Viewport stlUrl={stlUrl} onSnapshot={onSnapshot} busy={busy} />
          <ReadoutStrip
            current={current}
            versions={versions}
            onSelectVersion={selectVersion}
          />
          <SpecCard
            spec={liveSpec ?? current?.spec}
            meta={current}
          />
          {backendDown && (
            <Banner tone="danger">
              Backend unreachable — start it with{" "}
              <code className="text-line">
                backend\.venv\Scripts\python -m uvicorn app.main:app
              </code>{" "}
              from the backend folder, then reload.
            </Banner>
          )}
          {error && (
            <Banner tone="danger" onDismiss={() => setError(null)}>
              {error}
            </Banner>
          )}
          <PromptBar
            busy={busy}
            currentVersion={current?.version ?? null}
            onSubmit={onSubmit}
            onNewPart={newPart}
          />
        </main>
      </div>
      {settingsOpen && (
        <SettingsModal
          catalog={catalog}
          settings={settings}
          onSave={applySettings}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  );
}

function Banner({ tone, children, onDismiss }) {
  return (
    <div
      className={`glass px-4 py-2.5 text-xs flex items-start gap-3 ${
        tone === "danger" ? "border-danger/40" : ""
      }`}
    >
      <span className="text-danger font-mono text-[10px] tracking-[0.25em] mt-0.5 shrink-0">
        FAULT
      </span>
      <div className="flex-1 text-ink/85 leading-relaxed break-words">{children}</div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-muted hover:text-ink shrink-0">
          ✕
        </button>
      )}
    </div>
  );
}
