"""Generation pipeline: normalize -> generate/edit -> execute -> self-correct -> save.

Yields NDJSON-ready dicts so the API layer can stream progress to the UI.
"""

import asyncio
import shutil
from collections.abc import AsyncIterator

from . import storage
from .providers.base import Provider, ProviderError
from .sandbox.runner import execute_cadquery
from .schemas import GenerateRequest


async def run_pipeline(req: GenerateRequest, provider: Provider) -> AsyncIterator[dict]:
    is_edit = req.part_id is not None and req.base_version is not None

    # 1. Normalize (initial generations only — edit instructions stay verbatim).
    spec: str | None = None
    try:
        if is_edit:
            base = storage.get_version(req.part_id, req.base_version)
            spec = f"Edit of v{req.base_version}: {req.prompt}"
        else:
            yield {"stage": "normalizing", "detail": "Restating your request as a structured spec"}
            spec = await provider.normalize(req.prompt, units=req.settings.units)
        yield {"stage": "spec", "spec": spec}

        # 2. Generate or edit code.
        yield {"stage": "generating", "detail": f"Asking {provider.label} ({provider.model}) for CadQuery code"}
        if is_edit:
            code = await provider.edit(base["code"], req.prompt)
        else:
            code = await provider.generate(spec)
    except ProviderError as e:
        yield {"stage": "error", "error": str(e)}
        return

    # 3. Execute in the sandbox, self-correcting on failure.
    part_id = req.part_id or storage.new_part_id()
    version = storage.next_version(part_id)
    out_dir = storage.version_dir(part_id, version)

    result: dict = {}
    for attempt in range(req.settings.max_retries + 1):
        yield {"stage": "executing",
               "detail": "Building solid geometry (OpenCASCADE)" +
                         (f" — retry {attempt}" if attempt else ""),
               "attempt": attempt}
        shutil.rmtree(out_dir, ignore_errors=True)
        result = await asyncio.to_thread(
            execute_cadquery, code, str(out_dir), req.settings.timeout_seconds
        )
        if result.get("ok"):
            break
        if attempt >= req.settings.max_retries:
            break
        yield {"stage": "retrying", "attempt": attempt + 1,
               "kind": result.get("kind"),
               "detail": f"Geometry failed ({result.get('kind')}); asking the model to fix it"}
        try:
            code = await provider.correct(code, result.get("error", "unknown error"))
        except ProviderError as e:
            yield {"stage": "error", "error": str(e)}
            return

    if not result.get("ok"):
        shutil.rmtree(out_dir, ignore_errors=True)
        yield {"stage": "error",
               "kind": result.get("kind"),
               "error": f"Geometry generation failed after "
                        f"{req.settings.max_retries + 1} attempt(s): "
                        f"{result.get('error', 'unknown error')}",
               "code": code}
        return

    # 4. Persist and report.
    yield {"stage": "exporting", "detail": "Registering STEP / STL / OBJ / DXF exports"}
    record = storage.save_version(
        part_id, version,
        prompt=req.prompt, spec=spec, code=code,
        provider=provider.name, model=provider.model,
        exports=result["exports"], stats=result.get("stats"),
    )
    record["export_errors"] = result.get("export_errors", {})
    yield {"stage": "done", "part": record}
