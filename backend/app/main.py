import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from . import storage
from .pipeline import run_pipeline
from .providers.base import ProviderError
from .providers.registry import get_provider, provider_catalog
from .schemas import GenerateRequest, ModelsRequest, TestKeyRequest, ThumbnailRequest

# API keys travel in request bodies and are used transiently — never log bodies.
logging.getLogger("uvicorn.access").addFilter(
    lambda record: "api_key" not in record.getMessage()
)

app = FastAPI(title="CADForge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPORT_MEDIA = {
    "step": ("model.step", "application/step"),
    "stl": ("model.stl", "model/stl"),
    "obj": ("model.obj", "model/obj"),
    "dxf": ("model.dxf", "image/vnd.dxf"),
    "png": ("thumb.png", "image/png"),
}


@app.get("/api/providers")
def providers():
    return provider_catalog()


@app.post("/api/providers/test")
async def test_key(req: TestKeyRequest):
    try:
        provider = get_provider(req.provider, req.api_key, req.base_url, req.model)
        await provider.test_key()
    except ProviderError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@app.post("/api/providers/models")
async def list_models(req: ModelsRequest):
    try:
        provider = get_provider(req.provider, req.api_key, req.base_url)
        return {"models": await provider.list_models()}
    except ProviderError as e:
        return {"models": [], "error": str(e)}


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    try:
        provider = get_provider(req.provider, req.api_key, req.base_url, req.model)
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def stream():
        async for event in run_pipeline(req, provider):
            yield json.dumps(event) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/api/history")
def history():
    return storage.list_history()


@app.get("/api/history/{part_id}")
def part_versions(part_id: str):
    versions = storage.list_versions(part_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Unknown part")
    return versions


@app.delete("/api/history/{part_id}")
def delete_part(part_id: str):
    storage.delete_part(part_id)
    return {"ok": True}


@app.post("/api/thumbnail")
def thumbnail(req: ThumbnailRequest):
    try:
        storage.set_thumbnail(req.part_id, req.version, req.data_url)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.get("/api/files/{part_id}/{version}/{fmt}")
def download(part_id: str, version: int, fmt: str):
    if fmt not in EXPORT_MEDIA:
        raise HTTPException(status_code=404, detail="Unknown format")
    filename, media_type = EXPORT_MEDIA[fmt]
    path = storage.version_dir(part_id, version) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not available for this part")
    return FileResponse(
        path,
        media_type=media_type,
        filename=f"cadforge_{part_id}_v{version}.{fmt if fmt != 'png' else 'png'}",
    )
