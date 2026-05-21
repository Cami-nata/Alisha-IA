"""
Priority_Interrupt — interrupciones de alta prioridad.
Parte del sistema de Conciencia Situacional de Alisha.
"""

import threading
import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from silent_buffer import SilentBuffer

# Importación opcional con graceful degradation
try:
    import win32gui
    _WIN32_DISPONIBLE = True
except ImportError:
    _WIN32_DISPONIBLE = False

# Palabras clave que indican error en el título de ventana
_PALABRAS_CLAVE_ERROR = ("error", "fallo", "no responde", "detuvo")

# Umbral de cambios excesivos de ventana
_UMBRAL_CAMBIOS = 20
_VENTANA_SEGUNDOS = 60.0

# Mensaje hardcoded para cambios excesivos (Requisito 6.4)
_MENSAJE_CAMBIOS_EXCESIVOS = "Che, estás a mil, ¿no te estarás mareando con tantas pestañas?"

# Intervalo del thread de monitoreo
_INTERVALO_SEGUNDOS = 2


def detectar_error_titulo(titulo: str) -> bool:
    """
    Función pura: retorna True si el título contiene alguna palabra clave de error.
    Case-insensitive.

    Args:
        titulo: Título de la ventana activa.

    Returns:
        True si contiene al menos una palabra clave, False en caso contrario.
    """
    titulo_lower = titulo.lower()
    return any(kw in titulo_lower for kw in _PALABRAS_CLAVE_ERROR)


def detectar_cambios_excesivos(timestamps: list[float]) -> bool:
    """
    Función pura: retorna True si hay ≥ 20 timestamps dentro de alguna ventana de 60 segundos.

    Usa una ventana deslizante: para cada timestamp como punto de inicio,
    cuenta cuántos timestamps caen dentro de los siguientes 60 segundos.

    Args:
        timestamps: Lista de timestamps (float, epoch seconds) de cambios de ventana.

    Returns:
        True si se detectan cambios excesivos, False en caso contrario.
    """
    if len(timestamps) < _UMBRAL_CAMBIOS:
        return False

    ts_sorted = sorted(timestamps)
    n = len(ts_sorted)

    for i in range(n):
        # Contar cuántos timestamps están dentro de [ts_sorted[i], ts_sorted[i] + 60)
        limite = ts_sorted[i] + _VENTANA_SEGUNDOS
        count = 0
        for j in range(i, n):
            if ts_sorted[j] < limite:
                count += 1
            else:
                break
        if count >= _UMBRAL_CAMBIOS:
            return True

    return False


class PriorityInterrupt:
    """
    Monitorea eventos de alta prioridad en un thread daemon (intervalo 2s).

    Detecta:
    - Palabras clave de error en el título de la ventana activa.
    - Cambios de ventana excesivos (≥ 20 en 60 segundos).

    Expone `reinicio_event` (threading.Event) para que ReflectionTimer
    pueda suscribirse y reiniciar su contador (Requisito 6.5).
    """

    def __init__(self) -> None:
        self._buffer: "SilentBuffer | None" = None
        self._callback: Callable[[str], None] | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Event público para señalizar al ReflectionTimer que reinicie (Req 6.5)
        self.reinicio_event = threading.Event()

        # Ventana deslizante de timestamps de cambios de ventana
        self._cambios_timestamps: list[float] = []
        self._lock_cambios = threading.Lock()
        self._titulo_anterior: str = ""

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(self, buffer: "SilentBuffer", callback: Callable[[str], None]) -> None:
        """Arranca el thread daemon de monitoreo."""
        self._buffer = buffer
        self._callback = callback
        self._stop_event.clear()
        self.reinicio_event.clear()

        self._thread = threading.Thread(
            target=self._loop,
            name="PriorityInterrupt",
            daemon=True,
        )
        self._thread.start()

    def detener(self) -> None:
        """Detiene el thread limpiamente."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.wait(_INTERVALO_SEGUNDOS):
            try:
                self._tick()
            except Exception:
                pass

    def _tick(self) -> None:
        """Un ciclo de monitoreo: verifica título y cambios de ventana."""
        titulo = self._obtener_titulo_ventana()

        # Registrar cambio de ventana si el título cambió
        self._registrar_cambio_si_corresponde(titulo)

        # Detectar error en título
        if titulo and detectar_error_titulo(titulo):
            self._disparar_alerta("error_titulo", titulo)
            return

        # Detectar cambios excesivos
        with self._lock_cambios:
            timestamps_actuales = list(self._cambios_timestamps)

        if detectar_cambios_excesivos(timestamps_actuales):
            self._disparar_cambios_excesivos()

    # ------------------------------------------------------------------
    # Detección y disparo
    # ------------------------------------------------------------------

    def _obtener_titulo_ventana(self) -> str:
        """Retorna el título de la ventana activa, o '' si no disponible."""
        if not _WIN32_DISPONIBLE:
            return ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd) or ""
        except Exception:
            return ""

    def _registrar_cambio_si_corresponde(self, titulo: str) -> None:
        """Registra un cambio de ventana si el título cambió respecto al anterior."""
        if titulo != self._titulo_anterior:
            self._titulo_anterior = titulo
            ahora = time.time()
            limite = ahora - _VENTANA_SEGUNDOS
            with self._lock_cambios:
                self._cambios_timestamps.append(ahora)
                # Limpiar timestamps fuera de la ventana deslizante
                self._cambios_timestamps = [
                    t for t in self._cambios_timestamps if t >= limite
                ]

    def _disparar_alerta(self, motivo: str, detalle: str) -> None:
        """Registra alerta en el buffer, invoca callback y señaliza reinicio."""
        if self._buffer is not None:
            self._buffer.registrar("alerta", {"motivo": motivo, "detalle": detalle})

        if self._callback is not None:
            try:
                self._callback(detalle)
            except Exception:
                pass

        # Señalizar al ReflectionTimer que reinicie su contador (Req 6.5)
        self.reinicio_event.set()

    def _disparar_cambios_excesivos(self) -> None:
        """Dispara el mensaje hardcoded de cambios excesivos."""
        if self._buffer is not None:
            self._buffer.registrar(
                "alerta",
                {"motivo": "cambios_excesivos", "detalle": _MENSAJE_CAMBIOS_EXCESIVOS},
            )

        if self._callback is not None:
            try:
                self._callback(_MENSAJE_CAMBIOS_EXCESIVOS)
            except Exception:
                pass

        # Señalizar al ReflectionTimer que reinicie su contador (Req 6.5)
        self.reinicio_event.set()
