"""
services/groq_client.py — Cliente Groq (velocidad máxima).
"""
from __future__ import annotations
import os
from typing import Dict, List

try:
    from groq import Groq as _Groq
    _GROQ_OK = True
except ImportError:
    _GROQ_OK = False


class GroqClient:
    """Motor secundario — Groq (Llama 3 70B). Velocidad máxima."""

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        self._api_key = os.getenv("GROQ_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _GROQ_OK

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Envía mensajes a Groq y retorna la respuesta. Fail-silent."""
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
        if not _GROQ_OK:
            raise RuntimeError("groq no instalado: pip install groq")
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY no configurada")
        client = _Groq(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
