"""
mouse_coordinator.py — Detección de movimiento del usuario.

Monitorea la posición del mouse cada 100ms y publica el evento
`user_mouse_active` en el EventBus cuando detecta movimiento > 5px.

Principio fail-silent: toda excepción se captura y registra sin propagarse.

Requisitos: 5.1, 5.2, 5.3, 5.5, 5.6
"""
from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path
from typing import Optional

# Intentar importar pynput; si no está disponible, usar pyautogui como fallback
try:
    from pynput import mouse as _pynput_mouse  # type: ignore
    _PYNPUT_AVAILABLE = True
except Exception:
    _PYNPUT_AVAILABLE = False

import pyautogui  # siempre disponible como fallback

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# Umbral de detección en píxeles (distancia euclidiana)
_UMBRAL_PX: float = 5.0

# Ventana de actividad del usuario en segundos
_VENTANA_ACTIVIDAD_S: float = 3.0

# Intervalo de polling en segundos
_POLL_INTERVAL_S: float = 0.1


class MouseCoordinator:
    """
    Detecta movimiento del mouse del usuario y publica eventos en el EventBus.

    Parámetros
    ----------
    event_bus : objeto con método publish(event_type, data), opcional.
        Si es None, los eventos no se publican (modo standalone).
    """

    def __init__(self, event_bus=None) -> None:
        self._event_bus = event_bus
        self._umbral: float = _UMBRAL_PX
        self._usando_pynput: bool = _PYNPUT_AVAILABLE

        # Estado interno
        self._ultima_posicion: Optional[tuple[float, float]] = None
        self._ultimo_movimiento_ts: float = 0.0

        # Control del hilo
        self._running: bool = False
        self._hilo: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia el hilo daemon de polling."""
        if self._running:
            return
        self._running = True
        self._hilo = threading.Thread(
            target=self._poll_loop,
            name="MouseCoordinator-poll",
            daemon=True,
        )
        self._hilo.start()

    def stop(self) -> None:
        """Detiene el hilo de polling."""
        self._running = False
        # No hacemos join para no bloquear; es daemon, terminará solo.

    def is_user_active(self) -> bool:
        """
        Retorna True si el usuario movió el mouse en los últimos 3 segundos.
        """
        if self._ultimo_movimiento_ts == 0.0:
            return False
        return (time.time() - self._ultimo_movimiento_ts) < _VENTANA_ACTIVIDAD_S

    # ------------------------------------------------------------------
    # Bucle interno
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Corre en hilo daemon; hace polling cada 100ms."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"[MouseCoordinator] Error en poll_loop (ignorado): {e}")
            time.sleep(_POLL_INTERVAL_S)

    def _tick(self) -> None:
        """Una iteración del bucle: obtiene posición y evalúa movimiento."""
        pos = self._obtener_posicion()
        if pos is None:
            return

        x, y = pos

        if self._ultima_posicion is None:
            # Primera lectura: inicializar sin publicar evento
            self._ultima_posicion = (x, y)
            return

        px, py = self._ultima_posicion
        distancia = math.sqrt((x - px) ** 2 + (y - py) ** 2)

        if distancia > self._umbral:
            ahora = time.time()
            self._ultimo_movimiento_ts = ahora
            self._ultima_posicion = (x, y)

            # Publicar evento en EventBus (si está disponible)
            self._publicar_evento(x, y, ahora)

            # Actualizar chibi_state.json
            self._actualizar_estado(ahora)
        else:
            self._ultima_posicion = (x, y)

    def _obtener_posicion(self) -> Optional[tuple[float, float]]:
        """
        Obtiene la posición actual del mouse.

        Usa pynput si está disponible; de lo contrario, pyautogui.position().
        """
        try:
            if self._usando_pynput:
                controller = _pynput_mouse.Controller()
                pos = controller.position
                if pos is None:
                    raise ValueError("pynput retornó None")
                return (float(pos[0]), float(pos[1]))
            else:
                pos = pyautogui.position()
                return (float(pos.x), float(pos.y))
        except Exception as e:
            print(f"[MouseCoordinator] Error obteniendo posición (ignorado): {e}")
            return None

    def _publicar_evento(self, x: float, y: float, ts: float) -> None:
        """Publica el evento user_mouse_active en el EventBus si está disponible."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(
                "user_mouse_active",
                {"timestamp": ts, "x": x, "y": y},
            )
        except Exception as e:
            print(f"[MouseCoordinator] Error publicando evento (ignorado): {e}")

    def _actualizar_estado(self, ts: float) -> None:
        """Actualiza chibi_state.json con el timestamp del último movimiento."""
        try:
            estado: dict = {}
            if STATE_FILE.exists():
                try:
                    estado = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    estado = {}
            estado["ultimo_movimiento_usuario"] = ts
            STATE_FILE.write_text(
                json.dumps(estado, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[MouseCoordinator] Error actualizando chibi_state.json (ignorado): {e}")
