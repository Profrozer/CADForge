import re

import httpx

from . import prompts


class ProviderError(Exception):
    """A provider call failed in a way the user should see."""


def extract_code(text: str) -> str:
    """Pull CadQuery source out of a model response.

    Prefers fenced ```python blocks (longest wins if several); falls back to
    the raw text. Also strips <think>...</think> blocks some local models emit.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.DOTALL)
    code = max(blocks, key=len).strip() if blocks else text.strip()
    if not code:
        raise ProviderError("The model returned an empty response.")
    if "cadquery" not in code and "cq." not in code:
        raise ProviderError(
            "The model did not return CadQuery code. Response started with: "
            + code[:200]
        )
    return code


class Provider:
    """Shared interface every AI backend implements.

    Downstream logic only ever calls normalize/generate/edit/correct/
    test_key/list_models, so switching providers changes nothing else.
    """

    name: str = ""
    label: str = ""
    requires_key: bool = True
    supports_base_url: bool = False
    default_base_url: str | None = None
    default_model: str = ""
    static_models: list[str] = []

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or self.default_base_url or "").rstrip("/") or None
        self.model = model or self.default_model
        if self.requires_key and not self.api_key:
            raise ProviderError(f"{self.label} requires an API key. Add one in Settings.")

    # -- transport (implemented per provider) --------------------------------

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        return list(self.static_models)

    async def test_key(self) -> None:
        # Reasoning models (gpt-5.x, o-series, Qwen3, GLM thinking) spend tokens
        # on internal reasoning before any visible output; a tiny cap makes them
        # 400 with "max output reached". Caps only bill actual usage, so keep
        # this generous.
        await self.chat("Reply with the single word OK.", "ping", max_tokens=2048)

    # -- pipeline operations (shared) ----------------------------------------

    async def normalize(self, prompt: str, units: str = "mm") -> str:
        return (await self.chat(
            prompts.NORMALIZE_SYSTEM.format(units=units), prompt, max_tokens=6000
        )).strip()

    async def generate(self, spec: str) -> str:
        user = f"Specification:\n\n{spec}\n\nWrite the CadQuery program."
        return extract_code(await self.chat(prompts.GENERATE_SYSTEM, user, max_tokens=16000))

    async def edit(self, prior_code: str, instruction: str) -> str:
        user = (
            f"Existing program:\n\n```python\n{prior_code}\n```\n\n"
            f"Modification instruction: {instruction}\n\n"
            "Return the full modified program."
        )
        return extract_code(await self.chat(prompts.EDIT_SYSTEM, user, max_tokens=16000))

    async def correct(self, code: str, error: str) -> str:
        user = (
            f"Program:\n\n```python\n{code}\n```\n\n"
            f"Error:\n\n```\n{error}\n```\n\n"
            "Return the full corrected program."
        )
        return extract_code(await self.chat(prompts.CORRECT_SYSTEM, user, max_tokens=16000))

    # -- helpers --------------------------------------------------------------

    async def _post_json(self, url: str, headers: dict, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                r = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: connection failed ({e}).") from e
        if r.status_code >= 400:
            raise ProviderError(f"{self.label} error {r.status_code}: {_err_detail(r)}")
        return r.json()

    async def _get_json(self, url: str, headers: dict | None = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=headers or {})
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: connection failed ({e}).") from e
        if r.status_code >= 400:
            raise ProviderError(f"{self.label} error {r.status_code}: {_err_detail(r)}")
        return r.json()


_CAP_RE = re.compile(r"at most (\d+)")


def token_cap_from_error(message: str) -> int | None:
    """Pull a model's completion-token ceiling out of a 'too large' 400.

    Providers phrase it as '...supports at most 16384 completion tokens...'.
    Returns the number so the caller can retry clamped, or None if absent.
    """
    m = _CAP_RE.search(message)
    return int(m.group(1)) if m else None


def _err_detail(r: httpx.Response) -> str:
    try:
        body = r.json()
        err = body.get("error", body)
        if isinstance(err, dict):
            return str(err.get("message") or err)
        return str(err)[:300]
    except Exception:
        return r.text[:300]
