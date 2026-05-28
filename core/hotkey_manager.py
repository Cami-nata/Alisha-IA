"""
core/hotkey_manager.py — Gestor de hotkeys globales de Alisha IA.

Hotkeys registradas:
  INSERT          → toggle micrófono on/off
  CTRL+SHIFT+A    → mostrar/ocultar ventana principal
  ESC             → cancelar tarea en curso
  CTRL+SHIFT+S    → screenshot → brain para análisis

Principio fail-silent: si una hotkey ya está en uso, loguear y continuar.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Logger ────────────────────────────────────────────────────────────────────
logger = logging.getLogger("HotkeyManager")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
    )

# ── Importación opcional de keyboard ─────────────────────────────────────────
try:
    import keyboard as _keyboard
    _KEYBOARD_OK = True
except ImportError:
    _keyboard = None  # type: ignore
    _KEYBOARD_OK = False
    logger.warning(
        "La librería 'keyboard' no está instalada. "
        "Las hotkeys globales no estarán disponibles. "
        "Instalá con: pip install keyboard"
    )


class HotkeyManager:
    """
    Gestor de hotkeys globales de Alisha IA.

    Registra cuatro atajos de teclado globales que funcionan desde cualquier
    ventana activa del sistema operativo:
      - INSERT          → toggle micrófono (idle ↔ listening)
      - CTRL+SHIFT+A    → mostrar/ocultar ventana principal
      - ESC             → cancelar tarea en curso
      - CTRL+SHIFT+S    → screenshot → brain para análisis

    Principio fail-silent: si una hotkey ya está en uso por otra aplicación,
    se registra el conflicto en el log y se continúa con las demás.
    """

    # Nombres de hotkeys para registro y log
    HOTKEYS: dict[str, str] = {
        "insert":       "INSERT → toggle micrófono",
        "ctrl+shift+a": "CTRL+SHIFT+A → mostrar/ocultar ventana",
        "esc":          "ESC → cancelar tarea",
        "ctrl+shift+s": "CTRL+SHIFT+S → screenshot → brain",
    }

    def __init__(self) -> None:
        self._mic_active: bool = False
        self._registered: list[str] = []
        self._lock = threading.Lock()

    # ── API pública ───────────────────────────────────────────────────────────

    def register_all(self) -> None:
        """
        Registra las 4 hotkeys globales.
        Captura conflictos con try/except — principio fail-silent (Req 2.11).
        """
        if not _KEYBOARD_OK:
            logger.warning(
                "No se pueden registrar hotkeys: librería 'keyboard' no disponible."
            )
            return

        # Mapa hotkey → handler
        hotkey_map = {
            "insert":       self._on_insert,
            "ctrl+shift+a": self._on_ctrl_shift_a,
            "esc":          self._on_esc,
            "ctrl+shift+s": self._on_ctrl_shift_s,
        }

        for combo, handler in hotkey_map.items():
            self._register_one(combo, handler)

    def unregister_all(self) -> None:
        """Desregistra todas las hotkeys registradas por este manager."""
        if not _KEYBOARD_OK:
            return

        for combo in list(self._registered):
            try:
                _keyboard.remove_hotkey(combo)
                logger.info("Hotkey desregistrada: %s", combo.upper())
            except Exception as e:
                logger.warning("No se pudo desregistrar '%s': %s", combo, e)

        self._registered.clear()

    def is_mic_active(self) -> bool:
        """Retorna True si el micrófono está en estado 'listening'."""
        with self._lock:
            return self._mic_active

    # ── Handlers internos ─────────────────────────────────────────────────────

    def _on_insert(self) -> None:
        """
        INSERT → toggle micrófono on/off.
        Actualiza AssistantState según el nuevo estado (Req 2.4, 2.5).
        """
        with self._lock:
            self._mic_active = not self._mic_active
            nuevo_estado = self._mic_active

        if nuevo_estado:
            logger.info("🎤 Micrófono ACTIVADO (estado: listening)")
            self._set_assistant_state_working()
            self._notify_gemini_live(activar=True)
        else:
            logger.info("🎤 Micrófono DESACTIVADO (estado: idle)")
            self._set_assistant_state_idle()
            self._notify_gemini_live(activar=False)

    def _on_ctrl_shift_a(self) -> None:
        """
        CTRL+SHIFT+A → mostrar/ocultar ventana principal (Req 2.6).
        Intenta con win32gui primero; fallback a pyautogui.
        """
        logger.info("🪟 Toggle ventana principal (CTRL+SHIFT+A)")
        try:
            self._toggle_window_win32()
        except Exception as e:
            logger.warning("win32gui no disponible, usando pyautogui: %s", e)
            try:
                self._toggle_window_pyautogui()
            except Exception as e2:
                logger.warning("No se pudo toggle la ventana: %s", e2)

    def _on_esc(self) -> None:
        """
        ESC → cancelar tarea en curso.
        Llama a tools.pc_controller.abort_all_actions() (Req 2.7).
        """
        logger.info("⛔ ESC presionado — cancelando tarea en curso")
        try:
            from tools.pc_controller import abort_all_actions
            resultado = abort_all_actions()
            logger.info("abort_all_actions: %s", resultado)
        except ImportError:
            # Fallback: intentar desde raíz del proyecto
            try:
                from pc_controller import abort_all_actions  # type: ignore
                resultado = abort_all_actions()
                logger.info("abort_all_actions (raíz): %s", resultado)
            except Exception as e2:
                logger.warning("No se pudo llamar abort_all_actions: %s", e2)
        except Exception as e:
            logger.warning("Error al abortar acciones: %s", e)

    def _on_ctrl_shift_s(self) -> None:
        """
        CTRL+SHIFT+S → screenshot → brain para análisis (Req 2.8).
        Guarda en data/ con timestamp y notifica al brain.
        """
        logger.info("📸 Screenshot solicitado (CTRL+SHIFT+S)")
        try:
            import pyautogui
            from config.settings import DATA_DIR

            # Crear directorio de screenshots si no existe
            screenshots_dir = Path(DATA_DIR) / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            # Nombre con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = screenshots_dir / f"screenshot_{timestamp}.png"

            # Tomar screenshot
            img = pyautogui.screenshot()
            img.save(str(ruta))
            logger.info("Screenshot guardado en: %s", ruta)

            # Notificar al brain para análisis
            self._notify_brain_screenshot(str(ruta))

        except Exception as e:
            logger.warning("Error al tomar screenshot: %s", e)

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _register_one(self, combo: str, handler) -> None:
        """
        Registra una hotkey individual con manejo de conflictos (Req 2.11, 5.6).
        Si ya está en uso, loguea y continúa sin lanzar excepción.
        """
        descripcion = self.HOTKEYS.get(combo, combo.upper())
        try:
            _keyboard.add_hotkey(combo, handler, suppress=False)
            self._registered.append(combo)
            logger.info("✓ Hotkey registrada: %s — %s", combo.upper(), descripcion)
        except Exception as e:
            # Principio fail-silent: loguear conflicto y continuar
            logger.warning(
                "ADVERTENCIA: No se pudo registrar %s (%s): %s — continuando con las demás hotkeys.",
                combo.upper(),
                descripcion,
                e,
            )

    def _set_assistant_state_working(self) -> None:
        """Actualiza AssistantState a WORKING/listening."""
        try:
            from core.assistant_state import actualizar_estado, SystemMode
            actualizar_estado(
                estado="escuchando",
                modo=SystemMode.WORKING,
                ultima_actualizacion=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.warning("No se pudo actualizar AssistantState a WORKING: %s", e)

    def _set_assistant_state_idle(self) -> None:
        """Actualiza AssistantState a IDLE."""
        try:
            from core.assistant_state import actualizar_estado, SystemMode
            actualizar_estado(
                estado="neutral",
                modo=SystemMode.IDLE,
                ultima_actualizacion=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.warning("No se pudo actualizar AssistantState a IDLE: %s", e)

    def _notify_gemini_live(self, activar: bool) -> None:
        """Notifica al Gemini Live Client para activar/desactivar el micrófono."""
        try:
            from services.gemini_live_client import get_gemini_live_client
            client = get_gemini_live_client()
            if activar:
                # Iniciar en hilo para no bloquear el handler de hotkey
                t = threading.Thread(
                    target=client.start_listening,
                    daemon=True,
                    name="GeminiLive-Start",
                )
                t.start()
            else:
                client.stop_listening()
        except ImportError:
            # Gemini Live Client aún no implementado — no es error crítico
            logger.debug("services.gemini_live_client no disponible (aún no implementado).")
        except Exception as e:
            logger.warning("Error al notificar Gemini Live Client: %s", e)

    def _notify_brain_screenshot(self, ruta: str) -> None:
        """Envía el screenshot al brain para análisis visual."""
        try:
            from core.brain import get_brain
            brain = get_brain()
            # Construir mensaje para el brain con la ruta del screenshot
            mensaje = f"[Screenshot automático] Analiza esta captura de pantalla: {ruta}"
            # Ejecutar en hilo para no bloquear el handler de hotkey
            t = threading.Thread(
                target=brain.chat,
                args=(mensaje,),
                daemon=True,
                name="Brain-Screenshot",
            )
            t.start()
            logger.info("Screenshot enviado al brain para análisis.")
        except Exception as e:
            logger.warning("No se pudo notificar al brain sobre el screenshot: %s", e)

    def _toggle_window_win32(self) -> None:
        """Toggle ventana principal usando win32gui."""
        import win32gui
        import win32con

        # Buscar ventana de Alisha por título
        titulos_alisha = ["Alisha", "Alisha IA", "VTube Studio"]
        hwnd = None
        for titulo in titulos_alisha:
            hwnd = win32gui.FindWindow(None, titulo)
            if hwnd:
                break

        if not hwnd:
            logger.debug("No se encontró ventana de Alisha con win32gui.")
            return

        # Toggle: si está visible → ocultar, si está oculta → mostrar
        if win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            logger.info("Ventana ocultada.")
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("Ventana mostrada.")

    def _toggle_window_pyautogui(self) -> None:
        """Toggle ventana principal usando pyautogui como fallback."""
        import pyautogui
        # Usar Alt+Tab como fallback básico para traer la ventana al frente
        pyautogui.hotkey("alt", "tab")
        logger.info("Toggle ventana via pyautogui (Alt+Tab).")


# ── Singleton ─────────────────────────────────────────────────────────────────

_hotkey_manager: Optional[HotkeyManager] = None
_singleton_lock = threading.Lock()


def get_hotkey_manager() -> HotkeyManager:
    """Retorna la instancia singleton del HotkeyManager."""
    global _hotkey_manager
    if _hotkey_manager is None:
        with _singleton_lock:
            if _hotkey_manager is None:
                _hotkey_manager = HotkeyManager()
    return _hotkey_manager


def iniciar_hotkeys() -> None:
    """
    Inicializa y registra todas las hotkeys globales de Alisha.
    Llamar al arranque del sistema.
    """
    manager = get_hotkey_manager()
    manager.register_all()
    logger.info(
        "HotkeyManager iniciado. Hotkeys activas: %s",
        ", ".join(manager._registered) if manager._registered else "ninguna",
    )
