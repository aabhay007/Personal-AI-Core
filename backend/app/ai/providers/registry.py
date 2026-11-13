"""LLM Provider Registry and factory."""
from typing import Dict, Optional, Type
from app.ai.providers.base import LLMProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import settings

_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
}


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Retrieve an initialized LLM provider instance by name.
    
    Defaults to settings.DEFAULT_LLM_PROVIDER (e.g. 'groq').
    """
    selected_name = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower()

    provider_cls = _PROVIDERS.get(selected_name)
    if not provider_cls:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unsupported LLM provider '{selected_name}'. Available providers: {available}"
        )

    return provider_cls()
