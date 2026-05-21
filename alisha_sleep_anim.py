"""
alisha_sleep_anim.py — Ciclo de Sueño y Despertar para cabina_virtual.py.

Controla el estado de sueño/despertar del modelo Live2D directamente
via chibi_state.json. cabina_virtual.py lee ese archivo cada 50ms.

Estados:
  dormida   → ojos cerrados, respiración lenta, cabeza inclinada
  despertando → secuencia de animación (3 fases)
  despierta → estado normal

Gatillos de despertar:
  - Movimiento del mouse (detectado via pynput pasivo)
  - Mensaje en el chat web
  - Llamado directo a despertar()
"""
import json
import math
import threading
import time
from pathlib import Path

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"
SLEEP_FILE = DATA_DIR / "alisha_sleep_state.json"

_estado = "dormida"   # "dormida" | "despertando" | "despierta"
_lock   = threading.Lock()
_callback_despierta = None   # función a llamar cuando termina de despertar


def _leer_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _escribir_state(updates: dict) -> None:
    try:
        data = _leer_state()
        data.update(updates)
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def esta_dormida() -> bool:
    return _estado == "dormida"


def esta_despierta() -> bool:
    return _estado == "despierta"


def dormir(callback_despierta=None) -> None:
    """Pone a Alisha en modo dormida."""
    global _estado, _callback_despierta
    with _lock:
        _estado = "dormida"
        _callback_despierta = callback_despierta

    print("[SleepAnim] Alisha se durmio")
    # Escribir estado de sueño en chibi_state para que cabina_virtual lo aplique
    _escribir_state({
        "sleep_mode": True,
        "sleep_phase": "dormida",
        # Parámetros directos para cabina_virtual
        "sleep_eye_open":   0.0,
        "sleep_breath":     0.15,
        "sleep_angle_y":    8.0,   # cabeza inclinada hacia adelante
        "sleep_angle_z":    3.0,   # leve inclinación lateral
        "sleep_mouth_form": -0.2,
    })

    # Guardar en archivo de estado de sueño
    try:
        SLEEP_FILE.write_text(json.dumps({"dormida": True, "ts": time.time()}), encoding="utf-8")
    except Exception:
        pass


def despertar(motivo: str = "usuario") -> None:
    """Inicia la secuencia de despertar."""
    global _estado
    with _lock:
        if _estado == "despierta":
            return
        _estado = "despertando"

    print(f"[SleepAnim] Despertando ({motivo})...")
    threading.Thread(target=_secuencia_despertar, daemon=True).start()


def _secuencia_despertar() -> None:
    """
    Secuencia de 3 fases:
    Fase 1 (0-0.5s):  Ojos se abren rápido, sorpresa
    Fase 2 (0.5-1.5s): Bostezo suave, estiramiento
    Fase 3 (1.5-3s):  Normalización, saludo
    """
    global _estado

    # Fase 1: Sorpresa — ojos se abren rápido
    _escribir_state({
        "sleep_mode": True,
        "sleep_phase": "despertando_f1",
        "sleep_eye_open":   1.0,
        "sleep_breath":     0.9,
        "sleep_angle_y":    0.0,
        "sleep_angle_z":    0.0,
        "sleep_mouth_form": 0.0,
    })
    # Expresión de sorpresa
    _escribir_state({"estado": "curiosidad"})
    time.sleep(0.5)

    # Fase 2: Bostezo
    _escribir_state({
        "sleep_phase": "despertando_f2",
        "sleep_mouth_open": 0.8,   # boca abierta (bostezo)
        "sleep_breath":     1.0,
    })
    time.sleep(0.8)

    # Fase 3: Cerrar boca, normalizar
    _escribir_state({
        "sleep_phase": "despertando_f3",
        "sleep_mouth_open": 0.0,
        "sleep_breath":     0.6,
    })
    time.sleep(0.7)

    # Despertar completo — limpiar overrides de sueño
    _escribir_state({
        "sleep_mode":  False,
        "sleep_phase": "despierta",
    })

    with _lock:
        _estado = "despierta"

    print("[SleepAnim] Alisha despierta")

    # Guardar estado
    try:
        SLEEP_FILE.write_text(json.dumps({"dormida": False, "ts": time.time()}), encoding="utf-8")
    except Exception:
        pass

    # Llamar callback
    if _callback_despierta:
        try:
            _callback_despierta()
        except Exception:
            pass

    # Saludo de buenos días
    _saludo_despertar()


def _saludo_despertar() -> None:
    """
    Saludo al despertar — DESACTIVADO aquí para evitar doble voz.
    El saludo real lo genera alisha_sleep.py (SistemaSueno._saludar).
    """
    # Solo emitir al chat, sin hablar por voz (evita doble voz)
    try:
        from datetime import datetime
        hora = datetime.now().hour
        if 5 <= hora < 12:
            saludo = "Buen día, Cami. Ya estoy despierta."
        elif 12 <= hora < 19:
            saludo = "Buenas tardes. ¿En qué andamos?"
        else:
            saludo = "Buenas noches. Acá estoy."
        print(f"[SleepAnim] {saludo}")
        # NO llamar speak() aquí — alisha_sleep.py ya lo hace
    except Exception:
        pass


# ── Detector de actividad del mouse ──────────────────────────────────────────

def iniciar_detector_mouse() -> None:
    """Detecta el primer movimiento del mouse para despertar a Alisha."""
    def _detectar():
        try:
            from pynput import mouse as _mouse
            _ultimo_pos = [None]
            _despertado = [False]

            def _on_move(x, y):
                if _despertado[0]:
                    return
                if _ultimo_pos[0] is None:
                    _ultimo_pos[0] = (x, y)
                    return
                dx = abs(x - _ultimo_pos[0][0])
                dy = abs(y - _ultimo_pos[0][1])
                if dx > 5 or dy > 5:
                    if esta_dormida():
                        _despertado[0] = True
                        despertar("mouse")

            listener = _mouse.Listener(on_move=_on_move)
            listener.daemon = True
            listener.start()
            # Mantener el listener vivo
            while True:
                time.sleep(1.0)
                # Resetear flag para detectar próximo ciclo de sueño
                if esta_despierta():
                    _despertado[0] = False
        except Exception as e:
            print(f"[SleepAnim] Detector mouse: {e}")

    threading.Thread(target=_detectar, daemon=True, name="SleepMouseDetector").start()


def iniciar(callback_despierta=None, arrancar_dormida: bool = True) -> None:
    """
    Inicializa el sistema de sueño/despertar.
    
    arrancar_dormida: si True, Alisha arranca dormida y espera actividad.
    """
    iniciar_detector_mouse()

    if arrancar_dormida:
        dormir(callback_despierta=callback_despierta)
    else:
        global _estado
        _estado = "despierta"
        _escribir_state({"sleep_mode": False})
        if callback_despierta:
            callback_despierta()
