"""
alisha_bridge.py — Puente de memoria compartida entre el Cerebro y el Cuerpo.

Variables globales en memoria del proceso — latencia ~0ms.
El TTS escribe aquí, cabina_virtual.py lee aquí directamente.

Sin archivos, sin sockets, sin serialización.
"""

# ── Lip-sync ──────────────────────────────────────────────────────────────────
MOUTH_AMPLITUDE: float = 0.0   # 0.0 = boca cerrada, 1.0 = boca abierta
IS_SPEAKING:     bool  = False  # True mientras el TTS está reproduciendo

# ── Estado emocional ──────────────────────────────────────────────────────────
EMOTION:         str   = "neutral"
SARCASM_SCORE:   float = 0.0

# ── Animaciones Live2D ────────────────────────────────────────────────────────
ANIMATION_STATE: str   = "idle"    # Estado de animación actual
GAZE_X:          float = 0.0       # Dirección horizontal de la mirada (-1.0 a 1.0)
GAZE_Y:          float = 0.0       # Dirección vertical de la mirada (-1.0 a 1.0)

# ── Señal de pensamiento ──────────────────────────────────────────────────────
IS_THINKING:     bool  = False  # True mientras el cerebro procesa

# ── Word timestamps — sincronización texto/audio ──────────────────────────────
# Lista de dicts: [{"word": str, "offset_s": float}, ...]
# edge-tts los genera via WordBoundary events.
# web_app.py los lee para emitir cada palabra en el momento exacto.
WORD_TIMESTAMPS: list = []      # timestamps de la síntesis actual
AUDIO_START_TS:  float = 0.0   # time.time() cuando empezó a reproducirse el audio

# ── Funciones de animación ────────────────────────────────────────────────────

def set_animation_state(animation: str) -> None:
    """Establece el estado de animación actual."""
    global ANIMATION_STATE
    ANIMATION_STATE = animation

def set_gaze_direction(x: float, y: float) -> None:
    """Establece la dirección de la mirada."""
    global GAZE_X, GAZE_Y
    GAZE_X = max(-1.0, min(1.0, x))
    GAZE_Y = max(-1.0, min(1.0, y))

def trigger_animation(action: str) -> None:
    """
    Traduce acciones de texto a parámetros Live2D y los aplica.
    
    Args:
        action: Acción en texto (ej: "gira la cabeza", "sonríe", "mira hacia arriba")
    """
    import json
    from pathlib import Path
    
    # Mapeo de acciones a parámetros Live2D
    action_lower = action.lower().strip()
    
    # Leer estado actual
    from config import DATA_DIR
    state_file = DATA_DIR / "chibi_state.json"
    current_state = {}
    if state_file.exists():
        try:
            current_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    
    # Aplicar animación según la acción
    if "gira la cabeza" in action_lower or "voltea" in action_lower:
        # Girar la cabeza hacia un lado
        direction = 0.6 if "derecha" in action_lower else -0.6 if "izquierda" in action_lower else 0.4
        current_state.update({
            "gaze_x": direction,
            "gaze_y": 0.0,
            "estado": "curiosidad",
            "animation_state": "head_turn"
        })
        set_gaze_direction(direction, 0.0)
        set_animation_state("head_turn")
        
    elif "sonríe" in action_lower or "sonrisa" in action_lower:
        # Sonreír - aumentar amplitud de boca temporalmente
        current_state.update({
            "mouth_amplitude": 0.3,
            "estado": "alegría",
            "animation_state": "smile"
        })
        set_animation_state("smile")
        
    elif "mira hacia arriba" in action_lower or "levanta la vista" in action_lower:
        # Mirar hacia arriba
        current_state.update({
            "gaze_x": 0.0,
            "gaze_y": -0.5,
            "estado": "curiosidad",
            "animation_state": "look_up"
        })
        set_gaze_direction(0.0, -0.5)
        set_animation_state("look_up")
        
    elif "mira hacia abajo" in action_lower or "baja la vista" in action_lower:
        # Mirar hacia abajo
        current_state.update({
            "gaze_x": 0.0,
            "gaze_y": 0.5,
            "estado": "pensativa",
            "animation_state": "look_down"
        })
        set_gaze_direction(0.0, 0.5)
        set_animation_state("look_down")
        
    elif "asiente" in action_lower or "afirma" in action_lower:
        # Asentir con la cabeza
        current_state.update({
            "gaze_y": -0.2,
            "estado": "aprobación",
            "animation_state": "nod"
        })
        set_gaze_direction(0.0, -0.2)
        set_animation_state("nod")
        
    elif "niega" in action_lower or "sacude la cabeza" in action_lower:
        # Negar con la cabeza
        current_state.update({
            "gaze_x": 0.3,
            "estado": "desaprobación",
            "animation_state": "shake_head"
        })
        set_gaze_direction(0.3, 0.0)
        set_animation_state("shake_head")
        
    elif "parpadea" in action_lower or "guiña" in action_lower:
        # Parpadear o guiñar
        current_state.update({
            "estado": "coqueta",
            "animation_state": "blink"
        })
        set_animation_state("blink")
        
    elif "suspira" in action_lower:
        # Suspirar
        current_state.update({
            "mouth_amplitude": 0.1,
            "estado": "cansancio",
            "animation_state": "sigh"
        })
        set_animation_state("sigh")
        
    else:
        # Acción genérica - estado neutral con ligero movimiento
        current_state.update({
            "gaze_x": 0.0,
            "gaze_y": 0.0,
            "estado": "neutral",
            "animation_state": "generic"
        })
        set_gaze_direction(0.0, 0.0)
        set_animation_state("generic")
    
    # Escribir estado actualizado
    try:
        state_file.write_text(
            json.dumps(current_state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[alisha_bridge] Animación aplicada: {action} -> {current_state.get('animation_state', 'unknown')}")
    except Exception as e:
        print(f"[alisha_bridge] Error aplicando animación: {e}")

def reset_animation() -> None:
    """Resetea la animación a estado neutral."""
    import json
    from config import DATA_DIR
    
    state_file = DATA_DIR / "chibi_state.json"
    current_state = {}
    if state_file.exists():
        try:
            current_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    
    current_state.update({
        "gaze_x": 0.0,
        "gaze_y": 0.0,
        "estado": "neutral",
        "animation_state": "idle"
    })
    
    set_gaze_direction(0.0, 0.0)
    set_animation_state("idle")
    
    try:
        state_file.write_text(
            json.dumps(current_state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[alisha_bridge] Error reseteando animación: {e}")


# ── Loop de animaciones de espera (idle) ──────────────────────────────────────

import threading as _threading
import time as _time
import random as _random

_idle_loop_running = False
_idle_loop_thread = None


def start_idle_loop() -> None:
    """
    Inicia el loop de animaciones de espera en un hilo daemon.
    Genera parpadeos y micro-movimientos de respiración para que Alisha
    no parezca estática cuando no está hablando.
    """
    global _idle_loop_running, _idle_loop_thread
    if _idle_loop_running:
        return
    _idle_loop_running = True
    _idle_loop_thread = _threading.Thread(target=_idle_animation_loop, daemon=True, name="AlishaIdleLoop")
    _idle_loop_thread.start()
    print("[alisha_bridge] ✓ Idle animation loop iniciado")


def stop_idle_loop() -> None:
    """Detiene el loop de animaciones de espera."""
    global _idle_loop_running
    _idle_loop_running = False


def _idle_animation_loop() -> None:
    """
    Loop interno que genera animaciones de espera naturales:
    - Parpadeo cada 3-6 segundos
    - Micro-movimientos de mirada cada 8-15 segundos
    - Respiración sutil (movimiento vertical leve) continua
    Solo actúa cuando Alisha NO está hablando ni pensando.
    """
    import json
    from config import DATA_DIR

    state_file = DATA_DIR / "chibi_state.json"
    last_blink = _time.time()
    last_gaze_shift = _time.time()

    while _idle_loop_running:
        try:
            # Solo animar en idle (no interrumpir habla ni pensamiento)
            if IS_SPEAKING or IS_THINKING:
                _time.sleep(0.5)
                continue

            now = _time.time()

            # ── Parpadeo automático ──────────────────────────────────────────
            blink_interval = _random.uniform(3.0, 6.0)
            if now - last_blink >= blink_interval:
                _write_idle_state(state_file, {"animation_state": "blink"})
                _time.sleep(0.15)  # duración del parpadeo
                _write_idle_state(state_file, {"animation_state": "idle"})
                last_blink = now

            # ── Micro-movimiento de mirada ───────────────────────────────────
            gaze_interval = _random.uniform(8.0, 15.0)
            if now - last_gaze_shift >= gaze_interval:
                # Pequeño desvío natural de la mirada
                gaze_x = _random.uniform(-0.15, 0.15)
                gaze_y = _random.uniform(-0.1, 0.1)
                set_gaze_direction(gaze_x, gaze_y)
                _write_idle_state(state_file, {
                    "gaze_x": gaze_x,
                    "gaze_y": gaze_y,
                    "animation_state": "idle_look"
                })
                _time.sleep(_random.uniform(1.5, 3.0))
                # Volver al centro suavemente
                set_gaze_direction(0.0, 0.0)
                _write_idle_state(state_file, {
                    "gaze_x": 0.0,
                    "gaze_y": 0.0,
                    "animation_state": "idle"
                })
                last_gaze_shift = now

        except Exception:
            pass

        _time.sleep(0.5)


def _write_idle_state(state_file, updates: dict) -> None:
    """Escribe actualizaciones de estado idle en chibi_state.json."""
    import json
    try:
        current = {}
        if state_file.exists():
            try:
                current = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        current.update(updates)
        state_file.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass