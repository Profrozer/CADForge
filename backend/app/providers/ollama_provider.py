from .base import Provider, ProviderError


class OllamaProvider(Provider):
    name = "ollama"
    label = "Ollama (local)"
    requires_key = False
    supports_base_url = True
    default_base_url = "http://localhost:11434"
    default_model = "qwen2.5-coder:14b"
    static_models: list[str] = []

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        data = await self._post_json(
            f"{self.base_url}/api/chat",
            {"content-type": "application/json"},
            {
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"num_predict": max_tokens},
            },
        )
        msg = data.get("message") or {}
        return msg.get("content", "")

    async def list_models(self) -> list[str]:
        data = await self._get_json(f"{self.base_url}/api/tags")
        return [m["name"] for m in data.get("models", [])]

    async def test_key(self) -> None:
        # No key — a reachable server with at least one model counts as valid.
        models = await self.list_models()
        if not models:
            raise ProviderError(
                "Ollama is reachable but has no models. Run e.g. `ollama pull qwen2.5-coder:14b`."
            )
