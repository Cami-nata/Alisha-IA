"""
alisha_voz_control.py — Semáforo global de voz de Alisha.

Garantiza que solo UN sistema hable a la vez.
Todos los sistemas de comentarios espontáneos deben usar este módulo.
"""
import threading
import time

_lock = threading.Lock()
_hablando = False
_ultimo_habla = 0.0
MIN_SILENCIO = 8.0  # segundos mínimos entre comentarios espontáneos


def puede_hablar() -> bool:
    """True si ningún sistema está hablando y pasó suficiente tiempo."""
    global _hablando, _ultimo_habla
    if _hablando:
        return False
    if time.time() - _ultimo_habla < MIN_SILENCIO:
        return False
    # Verificar también chibi_state
    try:
        from assistant_state import cargar_estado
        estado = cargar_estado()
        if estado.get("hablando", False) or estado.get("modo") == "THINKING":
            return False
    except Exception:
        pass
    return True


def hablar(texto: str, callback_tts) -> bool:
    """
    Intenta hablar. Retorna True si pudo, False si estaba ocupada.
    callback_tts: función que recibe el texto y lo habla.
    """
    global _hablando, _ultimo_habla
    with _lock:
        if not puede_hablar():
            return False
        _hablando = True
        _ultimo_habla = time.time()

    try:
        callback_tts(texto)
    finally:
        _hablando = False

    return True
