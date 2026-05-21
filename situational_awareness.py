"""
situational_awareness.py — Orquestador principal del sistema de Conciencia Situacional.
Parte del sistema de Conciencia Situacional de Alisha.
"""

import logging
from typing import Callable

from atlas_memory import AtlasMemory
from context_monitor import ContextMonitor
from priority_interrupt import PriorityInterrupt
from proactive_notifier import ProactiveNotifier
from reflection_timer import ReflectionTimer
from silent_buffer import SilentBuffer

logger = logging.getLogger(__name__)


class SituationalAwareness:
    """
    Orquestador principal que instancia y conecta todos los módulos
    del sistema de Conciencia Situacional de Alisha.
    """

    def __init__(self) -> None:
        self._buffer: SilentBuffer | None = None
        self._context_monitor: ContextMonitor | None = None
        self._priority_interrupt: PriorityInterrupt | None = None
        self._atlas: AtlasMemory | None = None
        self._reflection_timer: ReflectionTimer | None = None
        self._proactive_notifier = None

    def iniciar(self, callback: Callable[[str], None]) -> None:
        """
        Crea e inicia todos los módulos en orden.

        Orden de arranque: buffer → context_monitor → priority_interrupt → reflection_timer
        El atlas_memory no requiere arranque (no tiene thread propio).

        Si algún módulo falla al iniciar, se loguea silenciosamente y se continúa.

        Args:
            callback: Función que recibe el texto generado por el LLM o alertas urgentes.
        """
        # 1. Silent Buffer (sin thread, siempre disponible)
        try:
            self._buffer = SilentBuffer()
        except Exception as e:
            logger.debug("SilentBuffer no pudo iniciar: %s", e)
            self._buffer = None

        # 2. Atlas Memory (sin thread, solo I/O)
        try:
            self._atlas = AtlasMemory()
        except Exception as e:
            logger.debug("AtlasMemory no pudo iniciar: %s", e)
            self._atlas = None

        # 3. Context Monitor
        try:
            self._context_monitor = ContextMonitor()
            if self._buffer is not None:
                self._context_monitor.iniciar(self._buffer)
        except Exception as e:
            logger.debug("ContextMonitor no pudo iniciar: %s", e)
            self._context_monitor = None

        # 4. Priority Interrupt
        try:
            self._priority_interrupt = PriorityInterrupt()
            if self._buffer is not None:
                self._priority_interrupt.iniciar(self._buffer, callback)
        except Exception as e:
            logger.debug("PriorityInterrupt no pudo iniciar: %s", e)
            self._priority_interrupt = None

        # 5. Reflection Timer
        try:
            self._reflection_timer = ReflectionTimer()
            # Suscribir el reinicio_event del PriorityInterrupt al ReflectionTimer
            if self._priority_interrupt is not None:
                self._reflection_timer.suscribir_reinicio(
                    self._priority_interrupt.reinicio_event
                )
            if self._buffer is not None and self._atlas is not None:
                self._reflection_timer.iniciar(self._buffer, self._atlas, callback)
        except Exception as e:
            logger.debug("ReflectionTimer no pudo iniciar: %s", e)
            self._reflection_timer = None

        try:
            self._proactive_notifier = ProactiveNotifier()
            if self._reflection_timer is not None:
                self._reflection_timer.conectar_proactive_notifier(self._proactive_notifier)
        except Exception as e:
            logger.debug("ProactiveNotifier no pudo iniciar: %s", e)
            self._proactive_notifier = None

    def detener(self) -> None:
        """
        Detiene todos los módulos en orden inverso al arranque.
        Cada detención es independiente: si una falla, continúa con las demás.
        """
        for nombre, modulo in [
            ("ReflectionTimer", self._reflection_timer),
            ("PriorityInterrupt", self._priority_interrupt),
            ("ContextMonitor", self._context_monitor),
        ]:
            if modulo is not None:
                try:
                    modulo.detener()
                except Exception as e:
                    logger.debug("%s no pudo detenerse: %s", nombre, e)

        self._reflection_timer = None
        self._priority_interrupt = None
        self._context_monitor = None
        self._atlas = None
        self._buffer = None
        self._proactive_notifier = None
