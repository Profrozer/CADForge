// Thin API client. The generate call streams NDJSON progress events.

export async function getProviders() {
  const r = await fetch("/api/providers");
  if (!r.ok) throw new Error("Backend unreachable — is uvicorn running on :8000?");
  return r.json();
}

export async function testKey(body) {
  const r = await fetch("/api/providers/test", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function listModels(body) {
  const r = await fetch("/api/providers/models", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function getHistory() {
  const r = await fetch("/api/history");
  return r.json();
}

export async function getVersions(partId) {
  const r = await fetch(`/api/history/${partId}`);
  return r.json();
}

export async function deletePart(partId) {
  await fetch(`/api/history/${partId}`, { method: "DELETE" });
}

export async function postThumbnail(partId, version, dataUrl) {
  await fetch("/api/thumbnail", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ part_id: partId, version, data_url: dataUrl }),
  });
}

export function fileUrl(partId, version, fmt) {
  return `/api/files/${partId}/${version}/${fmt}`;
}

/** Stream a generation; onEvent fires for each NDJSON progress line. */
export async function generate(body, onEvent) {
  const r = await fetch("/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch { /* keep default */ }
    onEvent({ stage: "error", error: detail });
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
}
