from .base import Provider


class AnthropicProvider(Provider):
    name = "anthropic"
    label = "Claude (Anthropic)"
    default_model = "claude-sonnet-4-6"
    static_models = [
        "claude-sonnet-4-6",
        "claude-sonnet-5",
        "claude-opus-4-8",
        "claude-opus-4-6",
        "claude-haiku-4-5",
    ]
    API = "https://api.anthropic.com/v1"

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        data = await self._post_json(
            f"{self.API}/messages",
            self._headers(),
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )

    async def list_models(self) -> list[str]:
        try:
            data = await self._get_json(f"{self.API}/models", self._headers())
            models = [m["id"] for m in data.get("data", [])]
            return models or list(self.static_models)
        except Exception:
            return list(self.static_models)
