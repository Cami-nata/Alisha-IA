"""
services/mistral_client.py — Cliente Mistral AI (motor de respaldo).
"""
from __future__ import annotations
import os
from typing import Dict, List

try:
    from mistralai.client import Mistral as _Mistral
    _MISTRAL_OK = True
except ImportError:
    _MISTRAL_OK = False


class MistralClient:
    """Motor de respaldo — Mistral AI (mistral-small-latest)."""

    MODEL = "mistral-small-latest"

    def __init__(self):
        self._api_key = os.getenv("MISTRAL_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _MISTRAL_OK

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Envía mensajes a Mistral y retorna la respuesta. Fail-silent."""
        if not self.is_available():
            return ""
        try:
            return self.generate(
                messages,
                timeout=kwargs.get("timeout", 30),
                temperature=kwargs.get("temperature", 0.4),
                max_tokens=kwargs.get("max_tokens", 800),
            )
        except Exception:
            return ""

    def generate(self, messages: List[Dict], timeout: int = 30,
                 temperature: float = 0.4, max_tokens: int = 800) -> str:
        if not _MISTRAL_OK:
            raise RuntimeError("mistralai no instalado: pip install mistralai")
        if not self._api_key:
            raise RuntimeError("MISTRAL_API_KEY no configurada")
        client = _Mistral(api_key=self._api_key)
        resp = client.chat.complete(
            model=self.MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
