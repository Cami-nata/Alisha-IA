from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"


class SystemMode(str, Enum):
    IDLE = "IDLE"
    WORKING = "WORKING"
    THINKING = "THINKING"
    OVERLOADED = "OVERLOADED"


@dataclass
class AssistantState:
    estado: str = "neutral"
    hablando: bool = False
    texto: str = ""
    modo: SystemMode = SystemMode.IDLE
    ultima_actualizacion: str = ""


def _estado_por_defecto() -> dict[str, Any]:
    estado = asdict(AssistantState())
    estado["modo"] = AssistantState().modo.value
    return estado


def cargar_estado() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _estado_por_defecto()


def guardar_estado(estado: dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def actualizar_estado(
    estado: str | None = None,
    hablando: bool | None = None,
    texto: str | None = None,
    modo: SystemMode | str | None = None,
    ultima_actualizacion: str | None = None,
) -> dict[str, Any]:
    actual = cargar_estado()
    if estado is not None:
        actual["estado"] = estado
    if hablando is not None:
        actual["hablando"] = hablando
    if texto is not None:
        actual["texto"] = texto
    if modo is not None:
        actual["modo"] = SystemMode(str(modo)).value
    if ultima_actualizacion is not None:
        actual["ultima_actualizacion"] = ultima_actualizacion
    guardar_estado(actual)
    return actual


def estado_por_defecto() -> dict[str, Any]:
    return _estado_por_defecto()


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM STATE MANAGER — Gestor autónomo de estados (FASE 9 — JCySharp)
# ══════════════════════════════════════════════════════════════════════════════

import threading
import time as _time


class SystemStateManager:
    """
    Gestor autónomo de estados del sistema.
    Corre en daemon y actualiza el modo según métricas reales de CPU/RAM.

    Reglas:
    - IDLE: sin actividad, CPU < 15%, sin consultas pendientes
    - WORKING: ejecutando herramienta o procesando consulta
    - THINKING: esperando respuesta del LLM
    - OVERLOADED: CPU > 80% o RAM > 90% → reducir actividad, NO apagarse
    """

    CPU_OVERLOAD_THRESHOLD = 80.0   # % CPU para entrar en OVERLOADED
    RAM_OVERLOAD_THRESHOLD = 90.0   # % RAM para entrar en OVERLOADED
    CPU_AHORRO_THRESHOLD   = 15.0   # % CPU para activar modo ahorro (README)
    EVAL_INTERVAL          = 5.0    # segundos entre evaluaciones

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._modo_actual = SystemMode.IDLE
        self._ultima_consulta = 0.0
        self._en_overload = False
        self._lock = threading.Lock()

    def iniciar(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="SystemStateManager"
        )
        self._thread.start()
        print("[SystemState] ✓ Gestor de estados iniciado (IDLE/WORKING/THINKING/OVERLOADED)")

    def detener(self) -> None:
        self._running = False

    def set_working(self) -> None:
        """Llamar cuando Alisha empieza a procesar una consulta."""
        with self._lock:
            self._ultima_consulta = _time.time()
        self._actualizar_modo(SystemMode.WORKING)

    def set_thinking(self) -> None:
        """Llamar cuando Alisha espera respuesta del LLM."""
        with self._lock:
            self._ultima_consulta = _time.time()
        self._actualizar_modo(SystemMode.THINKING)

    def set_idle(self) -> None:
        """Llamar cuando Alisha termina de procesar."""
        self._actualizar_modo(SystemMode.IDLE)

    def is_overloaded(self) -> bool:
        return self._en_overload

    def get_modo(self) -> SystemMode:
        return self._modo_actual

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            _time.sleep(self.EVAL_INTERVAL)

    def _tick(self) -> None:
        """Evalúa el estado del sistema y actualiza el modo."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
        except Exception:
            cpu, ram = 0.0, 0.0

        # OVERLOADED: CPU o RAM críticos
        if cpu > self.CPU_OVERLOAD_THRESHOLD or ram > self.RAM_OVERLOAD_THRESHOLD:
            if not self._en_overload:
                self._en_overload = True
                print(f"[SystemState] ⚠ OVERLOADED (CPU={cpu:.0f}%, RAM={ram:.0f}%) — reduciendo actividad")
                self._aplicar_modo_overload()
            self._actualizar_modo(SystemMode.OVERLOADED)
            return

        # Salir de OVERLOADED cuando bajan los recursos
        if self._en_overload and cpu < 60.0 and ram < 80.0:
            self._en_overload = False
            print("[SystemState] ✓ Saliendo de OVERLOADED — recursos normalizados")

        # Modo Ahorro (README): CPU > 15% sostenido → reducir actividad proactiva
        if cpu > self.CPU_AHORRO_THRESHOLD:
            self._aplicar_modo_ahorro()

        # IDLE: sin consultas recientes (> 30s)
        with self._lock:
            tiempo_sin_consulta = _time.time() - self._ultima_consulta

        if tiempo_sin_consulta > 30 and self._modo_actual not in (
            SystemMode.WORKING, SystemMode.THINKING
        ):
            self._actualizar_modo(SystemMode.IDLE)

    def _actualizar_modo(self, nuevo_modo: SystemMode) -> None:
        if nuevo_modo != self._modo_actual:
            self._modo_actual = nuevo_modo
            actualizar_estado(modo=nuevo_modo)
            print(f"[SystemState] → {nuevo_modo.value}")

    def _aplicar_modo_overload(self) -> None:
        """
        OVERLOADED: reducir razonamiento, priorizar estabilidad.
        NO apagarse — seguir respondiendo pero con menos recursos.
        """
        # Pausar reflexiones proactivas temporalmente
        try:
            from alisha_silencio import activar_silencio_global
            activar_silencio_global(duracion_segundos=120, motivo="overload")
        except Exception:
            pass

        # Reducir dopamina para que brain.py use menos tokens
        try:
            from brain import get_brain
            brain = get_brain()
            brain._emotional.dopamina = max(0.2, brain._emotional.dopamina - 0.2)
        except Exception:
            pass

    def _aplicar_modo_ahorro(self) -> None:
        """Modo Ahorro: reducir actividad proactiva sin apagar nada."""
        # El semáforo de silencio ya maneja esto automáticamente
        pass


# ── Singleton ──────────────────────────────────────────────────────────────────
_state_manager: SystemStateManager | None = None


def get_state_manager() -> SystemStateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = SystemStateManager()
    return _state_manager


def iniciar_state_manager() -> SystemStateManager:
    """Inicia el gestor autónomo de estados. Llamar al arranque de Alisha."""
    mgr = get_state_manager()
    mgr.iniciar()
    return mgr
