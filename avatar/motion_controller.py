"""
avatar/motion_controller.py — Controlador de movimiento motriz del avatar.

Responsabilidades:
- Respiración suave
- Parpadeo natural
- Mirada aleatoria controlada
- Micro inclinaciones de cabeza
- Reacción al hablar (lip-sync)
- Reacción al pensar
- Reacción al recibir Telegram
- Transición suave entre emociones

Escribe parámetros Live2D en chibi_state.json para que
cabina_virtual.py los lea en su loop de 60fps.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR
from avatar.avatar_state import get_state, AvatarState

STATE_FILE = DATA_DIR / "chibi_state.json"

# ── Rangos seguros de parámetros Live2D ───────────────────────────────────────
# Todos los valores se clampean antes de escribir para evitar el bug de
# acumulación de transparencia / latido visual.
PARAM_RANGES = {
    "ParamEyeLOpen":    (0.0, 1.0),
    "ParamEyeROpen":    (0.0, 1.0),
    "ParamAngleX":      (-30.0, 30.0),
    "ParamAngleY":      (-30.0, 30.0),
    "ParamAngleZ":      (-30.0, 30.0),
    "ParamBodyAngleX":  (-10.0, 10.0),
    "ParamBodyAngleY":  (-10.0, 10.0),
    "ParamBreath":      (0.0, 1.0),
    "ParamMouthOpenY":  (0.0, 1.0),
    "opacity":          (0.0, 1.0),
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class MotionParams:
    """Parámetros de movimiento actuales del avatar."""
    eye_l_open:   float = 1.0
    eye_r_open:   float = 1.0
    angle_x:      float = 0.0
    angle_y:      float = 0.0
    angle_z:      float = 0.0
    body_x:       float = 0.0
    body_y:       float = 0.0
    breath:       float = 0.0
    mouth_open:   float = 0.0
    opacity:      float = 1.0


class MotionController:
    """
    Controlador de movimiento motriz del avatar.
    Corre en un hilo daemon a 30fps.
    """

    FPS           = 30
    FRAME_TIME    = 1.0 / FPS

    # Tiempos de parpadeo (segundos)
    BLINK_MIN     = 2.5
    BLINK_MAX     = 6.0
    BLINK_SPEED   = 0.08   # duración del parpadeo

    # Respiración
    BREATH_PERIOD = 4.0    # segundos por ciclo

    # Mirada aleatoria
    GAZE_CHANGE_MIN = 3.0
    GAZE_CHANGE_MAX = 8.0
    GAZE_MAX_X      = 15.0
    GAZE_MAX_Y      = 10.0

    def __init__(self):
        self._params  = MotionParams()
        self._target  = MotionParams()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock    = threading.Lock()

        # Timers internos
        self._t0           = time.time()
        self._next_blink   = self._t0 + random.uniform(self.BLINK_MIN, self.BLINK_MAX)
        self._blinking     = False
        self._blink_phase  = 0.0
        self._next_gaze    = self._t0 + random.uniform(self.GAZE_CHANGE_MIN, self.GAZE_CHANGE_MAX)
        self._gaze_target_x = 0.0
        self._gaze_target_y = 0.0

        # Estado emocional previo (para detectar cambios)
        self._last_estado  = "neutral"
        self._last_hablando = False

    def start(self) -> None:
        self._running = True
        self._t0 = time.time()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="MotionController"
        )
        self._thread.start()
        print("[MotionController] ✓ Iniciado a 30fps")

    def stop(self) -> None:
        self._running = False

    # ── Loop principal ────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            t_start = time.time()
            try:
                self._tick()
            except Exception:
                pass
            elapsed = time.time() - t_start
            sleep_time = self.FRAME_TIME - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _tick(self) -> None:
        now = time.time()
        t   = now - self._t0
        state = get_state()

        # 1. Respiración suave
        self._update_breath(t)

        # 2. Parpadeo natural
        self._update_blink(now)

        # 3. Mirada aleatoria
        self._update_gaze(now, state)

        # 4. Micro inclinaciones según emoción
        self._update_head_tilt(t, state)

        # 5. Lip-sync
        self._update_mouth(state)

        # 6. Opacidad (clamp estricto — fix bug transparencia)
        self._params.opacity = _clamp(1.0, 0.0, 1.0)

        # 7. Interpolar hacia targets suavemente
        self._smooth_params()

        # 8. Escribir al estado compartido
        self._write_params(state)

    # ── Respiración ───────────────────────────────────────────────────────────

    def _update_breath(self, t: float) -> None:
        """Ciclo sinusoidal suave de respiración."""
        raw = (math.sin(2 * math.pi * t / self.BREATH_PERIOD) + 1) / 2
        self._target.breath = _clamp(raw, 0.0, 1.0)

        # Micro movimiento del cuerpo con la respiración
        body_y = math.sin(2 * math.pi * t / self.BREATH_PERIOD) * 1.5
        self._target.body_y = _clamp(body_y, -10.0, 10.0)

    # ── Parpadeo ──────────────────────────────────────────────────────────────

    def _update_blink(self, now: float) -> None:
        """Parpadeo natural con timing aleatorio."""
        if not self._blinking and now >= self._next_blink:
            self._blinking = True
            self._blink_phase = 0.0

        if self._blinking:
            self._blink_phase += self.FRAME_TIME / self.BLINK_SPEED
            # Fase 0→1: cerrar; 1→2: abrir
            if self._blink_phase < 1.0:
                eye = _clamp(1.0 - self._blink_phase, 0.0, 1.0)
            elif self._blink_phase < 2.0:
                eye = _clamp(self._blink_phase - 1.0, 0.0, 1.0)
            else:
                eye = 1.0
                self._blinking = False
                self._next_blink = now + random.uniform(self.BLINK_MIN, self.BLINK_MAX)

            self._target.eye_l_open = eye
            self._target.eye_r_open = eye
        else:
            self._target.eye_l_open = 1.0
            self._target.eye_r_open = 1.0

    # ── Mirada aleatoria ──────────────────────────────────────────────────────

    def _update_gaze(self, now: float, state: AvatarState) -> None:
        """Mirada aleatoria controlada — más activa cuando piensa."""
        if now >= self._next_gaze:
            # Rango de mirada según estado
            max_x = self.GAZE_MAX_X * (1.5 if state.is_thinking else 1.0)
            max_y = self.GAZE_MAX_Y * (1.2 if state.is_thinking else 1.0)

            self._gaze_target_x = random.uniform(-max_x, max_x)
            self._gaze_target_y = random.uniform(-max_y, max_y)

            # Intervalo más corto cuando piensa
            interval = random.uniform(
                self.GAZE_CHANGE_MIN * (0.5 if state.is_thinking else 1.0),
                self.GAZE_CHANGE_MAX * (0.7 if state.is_thinking else 1.0),
            )
            self._next_gaze = now + interval

        # Interpolar suavemente hacia el target
        self._target.angle_x = _clamp(self._gaze_target_x, -30.0, 30.0)
        self._target.angle_y = _clamp(self._gaze_target_y, -30.0, 30.0)

    # ── Inclinaciones de cabeza ───────────────────────────────────────────────

    def _update_head_tilt(self, t: float, state: AvatarState) -> None:
        """Micro inclinaciones según emoción."""
        if state.hablando:
            # Leve movimiento al hablar
            tilt = math.sin(t * 3.0) * 2.0
        elif state.is_thinking:
            # Inclinación hacia un lado al pensar
            tilt = math.sin(t * 0.8) * 5.0
        elif state.estado == "entusiasmo":
            # Más movimiento cuando está entusiasmada
            tilt = math.sin(t * 2.0) * 4.0
        elif state.is_sleeping:
            # Cabeza ligeramente caída al dormir
            tilt = -3.0
        else:
            # Micro movimiento idle
            tilt = math.sin(t * 0.3) * 1.5

        self._target.angle_z = _clamp(tilt, -30.0, 30.0)

        # Body tilt
        body_x = math.sin(t * 0.5) * 2.0
        self._target.body_x = _clamp(body_x, -10.0, 10.0)

    # ── Lip-sync ──────────────────────────────────────────────────────────────

    def _update_mouth(self, state: AvatarState) -> None:
        """Sincronizar apertura de boca con la amplitud del TTS."""
        amp = _clamp(state.mouth_amplitude, 0.0, 1.0)
        self._target.mouth_open = amp

    # ── Interpolación suave ───────────────────────────────────────────────────

    def _smooth_params(self) -> None:
        """Interpolar parámetros actuales hacia targets (easing)."""
        # Velocidades de interpolación (más alto = más rápido)
        speeds = {
            "eye_l_open": 0.3,
            "eye_r_open": 0.3,
            "angle_x":    0.08,
            "angle_y":    0.08,
            "angle_z":    0.06,
            "body_x":     0.05,
            "body_y":     0.05,
            "breath":     0.04,
            "mouth_open": 0.5,   # lip-sync necesita ser rápido
        }

        for attr, speed in speeds.items():
            current = getattr(self._params, attr)
            target  = getattr(self._target, attr)
            setattr(self._params, attr, _lerp(current, target, speed))

    # ── Escritura al estado compartido ───────────────────────────────────────

    def _write_params(self, state: AvatarState) -> None:
        """
        Escribe los parámetros de movimiento en chibi_state.json.
        PRESERVA los campos existentes (no sobreescribe estado emocional).
        FIX BUG: clamp estricto de opacity para evitar acumulación de transparencia.
        """
        try:
            # Leer estado actual
            data: dict = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            # Escribir solo los parámetros de movimiento
            # Clamp estricto en todos los valores — FIX BUG transparencia
            data["ParamEyeLOpen"]   = _clamp(self._params.eye_l_open, 0.0, 1.0)
            data["ParamEyeROpen"]   = _clamp(self._params.eye_r_open, 0.0, 1.0)
            data["ParamAngleX"]     = _clamp(self._params.angle_x, -30.0, 30.0)
            data["ParamAngleY"]     = _clamp(self._params.angle_y, -30.0, 30.0)
            data["ParamAngleZ"]     = _clamp(self._params.angle_z, -30.0, 30.0)
            data["ParamBodyAngleX"] = _clamp(self._params.body_x, -10.0, 10.0)
            data["ParamBodyAngleY"] = _clamp(self._params.body_y, -10.0, 10.0)
            data["ParamBreath"]     = _clamp(self._params.breath, 0.0, 1.0)
            data["ParamMouthOpenY"] = _clamp(self._params.mouth_open, 0.0, 1.0)
            # FIX: opacity siempre 1.0 — nunca acumular transparencia
            data["opacity"]         = 1.0

            STATE_FILE.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass  # fail-silent


# ── Singleton ──────────────────────────────────────────────────────────────────
_controller: Optional[MotionController] = None


def get_motion_controller() -> MotionController:
    global _controller
    if _controller is None:
        _controller = MotionController()
    return _controller


def start_motion_controller() -> MotionController:
    ctrl = get_motion_controller()
    if not ctrl._running:
        ctrl.start()
    return ctrl
