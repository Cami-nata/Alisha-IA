"""voice.py — Solo síntesis de voz (TTS). Sin reconocimiento de voz."""
from tts_engine import speak  # noqa: F401 — re-exportado para compatibilidad

__all__ = ["speak"]
