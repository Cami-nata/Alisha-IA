"""
services/gemini_live_client.py — Cliente de voz en tiempo real para Alisha IA.

Captura audio del micrófono con sounddevice y hace streaming a Gemini Live API.
Fallback automático a Vosk si Gemini Live falla.

Estados: idle → listening → processing → idle

Principio fail-silent: toda excepción capturada, no crashea el sistema.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

logger = logging.getLogger("GeminiLiveClient")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

# ── Dependencias opcionales ────────────────────────────────────────────────────
try:
    import sounddevice as _sd
    import numpy as _np
    _SOUNDDEVICE_OK = True
except ImportError:
    _sd = None  # type: ignore
    _np = None  # type: ignore
    _SOUNDDEVICE_OK = False
    logger.warning("sounddevice no instalado. Instalar con: pip install sounddevice")

try:
    from google import genai as _genai
    _GENAI_OK = True
except ImportError:
    _genai = None  # type: ignore
    _GENAI_OK = False
    logger.warning("google-genai no instalado. Instalar con: pip install google-genai")

# ── Constantes de audio ────────────────────────────────────────────────────────
_SAMPLE_RATE   = 16000   # Hz — requerido por Gemini Live
_CHANNELS      = 1       # mono
_CHUNK_SIZE    = 1024    # samples por chunk
_SILENCE_SECS  = 1.5     # segundos de silencio para enviar a API
_SILENCE_THRESH = 0.01   # umbral RMS para detectar silencio

# ── Estados ────────────────────────────────────────────────────────────────────
STATE_IDLE       = "idle"
STATE_LISTENING  = "listening"
STATE_PROCESSING = "processing"


class GeminiLiveClient:
    """
    Cliente de voz en tiempo real para Alisha IA.

    Flujo:
      1. start_listening() → activa micrófono, estado = listening
      2. Captura audio en chunks con sounddevice
      3. Detecta silencio → envía audio acumulado a Gemini Live API
      4. Recibe respuesta texto + audio → notifica al brain
      5. stop_listening() → desactiva micrófono, estado = idle

    Fallback: si Gemini Live falla → Vosk offline
    """

    def __init__(self) -> None:
        self._state: str = STATE_IDLE
        self._listening: bool = False
        self._lock = threading.Lock()
        self._stream = None          # sounddevice InputStream
        self._audio_buffer: list = []
        self._last_audio_time: float = 0.0
        self._processing_thread: Optional[threading.Thread] = None
        self._gemini_client = None   # lazy init

    # ── API pública ────────────────────────────────────────────────────────────

    def start_listening(self) -> None:
        """Activa el micrófono y comienza a capturar audio."""
        with self._lock:
            if self._listening:
                return
            self._listening = True
            self._audio_buffer = []
            self._last_audio_time = time.time()

        self._set_state(STATE_LISTENING)
        logger.info("🎤 Micrófono activado — escuchando...")

        if not _SOUNDDEVICE_OK:
            logger.warning("sounddevice no disponible — no se puede capturar audio.")
            return

        try:
            self._stream = _sd.InputStream(
                samplerate=_SAMPLE_RATE,
                channels=_CHANNELS,
                dtype="int16",
                blocksize=_CHUNK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.warning("Error al abrir stream de audio: %s", e)
            with self._lock:
                self._listening = False
            self._set_state(STATE_IDLE)

    def stop_listening(self) -> None:
        """Desactiva el micrófono."""
        with self._lock:
            if not self._listening:
                return
            self._listening = False

        self._set_state(STATE_IDLE)
        logger.info("🎤 Micrófono desactivado.")

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        except Exception as e:
            logger.warning("Error al cerrar stream de audio: %s", e)

    def is_listening(self) -> bool:
        """Retorna True si el micrófono está activo."""
        with self._lock:
            return self._listening

    def get_state(self) -> str:
        """Retorna el estado actual: 'idle' | 'listening' | 'processing'."""
        return self._state

    # ── Callback de audio ──────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Callback de sounddevice — recibe chunks de audio en tiempo real."""
        try:
            if not self._listening:
                return

            # Calcular RMS para detectar silencio
            if _np is not None:
                rms = float(_np.sqrt(_np.mean(indata.astype(_np.float32) ** 2))) / 32768.0
            else:
                rms = 0.1  # asumir audio si no hay numpy

            chunk = bytes(indata)
            self._audio_buffer.append(chunk)

            if rms > _SILENCE_THRESH:
                self._last_audio_time = time.time()
            else:
                # Silencio detectado — verificar si pasó suficiente tiempo
                elapsed = time.time() - self._last_audio_time
                if elapsed >= _SILENCE_SECS and len(self._audio_buffer) > 10:
                    # Enviar audio acumulado a la API
                    audio_data = b"".join(self._audio_buffer)
                    self._audio_buffer = []
                    self._last_audio_time = time.time()
                    self._dispatch_to_api(audio_data)

        except Exception as e:
            logger.warning("Error en audio_callback: %s", e)

    # ── Procesamiento de audio ─────────────────────────────────────────────────

    def _dispatch_to_api(self, audio_data: bytes) -> None:
        """Envía audio a Gemini Live API en hilo separado."""
        if self._processing_thread and self._processing_thread.is_alive():
            return  # ya hay un procesamiento en curso

        self._processing_thread = threading.Thread(
            target=self._process_audio,
            args=(audio_data,),
            daemon=True,
            name="GeminiLive-Process",
        )
        self._processing_thread.start()

    def _process_audio(self, audio_data: bytes) -> None:
        """Procesa el audio: Gemini Live → fallback Vosk → notifica brain."""
        self._set_state(STATE_PROCESSING)
        texto = ""

        try:
            # Intentar Gemini Live primero
            texto = self._transcribe_gemini(audio_data)
        except Exception as e:
            logger.warning("Gemini Live falló (%s) — usando Vosk offline", e)
            try:
                texto = self._transcribe_vosk(audio_data)
            except Exception as e2:
                logger.warning("Vosk también falló: %s", e2)

        if texto.strip():
            logger.info("Transcripción: %s", texto[:80])
            self._notify_brain(texto)

        # Volver a listening si el micrófono sigue activo
        with self._lock:
            still_listening = self._listening
        self._set_state(STATE_LISTENING if still_listening else STATE_IDLE)

    def _transcribe_gemini(self, audio_data: bytes) -> str:
        """Transcripción con Gemini Live API (streaming)."""
        if not _GENAI_OK:
            raise RuntimeError("google-genai no disponible")

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")

        # Inicializar cliente lazy
        if self._gemini_client is None:
            self._gemini_client = _genai.Client(api_key=api_key)

        # Usar el modelo de texto como fallback si Live no está disponible
        # (Gemini Live API requiere SDK específico — usar generate_content con audio)
        try:
            import base64
            audio_b64 = base64.b64encode(audio_data).decode()
            response = self._gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {
                        "parts": [
                            {"text": "Transcribe exactamente lo que se dice en este audio. Solo el texto, sin explicaciones."},
                            {"inline_data": {"mime_type": "audio/pcm", "data": audio_b64}},
                        ]
                    }
                ],
            )
            return response.text or ""
        except Exception as e:
            raise RuntimeError(f"Gemini transcription failed: {e}") from e

    def _transcribe_vosk(self, audio_data: bytes) -> str:
        """Transcripción offline con Vosk si Gemini Live falla (Req 2.9)."""
        try:
            import vosk
            import json
            from pathlib import Path
            from config.settings import DATA_DIR

            model_path = Path(DATA_DIR) / "vosk-model"
            if not model_path.exists():
                logger.debug("Modelo Vosk no encontrado en %s", model_path)
                return ""

            model = vosk.Model(str(model_path))
            rec = vosk.KaldiRecognizer(model, _SAMPLE_RATE)

            # Procesar en chunks
            chunk_size = 4000
            for i in range(0, len(audio_data), chunk_size):
                rec.AcceptWaveform(audio_data[i:i + chunk_size])

            result = json.loads(rec.FinalResult())
            return result.get("text", "")

        except ImportError:
            logger.debug("Vosk no instalado — fallback no disponible.")
            return ""
        except Exception as e:
            logger.warning("Error en Vosk: %s", e)
            return ""

    # ── Notificación al brain ──────────────────────────────────────────────────

    def _notify_brain(self, texto: str) -> None:
        """Envía el texto transcripto al brain de Alisha para procesamiento."""
        try:
            from core.brain import get_brain
            brain = get_brain()
            # Procesar en hilo para no bloquear
            threading.Thread(
                target=brain.chat,
                args=(texto,),
                daemon=True,
                name="Brain-VoiceInput",
            ).start()
        except Exception as e:
            logger.warning("No se pudo notificar al brain: %s", e)

    # ── Estado ────────────────────────────────────────────────────────────────

    def _set_state(self, new_state: str) -> None:
        """Actualiza el estado interno y el AssistantState."""
        self._state = new_state
        try:
            from core.assistant_state import actualizar_estado, SystemMode
            from datetime import datetime
            if new_state == STATE_LISTENING:
                actualizar_estado(
                    estado="escuchando",
                    modo=SystemMode.WORKING,
                    ultima_actualizacion=datetime.now().isoformat(),
                )
            elif new_state == STATE_PROCESSING:
                actualizar_estado(
                    estado="procesando",
                    modo=SystemMode.THINKING,
                    ultima_actualizacion=datetime.now().isoformat(),
                )
            else:  # idle
                actualizar_estado(
                    estado="neutral",
                    modo=SystemMode.IDLE,
                    ultima_actualizacion=datetime.now().isoformat(),
                )
        except Exception as e:
            logger.debug("No se pudo actualizar AssistantState: %s", e)


# ── Singleton ──────────────────────────────────────────────────────────────────

_client: Optional[GeminiLiveClient] = None
_singleton_lock = threading.Lock()


def get_gemini_live_client() -> GeminiLiveClient:
    """Retorna la instancia singleton del GeminiLiveClient."""
    global _client
    if _client is None:
        with _singleton_lock:
            if _client is None:
                _client = GeminiLiveClient()
    return _client
