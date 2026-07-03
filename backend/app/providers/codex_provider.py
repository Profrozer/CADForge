"""OpenAI's code-specific endpoint: the Responses API with Codex models."""

from .base import Provider, ProviderError, token_cap_from_error


class CodexProvider(Provider):
    name = "codex"
    label = "Codex (OpenAI Responses API)"
    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-5.1-codex"
    static_models = ["gpt-5.1-codex", "gpt-5.1-codex-mini", "gpt-5-codex"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        url = f"{self.base_url}/responses"
        payload = {
            "model": self.model,
            "instructions": system,
            "input": [{"role": "user", "content": user}],
            "max_output_tokens": max_tokens,
        }
        try:
            data = await self._post_json(url, self._headers(), payload)
        except ProviderError as e:
            cap = token_cap_from_error(str(e))
            if cap is None or cap >= payload["max_output_tokens"]:
                raise
            payload["max_output_tokens"] = cap
            data = await self._post_json(url, self._headers(), payload)
        parts: list[str] = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        parts.append(c.get("text", ""))
        if not parts:
            raise ProviderError(f"{self.label}: response contained no output text.")
        return "".join(parts)

    async def list_models(self) -> list[str]:
        try:
            data = await self._get_json(f"{self.base_url}/models", self._headers())
            models = sorted(m["id"] for m in data.get("data", []) if "codex" in m["id"])
            return models or list(self.static_models)
        except Exception:
            return list(self.static_models)
