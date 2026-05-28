"""
security_manager.py — Sistema de seguridad con confirmación para Alisha IA.

Intercepta acciones peligrosas antes de ejecutarlas y solicita confirmación
al usuario en voseo rioplatense. Timeout de 30 segundos.

Principio fail-silent: toda excepción interna retorna True (permite la acción).
"""

from __future__ import annotations

import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Acciones peligrosas (requieren confirmación) ──────────────────────────────
ACCIONES_PELIGROSAS: set[str] = {
    "eliminar_archivo",
    "eliminar_carpeta",
    "enviar_email",
    "enviar_whatsapp",
    "ejecutar_terminal",
    "instalar_programa",
    "acceder_credenciales",
    "power",
    "ejecutar_codigo",
}

# ── Whitelist de operaciones seguras (sin confirmación) ───────────────────────
WHITELIST_SEGURA: set[str] = {
    "abrir_app",
    "buscar_internet",
    "leer_archivo",
    "reproducir_musica",
    "screenshot",
    "responder_pregunta",
    "navegar_web",
    "buscar_web",
}

# ── Palabras de confirmación ──────────────────────────────────────────────────
PALABRAS_CONFIRMACION: set[str] = {
    "sí", "si", "confirmar", "dale", "ok", "sí dale", "si dale",
}

# ── Palabras de cancelación ───────────────────────────────────────────────────
PALABRAS_CANCELACION: set[str] = {
    "no", "cancelar", "para", "stop", "nope",
}

# ── Timeout de confirmación (segundos) ───────────────────────────────────────
CONFIRMATION_TIMEOUT: int = 30


class SecurityManager:
    """
    Gestiona la seguridad de acciones de Alisha.

    Flujo para acciones peligrosas:
      1. Alisha anuncia la acción en voseo rioplatense.
      2. Espera respuesta del usuario hasta 30 segundos.
      3. Si confirma → ejecuta. Si cancela o timeout → cancela.
    """

    def __init__(self):
        self._pending_event: Optional[threading.Event] = None
        self._pending_result: Optional[bool] = None
        self._pending_lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    # ── API pública ────────────────────────────────────────────────────────────

    def is_dangerous(self, action: str) -> bool:
        """
        Retorna True si la acción requiere confirmación del usuario.

        Args:
            action: Nombre de la acción a verificar.

        Returns:
            True si la acción está en la lista de acciones peligrosas.
        """
        try:
            return action.lower() in ACCIONES_PELIGROSAS
        except Exception:
            return False

    def request_confirmation(self, action: str, description: str = "") -> bool:
        """
        Solicita confirmación al usuario para una acción peligrosa.

        Anuncia la acción en voseo rioplatense y espera respuesta por 30 segundos.
        Si no hay respuesta o se cancela, retorna False.

        Args:
            action: Nombre de la acción a confirmar.
            description: Descripción legible de lo que se va a hacer.

        Returns:
            True si el usuario confirmó, False si canceló o hubo timeout.
        """
        try:
            # Si la acción está en whitelist, permitir sin confirmación
            if action.lower() in WHITELIST_SEGURA:
                return True

            # Preparar el evento de confirmación
            with self._pending_lock:
                # Cancelar cualquier confirmación pendiente anterior
                self._cancel_pending()

                event = threading.Event()
                self._pending_event = event
                self._pending_result = None

            # Construir mensaje de anuncio en voseo rioplatense
            desc_texto = description if description else action
            mensaje = f"Voy a {desc_texto}. ¿Confirmás? (sí/no)"

            # Anunciar la acción (TTS + print)
            self._anunciar(mensaje)

            # Iniciar timer de timeout
            timer = threading.Timer(CONFIRMATION_TIMEOUT, self._on_timeout)
            with self._pending_lock:
                self._timer = timer
            timer.start()

            # Esperar respuesta del usuario
            event.wait(timeout=CONFIRMATION_TIMEOUT + 1)

            # Leer resultado
            with self._pending_lock:
                result = self._pending_result
                self._pending_event = None
                self._pending_result = None
                if self._timer:
                    self._timer.cancel()
                    self._timer = None

            if result is True:
                return True
            else:
                # Cancelado o timeout
                self._anunciar("Dale, lo cancelo. Avisame si querés que lo haga.")
                return False

        except Exception as e:
            logger.warning(f"[SecurityManager] Error en request_confirmation: {e}")
            return True  # fail-silent: permite la acción si hay error interno

    def confirm(self, response: str) -> None:
        """
        Procesa la respuesta del usuario para una confirmación pendiente.

        Llamar cuando llega una respuesta de voz o WhatsApp.

        Args:
            response: Texto de la respuesta del usuario.
        """
        try:
            resp = response.strip().lower()

            # Verificar si es confirmación o cancelación
            if any(palabra in resp for palabra in PALABRAS_CONFIRMACION):
                resultado = True
            elif any(palabra in resp for palabra in PALABRAS_CANCELACION):
                resultado = False
            else:
                # Respuesta no reconocida — no hacer nada, seguir esperando
                return

            with self._pending_lock:
                if self._pending_event is not None:
                    self._pending_result = resultado
                    self._pending_event.set()
                    if self._timer:
                        self._timer.cancel()
                        self._timer = None

        except Exception as e:
            logger.warning(f"[SecurityManager] Error en confirm: {e}")

    def cancel(self) -> None:
        """
        Cancela la confirmación pendiente (equivale a responder 'no').
        """
        try:
            with self._pending_lock:
                if self._pending_event is not None:
                    self._pending_result = False
                    self._pending_event.set()
                    if self._timer:
                        self._timer.cancel()
                        self._timer = None
        except Exception as e:
            logger.warning(f"[SecurityManager] Error en cancel: {e}")

    def is_safe(self, action: str) -> bool:
        """
        Retorna True si la acción está en la whitelist (no requiere confirmación).

        Args:
            action: Nombre de la acción a verificar.

        Returns:
            True si la acción es segura (whitelist).
        """
        try:
            return action.lower() in WHITELIST_SEGURA
        except Exception:
            return True  # fail-silent

    # ── Métodos internos ───────────────────────────────────────────────────────

    def _on_timeout(self) -> None:
        """Callback del timer: cancela la confirmación por timeout."""
        try:
            with self._pending_lock:
                if self._pending_event is not None and not self._pending_event.is_set():
                    self._pending_result = False
                    self._pending_event.set()
                    self._timer = None
        except Exception as e:
            logger.warning(f"[SecurityManager] Error en timeout: {e}")

    def _cancel_pending(self) -> None:
        """Cancela cualquier confirmación pendiente. Llamar con _pending_lock."""
        if self._pending_event is not None and not self._pending_event.is_set():
            self._pending_result = False
            self._pending_event.set()
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _anunciar(self, mensaje: str) -> None:
        """
        Anuncia un mensaje por TTS y lo imprime en consola.
        Fail-silent: si TTS falla, solo imprime.
        """
        print(f"[Alisha] {mensaje}")
        try:
            from audio_visual_sync import get_audio_visual_sync
            avs = get_audio_visual_sync()
            avs.speak(mensaje, sarcasm_score=0.0,
                      emotional_state="neutral", async_mode=True)
        except Exception:
            pass
        try:
            from web_app import socketio as _sio
            _sio.emit("respuesta", {
                "texto": mensaje,
                "estado_emocional": "neutral",
                "fuente": "security",
            })
        except Exception:
            pass


# ── Función global de conveniencia ────────────────────────────────────────────

def check_action(action: str, description: str = "") -> bool:
    """
    Verifica si una acción puede ejecutarse.

    - Si la acción está en la whitelist → True (sin confirmación).
    - Si la acción es peligrosa → solicita confirmación al usuario.
    - Si la acción no está en ninguna lista → True (permite por defecto).
    - Si hay cualquier error interno → True (fail-silent).

    Args:
        action: Nombre de la acción a verificar.
        description: Descripción legible de lo que se va a hacer.

    Returns:
        True si la acción puede ejecutarse (segura o confirmada).
    """
    try:
        mgr = get_security_manager()

        # Whitelist: permitir sin confirmación
        if mgr.is_safe(action):
            return True

        # Acción peligrosa: solicitar confirmación
        if mgr.is_dangerous(action):
            return mgr.request_confirmation(action, description)

        # Acción desconocida: permitir por defecto
        return True

    except Exception as e:
        logger.warning(f"[SecurityManager] Error en check_action: {e}")
        return True  # fail-silent


# ── Singleton ─────────────────────────────────────────────────────────────────

_security_manager: Optional[SecurityManager] = None
_singleton_lock = threading.Lock()


def get_security_manager() -> SecurityManager:
    """
    Retorna el singleton de SecurityManager.

    Returns:
        Instancia única de SecurityManager.
    """
    global _security_manager
    if _security_manager is None:
        with _singleton_lock:
            if _security_manager is None:
                _security_manager = SecurityManager()
    return _security_manager
