"""
services/openai_client.py — Cliente OpenAI (motor reserva).
"""
from __future__ import annotations
import os
from typing import Dict, List

try:
    import openai as _openai
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False


class OpenAIClient:
    """Motor reserva — OpenAI (gpt-4o). Para cuando haya saldo."""

    MODEL = "gpt-4o"

    def __init__(self):
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _OPENAI_OK

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Envía mensajes a OpenAI y retorna la respuesta. Fail-silent."""
        if not self.is_available():
            return ""
        try:
            return self.generate(messages, timeout=kwargs.get("timeout", 60))
        except Exception:
            return ""

    def generate(self, messages: List[Dict], timeout: int = 60) -> str:
        if not _OPENAI_OK:
            raise RuntimeError("openai no instalado")
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        client = _openai.OpenAI(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self.MODEL, messages=messages, timeout=timeout,
        )
        return resp.choices[0].message.content.strip()
