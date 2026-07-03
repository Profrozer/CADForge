# CADForge

Prompt-to-CAD generator for engineering parts. Describe a mechanical part in
plain English; CADForge normalizes your request into a structured spec, has an
AI model of your choice write parametric **CadQuery** (Python) code, executes
it in a sandboxed subprocess against **OpenCASCADE**, previews the solid in a
Three.js viewport, and exports **STEP / STL / OBJ / DXF**. Follow-up prompts
edit the existing code incrementally, with full version history per part.

## Requirements

- **Python 3.10 – 3.12** (CadQuery ships wheels for these; 3.11 recommended)
- **Node.js 18+** with npm
- Windows, macOS, or Linux

## Setup

### 1. Backend (FastAPI + CadQuery)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt        # Linux/macOS: .venv/bin/pip
```

The CadQuery/OpenCASCADE wheel is large (~150 MB) — first install takes a few
minutes.

### 2. Frontend (React + Three.js + Tailwind)

```powershell
cd frontend
npm install
```

## Run (two terminals)

```powershell
# Terminal 1 — backend on :8000
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# Terminal 2 — frontend on :5173
cd frontend
npm run dev
```

Open **http://localhost:5173**. On Windows you can instead double-click
`run-backend.cmd` and `run-frontend.cmd` in the repo root.

## First flight (no API key needed)

The built-in **Mock (offline demo)** provider is selected by default — type
anything and press **FORGE** to see the whole pipeline (spec → code → geometry
→ preview → exports) run end-to-end with a demo L-bracket.

To generate real parts, open **Settings ⚙**:

1. Pick a provider tab, paste your API key, press **TEST** to validate it.
2. Optionally press **FETCH MODELS** and pick a model (each provider has a
   sensible default).
3. Set it as **Default provider** and save.

| Provider | Key | Notes |
|---|---|---|
| Claude (Anthropic) | `sk-ant-…` | default model `claude-sonnet-4-6` |
| OpenAI | `sk-…` | Chat Completions (GPT models) |
| Codex (OpenAI) | `sk-…` | Responses API with `gpt-*-codex` models |
| GLM (Zhipu AI) | Zhipu key | `glm-4.6` default |
| NVIDIA NIM | `nvapi-…` | curated + fetchable model list |
| Ollama (local) | none | just a base URL, default `http://localhost:11434` |

API keys live in your **browser's localStorage only**; each generation request
carries the key to your local backend, which uses it transiently and never
persists or logs it.

## Using it

- **Prompt** — e.g. *“L-bracket, 80mm x 60mm, 5mm thick, two 6mm bolt holes
  40mm apart, 3mm fillets on outer corners.”* The interpreted spec (including
  any assumptions the AI made) appears above the prompt so you can see what it
  understood; **VIEW CADQUERY** shows the generated code.
- **Iterate** — with a part loaded, the next prompt edits the *existing* code
  (“make the holes 8mm”). Each iteration is saved as a new revision; switch
  revisions with the `v1 v2 …` chips in the readout strip.
- **Export** — STEP / STL / OBJ always; DXF appears when a planar cross-section
  can be taken (flat/sheet parts). Buttons are grayed out until a valid solid
  exists.
- **Archive** — the left rail lists every part with thumbnail, model used,
  prompt and age; click to reload, ✕ to delete.
- If generation fails, the geometry error is automatically fed back to the
  same model for a self-correction pass (retry count configurable in
  Settings).

## Architecture

```
frontend/   Vite + React + Tailwind v4 + three.js (STL preview, orbit controls)
backend/    FastAPI
  app/providers/   provider-agnostic AI interface (Anthropic, OpenAI, Codex,
                   GLM, NVIDIA, Ollama, Mock) — raw HTTPS, no vendor SDKs
  app/pipeline.py  normalize → generate/edit → execute → self-correct → save
  app/sandbox/     subprocess harness: network disabled, temp cwd, hard timeout
  app/storage.py   sqlite history + files under backend/data/parts/
```

Generated code runs in a separate Python process started with `-I` (isolated
mode), with credential-looking environment variables stripped, in-process
socket access disabled, and a hard timeout (default 90 s). Geometry is
validated with OpenCASCADE (`isValid()`) before export.

## Tests

```powershell
cd backend
.venv\Scripts\python -m pytest tests -q
```

Covers sandbox execution/exports, failure classification (syntax, geometry,
timeout, no-result), the network block, code-fence extraction, storage, and
the full pipeline via the mock provider — no API keys needed.
