"""
services/ollama_client.py — Cliente Ollama (motor local, fallback sin internet).
"""
from __future__ import annotations
from typing import Dict, List

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from config.settings import OLLAMA_URL, MODEL


class OllamaClient:
    """Motor local — Ollama (llama3 / mistral). Fallback sin internet."""

    def __init__(self, model: str = MODEL, url: str = OLLAMA_URL):
        self.model = model
        self.url = url

    def is_available(self) -> bool:
        if not _REQUESTS_OK:
            return False
        try:
            r = _requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Envía mensajes a Ollama y retorna la respuesta. Fail-silent."""
        if not _REQUESTS_OK:
            return ""
        try:
            timeout = kwargs.get("timeout", 30)
            payload = {"model": self.model, "messages": messages, "stream": False}
            r = _requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "").strip()
        except Exception:
            return ""

    # Alias para compatibilidad con brain.py
    def generate(self, messages: List[Dict], timeout: int = 30) -> str:
        return self.chat(messages, timeout=timeout)
