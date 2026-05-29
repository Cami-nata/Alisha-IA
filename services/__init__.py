"""
services/ — Clientes LLM independientes. Uno por proveedor.

Interfaz común: is_available() -> bool, chat(messages, **kwargs) -> str
"""

from services.ollama_client import OllamaClient
from services.gemini_client import GeminiClient
from services.groq_client import GroqClient
from services.openai_client import OpenAIClient
from services.mistral_client import MistralClient

__all__ = [
    "OllamaClient",
    "GeminiClient",
    "GroqClient",
    "OpenAIClient",
    "MistralClient",
]
