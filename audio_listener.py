"""
audio_listener.py — Escucha el audio del sistema en tiempo real.

Permite a la IA:
- Escuchar lo que suena en la PC (películas, Zoom, música)
- Transcribir con Whisper
- Detectar contexto (reunión, película, música)
- Ofrecer ayuda contextual

Requiere: sounddevice, openai-whisper (o faster-whisper)
"""
import io
import os
import queue
import tempfile
import threading
import time
from typing import Callable, Optional

import numpy as np

try:
    import sounddevice as sd
    _SD_OK = True
except ImportError:
    _SD_OK = False

try:
    import whisper
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
SAMPLE_RATE    = 16000   # Hz requerido por Whisper
CHUNK_SECONDS  = 5       # capturar en bloques de 5 segundos
SILENCE_THRESH = 0.01    # umbral de silencio


class AudioListener:
    """Escucha el audio del sistema y transcribe con Whisper."""

    def __init__(self, callback: Callable[[str, str], None]):
        """
        callback(texto_transcrito, contexto_detectado):
        - texto_transcrito: lo que se escuchó
        - contexto_detectado: 'reunion', 'pelicula', 'musica', 'general'
        """
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._model = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._ultimo_texto = ""
        self._contexto_actual = "general"

    def _cargar_modelo(self) -> bool:
        """Carga el modelo Whisper (tiny para velocidad)."""
        if not _WHISPER_OK:
            print("[AudioListener] Whisper no instalado. Ejecutá: pip install openai-whisper")
            return False
        try:
            print("[AudioListener] Cargando modelo Whisper tiny...")
            self._model = whisper.load_model("tiny")
            print("[AudioListener] ✓ Modelo cargado")
            return True
        except Exception as e:
            print(f"[AudioListener] Error cargando Whisper: {e}")
            return False

    def iniciar(self) -> bool:
        """Inicia la escucha en un hilo daemon."""
        if not _SD_OK:
            print("[AudioListener] sounddevice no instalado.")
            return False
        if not self._cargar_modelo():
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AudioListener"
        )
        self._thread.start()
        print("[AudioListener] ✓ Escuchando audio del sistema")
        return True

    def detener(self) -> None:
        self._running = False

    def _loop(self) -> None:
        """Loop principal de captura y transcripción."""
        while self._running:
            try:
                # Capturar audio del sistema (loopback)
                audio = self._capturar_chunk()
                if audio is None:
                    time.sleep(1)
                    continue

                # Verificar si hay sonido (no silencio)
                if np.abs(audio).mean() < SILENCE_THRESH:
                    continue

                # Transcribir
                texto = self._transcribir(audio)
                if texto and texto != self._ultimo_texto:
                    self._ultimo_texto = texto
                    contexto = self._detectar_contexto(texto)
                    self._contexto_actual = contexto
                    self._callback(texto, contexto)

            except Exception as e:
                time.sleep(2)

    def _capturar_chunk(self) -> Optional[np.ndarray]:
        """Captura un bloque de audio del sistema."""
        try:
            # Buscar dispositivo de loopback (WASAPI en Windows)
            dispositivos = sd.query_devices()
            loopback_idx = None

            for i, d in enumerate(dispositivos):
                nombre = d.get("name", "").lower()
                if "loopback" in nombre or "stereo mix" in nombre or "what u hear" in nombre:
                    loopback_idx = i
                    break

            if loopback_idx is None:
                # Usar micrófono por defecto como fallback
                loopback_idx = sd.default.device[0]

            audio = sd.rec(
                int(CHUNK_SECONDS * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=loopback_idx,
            )
            sd.wait()
            return audio.flatten()
        except Exception:
            return None

    def _transcribir(self, audio: np.ndarray) -> str:
        """Transcribe el audio con Whisper."""
        if self._model is None:
            return ""
        try:
            result = self._model.transcribe(
                audio,
                language="es",
                fp16=False,
                verbose=False,
            )
            return result.get("text", "").strip()
        except Exception:
            return ""

    def _detectar_contexto(self, texto: str) -> str:
        """Detecta el contexto basándose en el texto transcrito."""
        texto_lower = texto.lower()

        # Palabras clave de reunión/Zoom
        if any(p in texto_lower for p in [
            "reunión", "meeting", "zoom", "teams", "presentación",
            "agenda", "proyecto", "equipo", "cliente"
        ]):
            return "reunion"

        # Palabras clave de película/serie
        if any(p in texto_lower for p in [
            "capítulo", "episodio", "temporada", "película", "serie",
            "protagonista", "escena", "director"
        ]):
            return "pelicula"

        # Música
        if any(p in texto_lower for p in [
            "♪", "♫", "coro", "estribillo", "verso", "canción"
        ]):
            return "musica"

        return "general"

    def get_contexto_actual(self) -> str:
        return self._contexto_actual


# ---------------------------------------------------------------------------
# Integración con la IA
# ---------------------------------------------------------------------------

_listener: Optional[AudioListener] = None


def iniciar_escucha(callback_ia: Callable[[str], None]) -> bool:
    """
    Inicia la escucha de audio.
    callback_ia: función que recibe el mensaje de la IA sobre lo que escuchó.
    """
    global _listener

    def _on_audio(texto: str, contexto: str) -> None:
        if contexto == "reunion":
            msg = f"Escuché algo en tu reunión: '{texto[:80]}'. ¿Querés que te ayude a responder algo?"
        elif contexto == "pelicula":
            msg = f"Escuché algo de lo que estás viendo: '{texto[:60]}'. ¿De qué trata?"
        else:
            return  # No interrumpir para audio general

        callback_ia(msg)

    _listener = AudioListener(_on_audio)
    return _listener.iniciar()


def get_listener() -> Optional[AudioListener]:
    return _listener

_transcriber_model = None

def _get_transcriber_model():
    global _transcriber_model
    if _transcriber_model is None:
        if not _WHISPER_OK:
            raise RuntimeError("Whisper no está instalado.")
        _transcriber_model = whisper.load_model("tiny")
    return _transcriber_model


def transcribir_audio_bytes(audio_bytes: bytes) -> str:
    """Transcribe un archivo de audio recibido desde el frontend."""
    if not _WHISPER_OK:
        raise RuntimeError("Whisper no está instalado.")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        model = _get_transcriber_model()
        result = model.transcribe(tmp_path, language="es", fp16=False, verbose=False)
        return result.get("text", "").strip()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
