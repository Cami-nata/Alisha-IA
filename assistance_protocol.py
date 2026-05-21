"""
assistance_protocol.py — Protocolo de asistencia de 4 pasos.

Detecta palabras clave en los mensajes del usuario y ejecuta un protocolo
de 4 pasos: captura visual → generación de propuesta → presentación → creación.

Principio fail-silent: toda excepción se captura y registra; nunca se propaga.
El socketio puede ser None (modo standalone sin emitir eventos).

Requisitos: 8.x
"""
from __future__ import annotations

import re
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from gemini_vision import GeminiVision
    from memory_db import MemoryDB
    from agent_loop import StateMapper


class AssistanceProtocol:
    """
    Protocolo de asistencia operativa de 4 pasos.

    Paso 1: Captura visual con GeminiVision.
    Paso 2: Generación de propuesta con brain.py.
    Paso 3: Presentación de propuesta vía SocketIO.
    Paso 4: Creación de archivo con la propuesta.
    """

    TRIGGER_KEYWORDS = {
        "ayudame con",
        "hacé un",
        "creá un",
        "analizá",
        "buscá info sobre",
    }

    def __init__(
        self,
        gemini_vision=None,
        memory_db=None,
        state_mapper=None,
    ) -> None:
        self._gemini_vision = gemini_vision
        self._memory_db = memory_db
        self._state_mapper = state_mapper

    # ── Detección de palabras clave ────────────────────────────────────────────

    def should_trigger(self, message: str) -> bool:
        """
        Retorna True si el mensaje contiene al menos una keyword de activación.
        Comparación case-insensitive.
        """
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.TRIGGER_KEYWORDS)

    # ── Paso 1: Captura visual ─────────────────────────────────────────────────

    def _step1_capture(self) -> Optional[str]:
        """
        Captura y analiza la pantalla con GeminiVision.
        Retorna la descripción visual o None si no está disponible.
        Propaga excepciones para que _run_protocol pueda notificar el error.
        """
        if self._gemini_vision is None:
            return None
        return self._gemini_vision.capture_and_analyze()

    # ── Paso 2: Generación de propuesta ───────────────────────────────────────

    def _step2_generate(self, context: str, request: str) -> str:
        """
        Consulta brain.py con el contexto visual y la solicitud del usuario.
        Retorna la propuesta generada o un texto de fallback.
        Propaga excepciones para que _run_protocol pueda notificar el error.
        """
        prompt = (
            f"Contexto visual: {context}\n\n"
            f"Solicitud: {request}\n\n"
            "Generá una propuesta estructurada en voseo rioplatense."
        )
        try:
            from brain import get_brain  # fail-silent si no disponible
            brain = get_brain()
            response = brain.process(prompt)
            return response.content
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 2 (generación): {e}")
            # Fallback: propuesta básica
            return (
                f"Propuesta para: {request}\n\n"
                "No pude conectarme al motor de IA, pero puedo ayudarte con esta tarea. "
                "Voy a crear un archivo con los pasos básicos para completarla."
            )

    # ── Paso 3: Presentación de propuesta ─────────────────────────────────────

    def _step3_propose(
        self,
        proposal: str,
        socketio,
        context: str = "",
    ) -> None:
        """
        Emite el evento SocketIO 'propuesta_asistencia' con la propuesta.
        Si socketio es None, no emite nada.
        """
        if socketio is None:
            return
        try:
            socketio.emit("propuesta_asistencia", {
                "paso": 3,
                "propuesta": proposal,
                "contexto_visual": context,
                "acciones_previstas": ["crear_word", "escribir_texto"],
            })
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 3 (propuesta SocketIO): {e}")

    # ── Paso 4: Creación de archivo ────────────────────────────────────────────

    def _step4_create(self, proposal: str, request: str = "") -> str:
        """
        Crea un archivo .txt con la propuesta usando tomar_nota de actions.py.
        Retorna la ruta del archivo creado.
        """
        try:
            from actions import tomar_nota

            # Generar nombre descriptivo basado en la solicitud
            titulo = _generar_titulo(request or "propuesta_asistencia")
            ruta = tomar_nota(titulo=titulo, texto=proposal)
            return ruta
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 4 (creación): {e}")
            return ""

    # ── Notificación de errores ────────────────────────────────────────────────

    def _notify_error(self, step: int, error: str, socketio) -> None:
        """
        Emite un mensaje de error en voseo rioplatense vía SocketIO.
        Si socketio es None, solo registra el error.
        """
        mensajes = {
            1: (
                f"Che, no pude capturar la pantalla en el Paso 1 ({error}). "
                "Voy a continuar con la propuesta sin contexto visual, ¿dale?"
            ),
            2: (
                f"Uy, tuve un problema generando la propuesta en el Paso 2 ({error}). "
                "Voy a intentar continuar con lo que tengo."
            ),
            3: (
                f"No pude enviarte la propuesta en el Paso 3 ({error}). "
                "Igual voy a crear el archivo para que lo tengas."
            ),
            4: (
                f"Tuve un problema creando el archivo en el Paso 4 ({error}). "
                "Revisá que tengas permisos de escritura en la carpeta."
            ),
        }
        mensaje = mensajes.get(
            step,
            f"Ocurrió un error en el Paso {step}: {error}",
        )
        print(f"[AssistanceProtocol] Error Paso {step}: {error}")

        if socketio is None:
            return
        try:
            socketio.emit("error_asistencia", {
                "paso": step,
                "mensaje": mensaje,
            })
        except Exception as emit_err:
            print(f"[AssistanceProtocol] Error emitiendo notificación: {emit_err}")

    # ── Ejecución del protocolo ────────────────────────────────────────────────

    def execute(self, message: str, socketio) -> None:
        """
        Ejecuta el protocolo de 4 pasos en un hilo separado.
        Actualiza el estado a WORKING al iniciar y a IDLE al completar o fallar.
        """
        hilo = threading.Thread(
            target=self._run_protocol,
            args=(message, socketio),
            name="AssistanceProtocol",
            daemon=True,
        )
        hilo.start()

    def _run_protocol(self, message: str, socketio) -> None:
        """Lógica interna del protocolo. Corre en hilo separado."""
        # Cambiar estado a WORKING
        self._set_state("WORKING")

        context = ""
        proposal = ""
        archivo_ruta = ""

        # ── Paso 1: Captura visual ─────────────────────────────────────────────
        try:
            context = self._step1_capture() or ""
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 1 (captura): {e}")
            self._notify_error(1, str(e), socketio)
            context = ""

        # ── Paso 2: Generación de propuesta ───────────────────────────────────
        try:
            proposal = self._step2_generate(context, message)
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 2 (generación): {e}")
            self._notify_error(2, str(e), socketio)
            proposal = f"Propuesta para: {message}"

        # ── Paso 3: Presentación de propuesta ─────────────────────────────────
        try:
            self._step3_propose(proposal, socketio, context=context)
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 3 (propuesta): {e}")
            self._notify_error(3, str(e), socketio)

        # ── Paso 4: Creación de archivo ────────────────────────────────────────
        try:
            archivo_ruta = self._step4_create(proposal, request=message)
            if archivo_ruta and socketio is not None:
                try:
                    socketio.emit("propuesta_confirmada", {
                        "paso": 4,
                        "archivo_creado": archivo_ruta,
                        "mensaje": f"Listo, lo guardé en '{archivo_ruta}'.",
                    })
                except Exception as emit_err:
                    print(f"[AssistanceProtocol] Error emitiendo propuesta_confirmada: {emit_err}")
        except Exception as e:
            print(f"[AssistanceProtocol] Error en Paso 4 (creación): {e}")
            self._notify_error(4, str(e), socketio)

        # Cambiar estado a IDLE al completar
        self._set_state("IDLE")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        """Actualiza el estado operativo usando StateMapper si está disponible."""
        if self._state_mapper is None:
            return
        try:
            self._state_mapper.apply(state)
        except Exception as e:
            print(f"[AssistanceProtocol] Error actualizando estado a {state}: {e}")


# ── Helpers de módulo ──────────────────────────────────────────────────────────

def _generar_titulo(request: str) -> str:
    """
    Genera un nombre de archivo descriptivo basado en la solicitud.
    Limpia caracteres no permitidos y trunca a 50 caracteres.
    """
    # Eliminar caracteres especiales y normalizar espacios
    titulo = re.sub(r"[^\w\s\-áéíóúüñÁÉÍÓÚÜÑ]", "", request)
    titulo = re.sub(r"\s+", "_", titulo.strip())
    titulo = titulo[:50] if len(titulo) > 50 else titulo
    return titulo or "propuesta_asistencia"
