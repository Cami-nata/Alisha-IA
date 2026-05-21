"""
Reflection_Timer — temporizador de reflexión y voz situacional.
Parte del sistema de Conciencia Situacional de Alisha.

Dispara cada 10 minutos, genera un State_Vector a partir del Silent_Buffer,
aplica la Semantic_Layer y llama al LLM (Ollama) con timeout de 15 segundos.
"""

import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Callable

import requests

from semantic_layer import SemanticLayer, detectar_inactividad
from state_vector import es_identico, generar_state_vector

if TYPE_CHECKING:
    from atlas_memory import AtlasMemory
    from silent_buffer import SilentBuffer

# Intervalo del temporizador en segundos (10 minutos — habla solo cuando hay algo nuevo)
_INTERVALO_SEGUNDOS = 600

# Timeout para la llamada al LLM en segundos
_LLM_TIMEOUT = 15

# Umbral de inactividad para pensamiento profundo (15 minutos)
_INACTIVIDAD_PROFUNDA_SEGUNDOS = 900

# URL del LLM (Ollama)
_LLM_URL = "http://localhost:11434/api/generate"
_LLM_MODEL = "llama3.1"


class ReflectionTimer:
    """
    Temporizador de reflexión que dispara cada 10 minutos.

    En cada ciclo:
    1. Vacía el Silent_Buffer y genera un State_Vector.
    2. Compara con el historial para detectar inactividad o ciclos idénticos.
    3. Si hay actividad nueva, construye un prompt via SemanticLayer y llama al LLM.
    4. Invoca el callback con la respuesta del LLM.
    5. Actualiza el historial y guarda en Atlas_Memory.

    El reinicio del contador se implementa con un threading.Event interno
    que interrumpe el wait() del temporizador.
    """

    def __init__(self) -> None:
        self._buffer: "SilentBuffer | None" = None
        self._atlas: "AtlasMemory | None" = None
        self._callback: Callable[[str], None] | None = None

        self._stop_event = threading.Event()
        self._reinicio_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Historial de los últimos 3 SVs para detección de inactividad (Req 5.3)
        self._historial_svs: deque = deque(maxlen=3)

        # Capa semántica con historial de apps en sesión
        self._semantic_layer = SemanticLayer()

        # SV del ciclo anterior para comparación (Req 5.2)
        self._sv_anterior: dict | None = None

        self._proactive_notifier = None

        # Tracking de última actividad real para pensamiento profundo
        self._ultima_actividad_real: float = time.monotonic()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(
        self,
        buffer: "SilentBuffer",
        atlas: "AtlasMemory",
        callback: Callable[[str], None],
    ) -> None:
        """Arranca el thread daemon del temporizador."""
        self._buffer = buffer
        self._atlas = atlas
        self._callback = callback

        self._stop_event.clear()
        self._reinicio_event.clear()

        self._thread = threading.Thread(
            target=self._loop,
            name="ReflectionTimer",
            daemon=True,
        )
        self._thread.start()

    def detener(self) -> None:
        """Detiene el thread limpiamente."""
        self._stop_event.set()
        # Despertar el wait() para que el thread termine rápido
        self._reinicio_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def reiniciar_contador(self) -> None:
        """
        Reinicia el contador del temporizador.
        Usado por PriorityInterrupt vía threading.Event (Req 6.5).
        El próximo ciclo ocurrirá 10 minutos después de este llamado.
        """
        self._reinicio_event.set()

    def conectar_proactive_notifier(self, notifier) -> None:
        self._proactive_notifier = notifier

    def suscribir_reinicio(self, reinicio_event: threading.Event) -> None:
        """
        Suscribe este timer al evento de reinicio del PriorityInterrupt.
        Lanza un thread daemon que espera el evento y llama reiniciar_contador().
        """
        def _watcher() -> None:
            while not self._stop_event.is_set():
                # Esperar a que el evento externo se active
                reinicio_event.wait(timeout=1)
                if reinicio_event.is_set():
                    reinicio_event.clear()
                    self.reiniciar_contador()

        t = threading.Thread(target=_watcher, name="ReflectionTimer-Watcher", daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Loop principal: espera el intervalo y ejecuta un ciclo."""
        while not self._stop_event.is_set():
            # Esperar el intervalo, pero interrumpible por reinicio o detención
            self._esperar_intervalo()

            if self._stop_event.is_set():
                break

            try:
                self._tick()
            except Exception:
                pass

    def _esperar_intervalo(self) -> None:
        """
        Espera _INTERVALO_SEGUNDOS, pero puede ser interrumpido por
        _reinicio_event (reinicio del contador) o _stop_event (detención).
        """
        inicio = time.monotonic()
        while not self._stop_event.is_set():
            transcurrido = time.monotonic() - inicio
            restante = _INTERVALO_SEGUNDOS - transcurrido
            if restante <= 0:
                break

            # Esperar el mínimo entre el tiempo restante y 1 segundo
            self._reinicio_event.wait(timeout=min(restante, 1.0))

            if self._reinicio_event.is_set():
                # Reiniciar el contador: resetear el tiempo de inicio
                self._reinicio_event.clear()
                inicio = time.monotonic()

    # ------------------------------------------------------------------
    # Ciclo de reflexión
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Un ciclo completo de reflexión."""
        if self._buffer is None:
            return

        if self._proactive_notifier is not None:
            try:
                emitido = self._proactive_notifier.evaluar(
                    generar_state_vector(list(self._buffer._deque) if hasattr(self._buffer, '_deque') else []),
                    self._atlas,
                    list(self._historial_svs),
                    self._callback
                )
                self._proactive_notifier.actualizar_inactividad(
                    generar_state_vector(list(self._buffer._deque) if hasattr(self._buffer, '_deque') else [])
                )
                if emitido:
                    return
            except Exception:
                pass

        # Pensamiento profundo tras 30 min de inactividad real
        try:
            inactividad = time.monotonic() - self._ultima_actividad_real
            if inactividad >= _INACTIVIDAD_PROFUNDA_SEGUNDOS:
                self._pensamiento_profundo()
                self._ultima_actividad_real = time.monotonic()
                return
        except Exception:
            pass

        # 1. Vaciar buffer y generar SV
        eventos = self._buffer.vaciar()
        sv = generar_state_vector(eventos)

        # 2. Si no hay actividad, omitir (pero el buffer ya fue vaciado — Req 5.5)
        if not sv.get("actividad_detectada", False):
            return

        # 3. Comparar con ciclo anterior (Req 5.2)
        if self._sv_anterior is not None and es_identico(sv, self._sv_anterior):
            self._historial_svs.append(sv)
            return

        # 4. Detectar inactividad en historial de 3 SVs (Req 5.4)
        historial_lista = list(self._historial_svs) + [sv]
        if detectar_inactividad(historial_lista):
            self._historial_svs.append(sv)
            return

        # 5. Construir prompt via SemanticLayer
        registro_anterior = None
        if self._atlas is not None:
            from datetime import datetime
            try:
                registro_anterior = self._atlas.buscar_franja_horaria(datetime.now())
            except Exception:
                pass

        prompt = self._semantic_layer.construir_prompt(sv, registro_anterior)

        # 6. Llamar al LLM con timeout 15s (Req 4.6)
        texto = self._llamar_llm(prompt)
        if texto is None:
            # Timeout o error: omitir ciclo silenciosamente
            self._historial_svs.append(sv)
            self._sv_anterior = sv
            return

        # 7. Invocar callback con la respuesta
        if self._callback is not None:
            try:
                self._callback(texto)
            except Exception:
                pass

        # 8. Actualizar historial y SemanticLayer
        self._historial_svs.append(sv)
        self._sv_anterior = sv
        self._semantic_layer.actualizar_historial(sv)
        self._ultima_actividad_real = time.monotonic()  # hay actividad real

        # 9. Guardar en Atlas y limpiar antiguos (Req 9.1, 9.6)
        if self._atlas is not None:
            try:
                self._atlas.guardar_ciclo(sv)
                self._atlas.limpiar_antiguos()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Llamada al LLM
    # ------------------------------------------------------------------

    def _llamar_llm(self, prompt: str) -> str | None:
        """
        Llama al LLM. Intenta Ollama primero, luego brain (Groq) como fallback.
        """
        # Intento 1: Ollama local
        try:
            response = requests.post(
                _LLM_URL,
                json={"model": _LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=_LLM_TIMEOUT,
            )
            result = response.json().get("response", "")
            if result and result.strip():
                return result
        except Exception:
            pass

        # Fallback: brain (Groq/Mistral) — siempre disponible
        try:
            from brain import get_brain
            brain = get_brain()
            resp = brain.process(prompt)
            return resp.content if resp and resp.content else None
        except Exception:
            return None

    def _pensamiento_profundo(self) -> None:
        """
        Reflexión autónoma tras 30 minutos de inactividad.
        Analiza el historial reciente y genera un consejo o conclusión.
        """
        try:
            # Leer últimas interacciones de ia_recuerdos.json
            import json
            from config import DATA_DIR
            recuerdos_recientes = []
            try:
                datos = json.loads((DATA_DIR / "ia_recuerdos.json").read_text(encoding="utf-8"))
                recuerdos_recientes = datos.get("recuerdos", [])[-5:]
            except Exception:
                pass

            resumen = ""
            if recuerdos_recientes:
                resumen = "\n".join(
                    f"- {r.get('entrada', '')} → {r.get('respuesta', '')[:80]}"
                    for r in recuerdos_recientes
                )

            prompt = (
                "Llevas un rato sin hablar con Camila. "
                "Basándote en las últimas interacciones, generá una reflexión breve, "
                "un consejo o una observación curiosa para cuando Camila vuelva. "
                "Respondé en voseo rioplatense, máximo 2 oraciones, con calidez y humor suave. "
                "No digas que estuviste esperando. Hablá como si acabaras de tener un pensamiento.\n\n"
                f"Últimas interacciones:\n{resumen or 'Sin interacciones recientes.'}"
            )

            texto = self._llamar_llm(prompt)
            if texto and self._callback:
                self._callback(texto.strip())
        except Exception:
            pass
