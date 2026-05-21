"""
alisha_health.py — Monitor de Salud del Sistema para la ASUS F15.

Verifica CPU y RAM de los procesos de Alisha cada 30 segundos.
Si supera el 15% de CPU → activa Modo Ahorro automáticamente.
Modo Ahorro: reduce intervalos de scan, desactiva visión activa, notifica a Cami.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

# ── Umbrales ───────────────────────────────────────────────────────────────────
CPU_UMBRAL_AHORRO  = 40.0   # % CPU → modo ahorro (subido de 15% — era muy sensible)
RAM_UMBRAL_AHORRO  = 700    # MB RAM → modo ahorro
CPU_UMBRAL_CRITICO = 60.0   # % CPU → alerta crítica
CHECK_INTERVAL     = 60     # segundos entre checks (subido de 30s)

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

_modo_ahorro_activo = False
_lock = threading.Lock()


def _get_alisha_pids() -> list[int]:
    """Retorna los PIDs de todos los procesos Python de Alisha."""
    if not _PSUTIL_OK:
        return []
    pids = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if any(s in cmdline for s in ["Alisha_IA", "cabina_virtual", "web_app", "desktop_widget"]):
                        pids.append(proc.info["pid"])
            except Exception:
                pass
    except Exception:
        pass
    return pids


def get_uso_recursos() -> dict:
    """Retorna el uso de CPU y RAM de los procesos de Alisha."""
    if not _PSUTIL_OK:
        return {"cpu": 0.0, "ram_mb": 0, "pids": [], "ok": False}

    pids = _get_alisha_pids()
    cpu_total = 0.0
    ram_total = 0

    for pid in pids:
        try:
            proc = psutil.Process(pid)
            cpu_total += proc.cpu_percent(interval=0.1)
            ram_total += proc.memory_info().rss // (1024 * 1024)  # MB
        except Exception:
            pass

    return {
        "cpu":    round(cpu_total, 1),
        "ram_mb": ram_total,
        "pids":   pids,
        "ok":     True,
        "modo_ahorro": _modo_ahorro_activo,
    }


def activar_modo_ahorro(razon: str = "CPU alto") -> None:
    """Activa el Modo Ahorro — reduce actividad de Alisha."""
    global _modo_ahorro_activo
    with _lock:
        if _modo_ahorro_activo:
            return
        _modo_ahorro_activo = True

    print(f"[Health] ⚡ MODO AHORRO activado — {razon}")

    # 1. Reducir intervalo de VisionEngine
    try:
        from vision_engine import get_vision_engine
        ve = get_vision_engine()
        ve.SCAN_INTERVAL_MIN = 45.0
        ve.SCAN_INTERVAL_MAX = 60.0
        print("[Health] VisionEngine → scan cada 45-60s")
    except Exception:
        pass

    # 2. Reducir intervalo de alisha_analitica
    try:
        from alisha_analitica import get_alisha_analitica
        aa = get_alisha_analitica()
        if aa:
            aa.analysis_interval = 600  # 10 min en modo ahorro
            print("[Health] AlishaAnalitica → análisis cada 10 min")
    except Exception:
        pass

    # 3. Notificar a Cami — solo una vez, sin contradecirse
    mensaje = (
        f"Che Cami, la laptop está trabajando bastante ({razon}). "
        f"Voy a reducir mi actividad un rato para no calentar nada."
    )
    _notificar(mensaje, "preocupación")


def desactivar_modo_ahorro() -> None:
    """Desactiva el Modo Ahorro — restaura actividad normal."""
    global _modo_ahorro_activo
    with _lock:
        if not _modo_ahorro_activo:
            return
        _modo_ahorro_activo = False

    print("[Health] ✅ Modo ahorro desactivado — CPU normalizada")

    # Restaurar intervalos normales
    try:
        from vision_engine import get_vision_engine
        ve = get_vision_engine()
        ve.SCAN_INTERVAL_MIN = 10.0
        ve.SCAN_INTERVAL_MAX = 15.0
    except Exception:
        pass

    try:
        from alisha_analitica import get_alisha_analitica
        aa = get_alisha_analitica()
        if aa:
            aa.analysis_interval = 180
    except Exception:
        pass

    _notificar("CPU normalizada, ya estoy al 100% de nuevo.", "alegría")


def _notificar(mensaje: str, estado: str = "neutral") -> None:
    """Envía notificación al chat y por voz."""
    try:
        from web_app import socketio
        socketio.emit("respuesta", {"texto": mensaje, "estado_emocional": estado})
    except Exception:
        pass
    try:
        from tts_engine import speak
        threading.Thread(target=speak, args=(mensaje,), daemon=True).start()
    except Exception:
        pass
    print(f"[Health] {mensaje}")


def _monitor_loop() -> None:
    """Loop de monitoreo cada 30 segundos."""
    # Esperar 60s al arranque para que todo cargue
    time.sleep(60)

    cpu_alto_count = 0  # cuántos checks consecutivos con CPU alto

    while True:
        try:
            uso = get_uso_recursos()
            if not uso["ok"]:
                time.sleep(CHECK_INTERVAL)
                continue

            cpu = uso["cpu"]
            ram = uso["ram_mb"]

            # Log periódico (cada 5 minutos)
            print(f"[Health] CPU={cpu}% RAM={ram}MB modo_ahorro={_modo_ahorro_activo}")

            if cpu > CPU_UMBRAL_CRITICO:
                cpu_alto_count += 1
                if cpu_alto_count >= 2:  # 2 checks consecutivos = 1 minuto
                    activar_modo_ahorro(f"CPU {cpu}% (crítico)")
                    cpu_alto_count = 0
            elif cpu > CPU_UMBRAL_AHORRO:
                cpu_alto_count += 1
                if cpu_alto_count >= 3:  # 3 checks = 1.5 minutos sostenidos
                    activar_modo_ahorro(f"CPU {cpu}% sostenido")
                    cpu_alto_count = 0
            else:
                cpu_alto_count = 0
                # Si estaba en modo ahorro y CPU bajó, desactivar
                if _modo_ahorro_activo and cpu < CPU_UMBRAL_AHORRO * 0.7:
                    desactivar_modo_ahorro()

            if ram > RAM_UMBRAL_AHORRO and not _modo_ahorro_activo:
                activar_modo_ahorro(f"RAM {ram}MB")

        except Exception as e:
            print(f"[Health] Error en monitor: {e}")

        time.sleep(CHECK_INTERVAL)


def iniciar_monitor() -> None:
    """Inicia el monitor de salud en hilo daemon."""
    if not _PSUTIL_OK:
        print("[Health] psutil no disponible — monitor desactivado")
        return
    t = threading.Thread(target=_monitor_loop, daemon=True, name="HealthMonitor")
    t.start()
    print("[Health] ✓ Monitor de salud iniciado (umbral CPU: 15%)")
