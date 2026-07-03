"""Chat-completions-compatible providers: OpenAI, GLM (Zhipu), NVIDIA NIM."""

from .base import Provider, ProviderError, token_cap_from_error


class OpenAICompatProvider(Provider):
    # Newer OpenAI models reject "max_tokens"; other vendors still use it.
    token_param = "max_tokens"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            self.token_param: max_tokens,
        }
        url = f"{self.base_url}/chat/completions"
        try:
            data = await self._post_json(url, self._headers(), payload)
        except ProviderError as e:
            # Model caps completion tokens below our request — retry at its limit.
            cap = token_cap_from_error(str(e))
            if cap is None or cap >= payload[self.token_param]:
                raise
            payload[self.token_param] = cap
            data = await self._post_json(url, self._headers(), payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"{self.label}: unexpected response shape.")
        return content or ""

    async def list_models(self) -> list[str]:
        try:
            data = await self._get_json(f"{self.base_url}/models", self._headers())
            models = sorted(m["id"] for m in data.get("data", []))
            return models or list(self.static_models)
        except Exception:
            return list(self.static_models)


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"
    label = "OpenAI"
    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-5.1"
    token_param = "max_completion_tokens"
    static_models = ["gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o"]


class GLMProvider(OpenAICompatProvider):
    name = "glm"
    label = "GLM (Zhipu AI)"
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    default_model = "glm-4.6"
    static_models = ["glm-4.6", "glm-4.5", "glm-4.5-air", "glm-4-plus"]

    async def list_models(self) -> list[str]:
        # Zhipu has no /models endpoint on this path; use the curated list.
        return list(self.static_models)


class NvidiaProvider(OpenAICompatProvider):
    name = "nvidia"
    label = "NVIDIA NIM"
    default_base_url = "https://integrate.api.nvidia.com/v1"
    default_model = "qwen/qwen3-coder-480b-a35b-instruct"
    static_models = [
        "qwen/qwen3-coder-480b-a35b-instruct",
        "deepseek-ai/deepseek-v3.1",
        "moonshotai/kimi-k2-instruct",
        "meta/llama-3.3-70b-instruct",
    ]
