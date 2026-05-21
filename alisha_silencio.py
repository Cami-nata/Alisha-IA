"""
alisha_silencio.py — Semáforo global de silencio para Alisha.

Controla que Alisha NO hable por iniciativa propia más de una vez
cada COOLDOWN_SEGUNDOS. Solo habla si Cami le pregunta algo directo.

Todos los sistemas proactivos consultan puede_hablar_proactivo()
antes de emitir cualquier comentario espontáneo.
"""
import time
import threading

# ── Configuración ──────────────────────────────────────────────────────────────
COOLDOWN_SEGUNDOS = 600   # 10 minutos entre comentarios espontáneos (era 2 min)
_ultimo_habla: dict = {}  # {sistema: timestamp}
_lock = threading.Lock()

# Ventana activa anterior — para detectar cambios significativos
_ultima_ventana = ""
_ventana_lock   = threading.Lock()


def puede_hablar_proactivo(sistema: str = "general") -> bool:
    """
    Retorna True si:
    1. Pasaron >= COOLDOWN_SEGUNDOS desde el último comentario proactivo
    2. Hay una captura de pantalla reciente (< 30s) — si no, silencio total
    """
    with _lock:
        ultimo = _ultimo_habla.get(sistema, 0.0)
        if (time.time() - ultimo) < COOLDOWN_SEGUNDOS:
            return False

    # Verificar que hay visión reciente antes de comentar
    try:
        from vision_engine import get_vision_engine
        ve = get_vision_engine()
        snap = ve.get_last_snapshot()
        if snap is None:
            return False  # sin captura → silencio
        edad = time.time() - snap.timestamp
        if edad > 30.0:
            return False  # captura vieja → silencio
    except Exception:
        pass  # si VisionEngine no está disponible, permitir igual

    return True


def registrar_habla_proactivo(sistema: str = "general") -> None:
    """Registra que Alisha acaba de hablar por iniciativa propia."""
    with _lock:
        _ultimo_habla[sistema] = time.time()


# Aliases para compatibilidad
def puede_hablar_ahora() -> bool:
    return puede_hablar_proactivo("general")


def registrar_habla_proactiva() -> None:
    registrar_habla_proactivo("general")


def tiempo_hasta_proximo(sistema: str = "general") -> float:
    """Retorna los segundos que faltan para poder hablar de nuevo."""
    with _lock:
        ultimo = _ultimo_habla.get(sistema, 0.0)
        restante = COOLDOWN_SEGUNDOS - (time.time() - ultimo)
        return max(0.0, restante)


def ventana_cambio_significativo(nueva_ventana: str) -> bool:
    """
    Retorna True si la ventana activa cambió significativamente.
    Cambios menores (mismo dominio, mismo proceso) no cuentan.
    """
    global _ultima_ventana
    with _ventana_lock:
        nueva    = nueva_ventana.lower().strip()
        anterior = _ultima_ventana.lower().strip()

        if not anterior:
            _ultima_ventana = nueva_ventana
            return False

        if nueva == anterior:
            return False

        import re
        def _app_principal(titulo: str) -> str:
            titulo = re.sub(r'\s*[-–]\s*(google chrome|microsoft edge|opera|firefox|brave).*$',
                            '', titulo, flags=re.IGNORECASE)
            titulo = re.sub(r'\s*\d+\s*$', '', titulo)
            return titulo.strip()[:40]

        if _app_principal(nueva) == _app_principal(anterior):
            return False

        _ultima_ventana = nueva_ventana
        return True


def resetear_ventana() -> None:
    global _ultima_ventana
    with _ventana_lock:
        _ultima_ventana = ""
