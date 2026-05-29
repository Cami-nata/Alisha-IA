"""
avatar/avatar_state.py — Lector de estado compartido para el avatar.

Lee chibi_state.json y expone el estado actual al motion_controller.
No escribe — solo lee. La escritura la hace el core (assistant_state.py).
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR

STATE_FILE = DATA_DIR / "chibi_state.json"


@dataclass
class AvatarState:
    """Estado actual del avatar leído desde chibi_state.json."""
    estado:          str   = "neutral"   # emoción actual
    hablando:        bool  = False
    mouth_amplitude: float = 0.0         # 0.0–1.0 para lip-sync
    modo:            str   = "IDLE"      # IDLE / WORKING / THINKING / OVERLOADED
    tts_silenciado:  bool  = False
    media_actual:    dict  = field(default_factory=dict)

    # Campos calculados
    @property
    def is_thinking(self) -> bool:
        return self.modo == "THINKING" or self.estado in ("curiosidad", "preocupación")

    @property
    def is_working(self) -> bool:
        return self.modo == "WORKING"

    @property
    def is_sleeping(self) -> bool:
        return self.modo == "IDLE" and self.estado in ("cansancio", "sleep")

    @property
    def emotion_intensity(self) -> float:
        """0.0–1.0 según la intensidad de la emoción actual."""
        intensities = {
            "entusiasmo": 1.0, "alegría": 0.8, "curiosidad": 0.7,
            "preocupación": 0.6, "frustración": 0.5, "neutral": 0.3,
            "cansancio": 0.2,
        }
        return intensities.get(self.estado, 0.3)


class AvatarStateReader:
    """
    Lee chibi_state.json en un hilo daemon y mantiene el estado en memoria.
    Fail-silent: si el archivo no existe o está corrupto, usa defaults.
    """

    POLL_INTERVAL = 0.05  # 50ms = 20 Hz

    def __init__(self):
        self._state = AvatarState()
        self._lock  = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_mtime: float = 0.0

    def start(self) -> None:
        """Iniciar el lector en background."""
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AvatarStateReader"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def get(self) -> AvatarState:
        """Obtener copia del estado actual (thread-safe)."""
        with self._lock:
            return AvatarState(
                estado=self._state.estado,
                hablando=self._state.hablando,
                mouth_amplitude=self._state.mouth_amplitude,
                modo=self._state.modo,
                tts_silenciado=self._state.tts_silenciado,
                media_actual=dict(self._state.media_actual),
            )

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(self.POLL_INTERVAL)

    def _tick(self) -> None:
        """Leer el archivo solo si cambió (por mtime)."""
        if not STATE_FILE.exists():
            return

        try:
            mtime = STATE_FILE.stat().st_mtime
        except OSError:
            return

        if mtime <= self._last_mtime:
            return

        self._last_mtime = mtime

        try:
            raw = STATE_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return

        with self._lock:
            self._state.estado          = data.get("estado", "neutral")
            self._state.hablando        = bool(data.get("hablando", False))
            self._state.mouth_amplitude = float(data.get("mouth_amplitude", 0.0))
            self._state.modo            = data.get("modo", "IDLE")
            self._state.tts_silenciado  = bool(data.get("tts_silenciado", False))
            self._state.media_actual    = data.get("media_actual") or {}


# ── Singleton ──────────────────────────────────────────────────────────────────
_reader: Optional[AvatarStateReader] = None


def get_avatar_state_reader() -> AvatarStateReader:
    global _reader
    if _reader is None:
        _reader = AvatarStateReader()
        _reader.start()
    return _reader


def get_state() -> AvatarState:
    """Shortcut para obtener el estado actual."""
    return get_avatar_state_reader().get()
