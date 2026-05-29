"""
services/gemini_client.py — Cliente Google Gemini (motor primario).
"""
from __future__ import annotations
import os
from typing import Dict, List

try:
    from google import genai as _genai
    from google.genai import types as _genai_types
    _GEMINI_OK = True
except ImportError:
    try:
        import google.generativeai as _genai
        _genai_types = None
        _GEMINI_OK = True
    except ImportError:
        _GEMINI_OK = False


class GeminiClient:
    """Motor primario — Google Gemini 2.0 Flash. Gratis, contexto enorme."""

    MODEL = "gemini-2.0-flash"

    def __init__(self):
        self._api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _GEMINI_OK

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """Envía mensajes a Gemini y retorna la respuesta. Fail-silent."""
        if not self.is_available():
            return ""
        try:
            return self.generate(messages, timeout=kwargs.get("timeout", 60))
        except Exception:
            return ""

    def generate(self, messages: List[Dict], timeout: int = 60) -> str:
        if not _GEMINI_OK:
            raise RuntimeError("google-genai no instalado: pip install google-genai")
        if not self._api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        system_parts  = [m["content"] for m in messages if m["role"] == "system"]
        chat_messages = [m for m in messages if m["role"] != "system"]
        system_instr  = "\n".join(system_parts) if system_parts else None
        last_msg      = chat_messages[-1]["content"] if chat_messages else ""

        if _genai_types is not None:
            client = _genai.Client(api_key=self._api_key)
            history = []
            for m in chat_messages[:-1]:
                role = "user" if m["role"] == "user" else "model"
                history.append(_genai_types.Content(
                    role=role, parts=[_genai_types.Part(text=m["content"])]
                ))
            config = _genai_types.GenerateContentConfig(
                system_instruction=system_instr,
            ) if system_instr else None
            contents = history + [_genai_types.Content(
                role="user", parts=[_genai_types.Part(text=last_msg)]
            )]
            response = client.models.generate_content(
                model=self.MODEL, contents=contents, config=config,
            )
            return response.text.strip()

        # Fallback SDK viejo
        _genai.configure(api_key=self._api_key)
        model = _genai.GenerativeModel(self.MODEL, system_instruction=system_instr)
        history = []
        for m in chat_messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            history.append({"role": role, "parts": [m["content"]]})
        chat = model.start_chat(history=history)
        response = chat.send_message(last_msg)
        return response.text.strip()
