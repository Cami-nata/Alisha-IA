"""
Context_Monitor — recolección de contexto del entorno.
Parte del sistema de Conciencia Situacional de Alisha.
"""

import threading
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from silent_buffer import SilentBuffer

# Importaciones opcionales con graceful degradation
try:
    import psutil
    _PSUTIL_DISPONIBLE = True
except ImportError:
    _PSUTIL_DISPONIBLE = False

try:
    import win32gui
    import win32process
    _WIN32_DISPONIBLE = True
except ImportError:
    _WIN32_DISPONIBLE = False

try:
    from pynput import keyboard as pynput_keyboard
    _PYNPUT_DISPONIBLE = True
except ImportError:
    _PYNPUT_DISPONIBLE = False


def calcular_ritmo(timestamps: list[float], duracion_minutos: float) -> float:
    """
    Calcula el ritmo de escritura en teclas por minuto.

    Args:
        timestamps: Lista de timestamps (float) de teclas presionadas.
        duracion_minutos: Duración del período en minutos.

    Returns:
        Teclas por minuto como float.
    """
    if duracion_minutos <= 0:
        return 0.0
    return len(timestamps) / duracion_minutos


class ContextMonitor:
    """
    Recolecta contexto del entorno cada 30 segundos en un thread daemon de baja prioridad.
    Registra snapshots en el SilentBuffer como eventos tipo 'contexto'.
    """

    _INTERVALO_SEGUNDOS = 30

    def __init__(self) -> None:
        self._buffer: "SilentBuffer | None" = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Registro de cambios de ventana (timestamps del último minuto)
        self._cambios_ventana: list[float] = []
        self._ventana_anterior: str = ""
        self._lock_ventana = threading.Lock()

        # Registro de teclas presionadas (timestamps)
        self._teclas_timestamps: list[float] = []
        self._lock_teclas = threading.Lock()
        self._listener: object | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(self, buffer: "SilentBuffer") -> None:
        """Arranca el thread de monitoreo y el listener de teclado."""
        self._buffer = buffer
        self._stop_event.clear()

        self._iniciar_listener_teclado()

        self._thread = threading.Thread(
            target=self._loop,
            name="ContextMonitor",
            daemon=True,
        )
        self._thread.start()

    def detener(self) -> None:
        """Detiene el thread limpiamente."""
        self._stop_event.set()
        self._detener_listener_teclado()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.wait(self._INTERVALO_SEGUNDOS):
            try:
                self._tick()
            except Exception:
                pass

    def _tick(self) -> None:
        """Recolecta un snapshot y lo registra en el buffer."""
        if self._buffer is None:
            return
        snapshot = self._construir_snapshot()
        self._buffer.registrar("contexto", snapshot)

        # FASE 4 — Sentidos simulados: actualizar estado emocional con señales del entorno
        try:
            from emotion_engine import EmotionEngine
            EmotionEngine.get_instance().actualizar_desde_contexto(snapshot)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Construcción del snapshot
    # ------------------------------------------------------------------

    def _construir_snapshot(self) -> dict:
        """
        Construye el snapshot del entorno actual.
        Omite campos no disponibles sin lanzar excepción.
        """
        datos: dict = {}

        # Hora del sistema (siempre disponible)
        datos["hora"] = datetime.now().strftime("%H:%M")

        # App activa y título de ventana
        app_activa, titulo_ventana = self._obtener_ventana_activa()
        datos["app_activa"] = app_activa
        datos["titulo_ventana"] = titulo_ventana

        # Registrar cambio de ventana si corresponde
        self._registrar_cambio_ventana(titulo_ventana)

        # Nivel de batería
        datos["bateria"] = self._obtener_bateria()

        # Cambios de ventana en el último minuto
        datos["cambios_ventana"] = self._contar_cambios_ultimo_minuto()

        # Ritmo de escritura
        datos["teclas_por_minuto"] = self._calcular_ritmo_actual()

        return datos

    def _obtener_ventana_activa(self) -> tuple[str | None, str | None]:
        """Retorna (app_activa, titulo_ventana) o (None, None) si no disponible."""
        if not _WIN32_DISPONIBLE:
            return None, None
        try:
            hwnd = win32gui.GetForegroundWindow()
            titulo = win32gui.GetWindowText(hwnd)

            app_activa = None
            if _PSUTIL_DISPONIBLE:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    app_activa = proc.name()
                except Exception:
                    pass

            return app_activa or None, titulo or None
        except Exception:
            return None, None

    def _obtener_bateria(self) -> int | None:
        """Retorna el nivel de batería como entero o None si no disponible."""
        if not _PSUTIL_DISPONIBLE:
            return None
        try:
            bateria = psutil.sensors_battery()
            if bateria is None:
                return None
            return int(bateria.percent)
        except Exception:
            return None

    def _registrar_cambio_ventana(self, titulo_actual: str | None) -> None:
        """Registra un cambio de ventana si el título cambió."""
        titulo = titulo_actual or ""
        with self._lock_ventana:
            if titulo != self._ventana_anterior:
                self._ventana_anterior = titulo
                import time
                self._cambios_ventana.append(time.time())

    def _contar_cambios_ultimo_minuto(self) -> int:
        """Cuenta los cambios de ventana ocurridos en el último minuto."""
        import time
        ahora = time.time()
        limite = ahora - 60.0
        with self._lock_ventana:
            self._cambios_ventana = [t for t in self._cambios_ventana if t >= limite]
            return len(self._cambios_ventana)

    def _calcular_ritmo_actual(self) -> float | None:
        """Calcula teclas por minuto en el último minuto."""
        if not _PYNPUT_DISPONIBLE:
            return None
        import time
        ahora = time.time()
        limite = ahora - 60.0
        with self._lock_teclas:
            self._teclas_timestamps = [t for t in self._teclas_timestamps if t >= limite]
            timestamps_recientes = list(self._teclas_timestamps)

        if not timestamps_recientes:
            return 0.0
        return calcular_ritmo(timestamps_recientes, 1.0)

    # ------------------------------------------------------------------
    # Listener de teclado (pynput)
    # ------------------------------------------------------------------

    def _iniciar_listener_teclado(self) -> None:
        """Inicia el listener de teclado no intrusivo si pynput está disponible."""
        if not _PYNPUT_DISPONIBLE:
            return
        try:
            self._listener = pynput_keyboard.Listener(
                on_press=self._on_key_press,
                suppress=False,  # no intrusivo: no bloquea las teclas
            )
            self._listener.start()  # type: ignore[union-attr]
        except Exception:
            self._listener = None

    def _detener_listener_teclado(self) -> None:
        """Detiene el listener de teclado si está activo."""
        if self._listener is not None:
            try:
                self._listener.stop()  # type: ignore[union-attr]
            except Exception:
                pass
            self._listener = None

    def _on_key_press(self, key: object) -> None:
        """Callback del listener de teclado: registra el timestamp de la tecla."""
        try:
            import time
            with self._lock_teclas:
                self._teclas_timestamps.append(time.time())
        except Exception:
            pass

