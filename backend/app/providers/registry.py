from .anthropic_provider import AnthropicProvider
from .base import Provider, ProviderError
from .codex_provider import CodexProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compat import GLMProvider, NvidiaProvider, OpenAIProvider

PROVIDER_CLASSES: dict[str, type[Provider]] = {
    cls.name: cls
    for cls in (
        AnthropicProvider,
        OpenAIProvider,
        CodexProvider,
        GLMProvider,
        NvidiaProvider,
        OllamaProvider,
        MockProvider,
    )
}


def get_provider(name: str, api_key: str | None = None,
                 base_url: str | None = None, model: str | None = None) -> Provider:
    cls = PROVIDER_CLASSES.get(name)
    if cls is None:
        raise ProviderError(f"Unknown provider '{name}'.")
    return cls(api_key=api_key, base_url=base_url, model=model)


def provider_catalog() -> list[dict]:
    return [
        {
            "name": cls.name,
            "label": cls.label,
            "requires_key": cls.requires_key,
            "supports_base_url": cls.supports_base_url or cls.name == "ollama",
            "default_base_url": cls.default_base_url,
            "default_model": cls.default_model,
            "models": list(cls.static_models),
        }
        for cls in PROVIDER_CLASSES.values()
    ]
