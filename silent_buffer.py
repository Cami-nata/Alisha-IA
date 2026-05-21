"""
Silent_Buffer — búfer thread-safe de eventos del sistema.
Parte del sistema de Conciencia Situacional de Alisha.
"""

import collections
import threading
from datetime import datetime


class SilentBuffer:
    """Búfer thread-safe de eventos con capacidad máxima de 500 (FIFO)."""

    def __init__(self) -> None:
        self._deque: collections.deque = collections.deque(maxlen=500)
        self._lock = threading.Lock()

    def registrar(self, tipo: str, datos: dict) -> None:
        """Agrega un evento al búfer con timestamp ISO 8601 automático."""
        try:
            evento = {
                "timestamp": datetime.now().isoformat(),
                "tipo": tipo,
                "datos": datos,
            }
            with self._lock:
                self._deque.append(evento)
        except Exception:
            pass

    def vaciar(self) -> list[dict]:
        """Retorna todos los eventos en orden de inserción y limpia el búfer."""
        try:
            with self._lock:
                eventos = list(self._deque)
                self._deque.clear()
            return eventos
        except Exception:
            return []

    def __len__(self) -> int:
        """Retorna la cantidad actual de eventos en el búfer."""
        try:
            with self._lock:
                return len(self._deque)
        except Exception:
            return 0
