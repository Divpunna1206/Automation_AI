from abc import ABC, abstractmethod

import httpx

from app.core.settings import Settings, get_settings


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return model output for generation tasks."""


class LocalLLMProvider(LLMProvider):
    """Deterministic fallback used when no API key is configured."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return user_prompt


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI-compatible provider.")

        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={
                "model": self.settings.openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    active_settings = settings or get_settings()
    if active_settings.llm_provider.lower() in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider(active_settings)
    return LocalLLMProvider()
