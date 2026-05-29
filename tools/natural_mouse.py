"""
natural_mouse.py — Puntero SP de Alisha: movimiento orgánico, asíncrono y reactivo.

Optimizaciones v2:
  - Pre-cálculo asíncrono: el movimiento corre en hilo daemon, no bloquea Gemini
  - easeOutQuad: interpolación ligera (una multiplicación) en lugar de smooth step
  - Caché de coordenadas: recuerda posiciones de elementos comunes
  - Feedback inmediato: señal a chibi_state.json antes de que el mouse arranque
  - Override de usuario: si el usuario mueve el mouse, Alisha suelta el control

Principio fail-silent: toda excepción se captura; nunca se propaga.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time
from pathlib import Path
from typing import Optional

import pyautogui

from config.settings import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# ── Detección de resolución y DPI real ───────────────────────────────────────

def _obtener_resolucion_real() -> tuple[int, int]:
    """
    Retorna la resolución real de la pantalla considerando el escalado DPI de Windows.
    En pantallas con 125% o 150% de escalado, las coordenadas físicas difieren
    de las lógicas. pyautogui ya maneja esto internamente, pero necesitamos
    la resolución para normalizar el caché de coordenadas.
    """
    try:
        import ctypes
        # Obtener resolución física real (no escalada)
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return (w, h)
    except Exception:
        return (1920, 1080)  # fallback seguro

_SW, _SH = _obtener_resolucion_real()

# ── Caché de coordenadas normalizadas (0.0-1.0) ───────────────────────────────
# Usar coordenadas normalizadas en lugar de píxeles fijos.
# Se convierten a píxeles reales en tiempo de ejecución según la resolución actual.
_COORD_CACHE_NORM: dict[str, tuple[float, float]] = {
    "barra_tareas":    (0.5,   0.98),   # centro inferior
    "boton_inicio":    (0.016, 0.98),   # esquina inferior izquierda
    "escritorio":      (0.5,   0.5),    # centro de pantalla
    "esquina_cerrar":  (0.99,  0.01),   # esquina superior derecha
}

def _norm_a_px(nx: float, ny: float) -> tuple[int, int]:
    """Convierte coordenadas normalizadas (0-1) a píxeles reales."""
    sw, sh = _obtener_resolucion_real()
    return (int(nx * sw), int(ny * sh))

# Mantener compatibilidad con código que usa píxeles directos
_COORD_CACHE: dict[str, tuple[int, int]] = {
    k: _norm_a_px(nx, ny) for k, (nx, ny) in _COORD_CACHE_NORM.items()
}


class NaturalMouse:
    """
    Puntero SP de Alisha — movimiento orgánico y asíncrono.

    El movimiento corre en un hilo daemon separado para no bloquear
    el procesamiento de Gemini ni el render del Live2D.
    """

    def __init__(self):
        self._hilo_movimiento: Optional[threading.Thread] = None
        self._cancelar = threading.Event()   # señal para cancelar movimiento en curso
        self._en_movimiento = False

    # ── API pública ────────────────────────────────────────────────────────────

    def mover_a(self, x: int, y: int, bloquear: bool = False) -> None:
        """
        Mueve el cursor a (x, y) de forma orgánica.

        bloquear=False (default): asíncrono — retorna inmediatamente,
                                  el movimiento ocurre en hilo daemon.
        bloquear=True: espera a que el movimiento termine.
        """
        # Señal inmediata al Live2D — Alisha mira hacia donde va a mover el mouse
        self._feedback_inmediato(x, y)

        # Cancelar movimiento anterior si hay uno en curso
        self._cancelar.set()
        if self._hilo_movimiento and self._hilo_movimiento.is_alive():
            self._hilo_movimiento.join(timeout=0.1)
        self._cancelar.clear()

        self._hilo_movimiento = threading.Thread(
            target=self._ejecutar_movimiento,
            args=(x, y),
            daemon=True,
            name="NaturalMouse-Move",
        )
        self._hilo_movimiento.start()

        if bloquear:
            self._hilo_movimiento.join()

    def click_natural(self, x: int, y: int) -> None:
        """Mueve el cursor a (x, y) y hace clic. Bloquea hasta completar."""
        self.mover_a(x, y, bloquear=True)
        try:
            pyautogui.click()
            # Actualizar caché con la posición clickeada
            _COORD_CACHE[f"ultimo_click"] = (x, y)
        except pyautogui.FailSafeException:
            print("[NaturalMouse] FailSafe — click cancelado")
        except Exception as e:
            print(f"[NaturalMouse] Error en click: {e}")

    def cancelar(self) -> None:
        """Cancela el movimiento en curso inmediatamente."""
        self._cancelar.set()

    def esta_en_movimiento(self) -> bool:
        return self._en_movimiento

    def recordar_posicion(self, nombre: str, x: int, y: int) -> None:
        """Guarda una posición en el caché para uso futuro."""
        _COORD_CACHE[nombre] = (x, y)

    def obtener_posicion_recordada(self, nombre: str) -> Optional[tuple[int, int]]:
        """Retorna una posición recordada o None si no existe."""
        return _COORD_CACHE.get(nombre)

    def señalar(self, x: int, y: int, vueltas: float = 1.5) -> None:
        """
        Mueve el mouse en círculos alrededor de (x, y) para señalar algo.
        Útil cuando Alisha explica algo en pantalla.
        Asíncrono — no bloquea.
        """
        def _circulo():
            try:
                radio = 40
                pasos = int(vueltas * 24)
                for i in range(pasos):
                    if self._cancelar.is_set():
                        break
                    angulo = (i / 24) * 2 * math.pi
                    cx = int(x + radio * math.cos(angulo))
                    cy = int(y + radio * math.sin(angulo))
                    pyautogui.moveTo(cx, cy, duration=0)
                    time.sleep(0.04)
                # Volver al centro
                pyautogui.moveTo(x, y, duration=0.2)
            except Exception as e:
                print(f"[NaturalMouse] Error en señalar: {e}")

        self._cancelar.set()
        self._cancelar.clear()
        threading.Thread(target=_circulo, daemon=True, name="NaturalMouse-Señalar").start()

    # ── Movimiento interno ─────────────────────────────────────────────────────

    def _ejecutar_movimiento(self, x_dest: int, y_dest: int) -> None:
        """Ejecuta el movimiento en hilo daemon con easeOutQuad."""
        self._en_movimiento = True
        try:
            pos = pyautogui.position()
            x0, y0 = float(pos.x), float(pos.y)
            x1, y1 = float(x_dest), float(y_dest)

            distancia = math.hypot(x1 - x0, y1 - y0)

            # Movimiento corto — lineal directo, sin overhead
            if distancia < 60.0:
                if not self._cancelar.is_set():
                    pyautogui.moveTo(x_dest, y_dest, duration=0.12)
                return

            # Movimiento largo — Bézier con easeOutQuad
            duracion = self._calcular_duracion(distancia)

            # Punto de control (curva suave)
            dx, dy = x1 - x0, y1 - y0
            longitud = math.hypot(dx, dy) or 1.0
            perp_x, perp_y = -dy / longitud, dx / longitud
            desp = random.uniform(15.0, 50.0) * random.choice([-1.0, 1.0])
            cx = (x0 + x1) / 2.0 + desp * perp_x
            cy = (y0 + y1) / 2.0 + desp * perp_y

            # Pre-calcular puntos (solo 20 — suficiente para fluidez)
            STEPS = 20
            puntos = self._bezier_rapido((x0, y0), (cx, cy), (x1, y1), STEPS)

            t_inicio = time.perf_counter()

            for i, (px, py) in enumerate(puntos):
                if self._cancelar.is_set():
                    return

                # Verificar override del usuario (si movió el mouse > 8px)
                pos_actual = pyautogui.position()
                if i > 2:  # ignorar los primeros pasos
                    dx_user = abs(pos_actual.x - int(round(px)))
                    dy_user = abs(pos_actual.y - int(round(py)))
                    if dx_user > 8 or dy_user > 8:
                        print("[NaturalMouse] Override del usuario — soltando control")
                        return

                # easeOutQuad: t_ease = 1 - (1-t)²  — más rápido al inicio, suave al final
                t_norm = i / max(STEPS - 1, 1)
                t_ease = 1.0 - (1.0 - t_norm) ** 2

                # Tiempo objetivo para este punto
                t_objetivo = t_inicio + t_ease * duracion
                ahora = time.perf_counter()
                espera = t_objetivo - ahora
                if espera > 0.001:
                    time.sleep(espera)

                pyautogui.moveTo(int(round(px)), int(round(py)), duration=0)

        except pyautogui.FailSafeException:
            print("[NaturalMouse] FailSafe — movimiento detenido")
        except Exception as e:
            print(f"[NaturalMouse] Error en movimiento: {e}")
        finally:
            self._en_movimiento = False

    def _bezier_rapido(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        steps: int,
    ) -> list[tuple[float, float]]:
        """Bézier cuadrática optimizada — sin bucle de ease, solo geometría."""
        puntos = []
        for i in range(steps):
            t = i / (steps - 1)
            mt = 1.0 - t
            x = mt * mt * p0[0] + 2.0 * mt * t * p1[0] + t * t * p2[0]
            y = mt * mt * p0[1] + 2.0 * mt * t * p1[1] + t * t * p2[1]
            puntos.append((x, y))
        puntos[-1] = (float(p2[0]), float(p2[1]))
        return puntos

    def _calcular_duracion(self, distancia: float) -> float:
        """Duración en segundos — más rápido que antes para sensación reactiva."""
        if distancia < 60.0:
            return 0.12
        # Máximo 0.6s (antes era 1.2s) — el doble de rápido
        return min(0.6, max(0.12, distancia / 2000.0))

    def _feedback_inmediato(self, x_dest: int, y_dest: int) -> None:
        """
        Señal inmediata al Live2D antes de que el mouse arranque.
        Los ojos de Alisha miran hacia donde va a mover el cursor.
        Usa resolución real detectada dinámicamente.
        """
        try:
            sw, sh = _obtener_resolucion_real()

            # Normalizar destino a [-1, 1]
            gaze_x = (x_dest / sw) * 2.0 - 1.0
            gaze_y = (y_dest / sh) * 2.0 - 1.0

            data = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass

            data["gaze_x"]        = round(gaze_x * 0.8, 3)   # escalar a rango Live2D
            data["gaze_y"]        = round(gaze_y * 0.6, 3)
            data["gaze_override"] = True
            data["estado"]        = "curiosidad"   # expresión de acción

            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            # Quitar override después de 1.5s
            def _quitar():
                time.sleep(1.5)
                try:
                    d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    d["gaze_override"] = False
                    STATE_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
            threading.Thread(target=_quitar, daemon=True).start()

        except Exception:
            pass

    # ── Funciones de compatibilidad (para tests existentes) ───────────────────

    def _bezier_curve(self, p0, p1, p2, steps):
        return self._bezier_rapido(p0, p1, p2, steps)

    def _ease_in_out(self, t: float) -> float:
        return 3.0 * t * t - 2.0 * t * t * t


