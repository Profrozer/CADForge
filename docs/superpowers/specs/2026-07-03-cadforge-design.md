# CADForge — Design

Date: 2026-07-03
Status: Approved-by-spec (user provided a complete requirements spec; decisions below fill the remaining gaps)

## What it is

A local-first web app that turns plain-English descriptions of mechanical parts into
parametric CadQuery (Python) code via a user-selected AI provider, executes that code
server-side against OpenCASCADE, previews the solid in a Three.js viewport, and exports
STEP / STL / OBJ / DXF. Follow-up prompts edit the existing code (incremental iteration
with version history).

## Architecture

```
frontend/  (Vite + React JSX + Tailwind v4 + three)
   │  HTTP (NDJSON streaming for generation, JSON otherwise)
backend/   (FastAPI, Python 3.11 venv)
   ├─ providers/   provider-agnostic AI interface (raw httpx, no vendor SDKs)
   ├─ pipeline.py  normalize → generate → execute → (self-correct ×N) → export
   ├─ sandbox/     subprocess harness: no network, temp cwd, hard timeout
   ├─ exports     STEP/STL/OBJ always; DXF when a flat section can be taken
   └─ storage.py   sqlite (stdlib) history + files under backend/data/parts/
```

## Key decisions (gaps the spec left open)

1. **API keys** live in browser `localStorage` only. Every request carries the key for
   the selected provider in the JSON body; the backend uses it transiently and never
   persists or logs it (logging filters redact `api_key`). `/api/providers/test` validates
   a key with a minimal round-trip before saving.
2. **Provider layer**: one `OpenAICompatProvider` base (chat-completions shape) covers
   OpenAI, GLM (Zhipu v4), NVIDIA NIM, and Ollama (native /api/chat, no key). Codex uses
   OpenAI's Responses API endpoint (`/v1/responses`) — the code-specific endpoint —
   falling back conceptually to chat models the user picks. Anthropic uses the Messages
   API. All via `httpx`; interface = `normalize(prompt)`, `generate(spec, prior_code,
   instruction)`, `correct(code, error)`, `test_key()`, `list_models()`.
3. **Streaming status**: `POST /api/generate` returns a streamed NDJSON body; each line is
   `{"stage": "...", ...}` (`normalizing`, `generating`, `executing`, `retrying`,
   `exporting`, `done`/`error`). Frontend reads it with `fetch` + ReadableStream.
4. **Sandbox** (Windows has no seccomp): generated code runs in a separate Python
   subprocess via `harness.py`, which (a) monkey-patches `socket` to refuse connections,
   (b) runs in a scratch temp cwd, (c) receives a minimal environment, (d) is killed
   (whole tree) after a hard timeout (default 90 s). Geometry is validated with
   `shape.isValid()`; harness distinguishes syntax errors / geometry errors / no-result.
5. **Preview**: frontend loads the exported STL through Three.js `STLLoader` from
   `GET /api/files/{part}/{version}/{fmt}` — no custom mesh protocol.
6. **History**: sqlite (stdlib `sqlite3`) at `backend/data/cadforge.db`. A *part* groups
   *versions*; a follow-up prompt creates version N+1 with the prior version's code sent
   back to the model. Thumbnails are captured client-side from the viewport canvas and
   POSTed to attach to the version.
7. **Self-correction**: on execution failure the harness error is fed to
   `provider.correct()`; default max 2 retries, user-configurable in Settings.
8. **DXF**: attempted via a planar section of the solid at mid-height; if the export
   raises, the format is flagged unavailable for that part (UI grays out the button).

## Error handling

- Provider HTTP errors → surfaced as `error` stage with provider message.
- Code extraction strips markdown fences; empty/non-Python responses → error.
- Sandbox failure classes: `timeout`, `python_error`, `geometry_invalid`, `no_result`;
  each becomes a correction prompt with the traceback.

## Testing

- Backend: pytest covering sandbox execution of a known-good CadQuery snippet (no AI
  needed), failure classification, export formats, code-fence stripping, history CRUD.
- Frontend: production build must pass; manual smoke via mock provider.
- A built-in `mock` provider (canned L-bracket code) allows full end-to-end pipeline
  verification without any API key.
