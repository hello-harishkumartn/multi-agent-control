from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import get_settings


@dataclass
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


class ModelProvider(Protocol):
    def generate(self, system: str, prompt: str, context: list[dict[str, Any]]) -> ModelResponse: ...


class DeterministicProvider:
    def generate(self, system: str, prompt: str, context: list[dict[str, Any]]) -> ModelResponse:
        content = json.dumps({"summary": prompt[:300], "context_items": len(context)})
        return ModelResponse(content, (len(system) + len(prompt)) // 4, len(content) // 4, "demo-v1", "deterministic")


class GeminiProvider:
    def generate(self, system: str, prompt: str, context: list[dict[str, Any]]) -> ModelResponse:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        body = {"system_instruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt + "\n\nCONTEXT_DATA:\n" + json.dumps(context)}]}]}
        response = httpx.post(url, params={"key": settings.gemini_api_key}, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return ModelResponse(content, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0), settings.gemini_model, "gemini")


class OllamaProvider:
    def generate(self, system: str, prompt: str, context: list[dict[str, Any]]) -> ModelResponse:
        settings = get_settings()
        response = httpx.post(f"{settings.ollama_base_url}/api/chat", json={"model": settings.ollama_model, "stream": False, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt + "\n" + json.dumps(context)}]}, timeout=120)
        response.raise_for_status()
        data = response.json()
        return ModelResponse(data["message"]["content"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), settings.ollama_model, "ollama")


def get_provider(name: str | None = None) -> ModelProvider:
    provider = name or get_settings().model_provider
    return {"gemini": GeminiProvider, "ollama": OllamaProvider}.get(provider, DeterministicProvider)()

