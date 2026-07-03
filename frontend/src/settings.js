// Per-user settings live in localStorage only — API keys never persist server-side.

const KEY = "cadforge.settings.v1";

export const defaultSettings = {
  defaultProvider: "mock",
  maxRetries: 2,
  units: "mm",
  timeoutSeconds: 90,
  providers: {}, // { [name]: { apiKey, baseUrl, model } }
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...defaultSettings };
    return { ...defaultSettings, ...JSON.parse(raw) };
  } catch {
    return { ...defaultSettings };
  }
}

export function saveSettings(settings) {
  localStorage.setItem(KEY, JSON.stringify(settings));
}

export function providerConfig(settings, name) {
  return settings.providers[name] ?? { apiKey: "", baseUrl: "", model: "" };
}
