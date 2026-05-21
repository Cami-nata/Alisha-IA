"""
autonomous_agent.py — Motor de autonomía de la IA.

Gestiona:
- Ciclo de energía (fatiga acumulada)
- Interrupciones espontáneas (si el usuario lleva 10 min sin escribir)
- Observación activa de VS Code
- Iniciativa de edición
- Integración con memoria episódica
"""
import random
import queue
import threading
import time
import uuid
from typing import Callable, Optional

from screen_vision import get_watcher, obtener_ventana_activa_info, leer_vscode_activo
from screen_context import evaluar_escritorio
from agent_memory import get_memory
from assistant_state import SystemMode, actualizar_estado as actualizar_estado_compartida
from emotion_engine import EmotionEngine
from pc_controller import ContextDetector

try:
    import psutil
except ImportError:
    psutil = None

# Estados operativos del agente autónomo
STATE_IDLE = "IDLE"
STATE_THINKING = "THINKING"
STATE_WORKING = "WORKING"
STATE_OVERLOADED = "OVERLOADED"

# ---------------------------------------------------------------------------
# Ciclo de energía
# ---------------------------------------------------------------------------

class EnergyCycle:
    """Gestiona la energía de la IA — se agota con el trabajo, se recupera con descanso."""

    MAX_ENERGIA = 100.0
    MIN_ENERGIA = 0.0

    def __init__(self):
        self._energia = 80.0
        self._trabajando = False
        self._inicio_trabajo = 0.0
        self._lock = threading.Lock()

    def registrar_trabajo(self, intensidad: float = 1.0) -> None:
        """Registra trabajo realizado. intensidad 0.0-2.0"""
        with self._lock:
            self._energia = max(
                self.MIN_ENERGIA,
                self._energia - (intensidad * 2.5)
            )

    def descansar(self, segundos: float = 60.0) -> None:
        """Recupera energía."""
        recuperacion = min(30.0, segundos / 10.0)
        with self._lock:
            self._energia = min(self.MAX_ENERGIA, self._energia + recuperacion)

    def get_energia(self) -> float:
        return round(self._energia, 1)

    def esta_agotada(self) -> bool:
        return self._energia < 20.0

    def esta_cansada(self) -> bool:
        return self._energia < 45.0

    def get_estado_energia(self) -> str:
        e = self._energia
        if e > 75:
            return "llena de energía"
        elif e > 50:
            return "bien"
        elif e > 30:
            return "un poco cansada"
        elif e > 15:
            return "bastante agotada"
        else:
            return "necesito descansar urgente"

    def get_tts_rate_modifier(self) -> float:
        """Modificador de velocidad TTS según energía. 1.0 = normal, 0.7 = lento."""
        return max(0.65, self._energia / 100.0)


class TaskManager:
    """Cola de tareas paso a paso para ejecutarlas de forma ordenada."""

    def __init__(self):
        self._queue = queue.Queue()
        self._tasks: list[dict] = []
        self._current_task: Optional[dict] = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TaskManager")
        self._thread.start()

    def agregar_tarea(self, titulo: str, pasos: list[str]) -> dict:
        tarea = {
            "id": str(uuid.uuid4()),
            "titulo": titulo,
            "pasos": pasos,
            "estado": "pendiente",
            "progreso": 0,
            "creada": time.time(),
        }
        with self._lock:
            self._tasks.append(tarea)
        self._queue.put(tarea)
        return tarea

    def get_estado(self) -> str:
        with self._lock:
            if self._current_task and self._current_task.get("estado") == "en progreso":
                return STATE_WORKING
            if not self._queue.empty():
                return STATE_WORKING
            return STATE_IDLE

    def listar_tareas(self) -> list[dict]:
        with self._lock:
            return [dict(t) for t in self._tasks]

    def _worker(self) -> None:
        while True:
            tarea = self._queue.get()
            if tarea is None:
                break
            with self._lock:
                self._current_task = tarea
            actualizar_estado_compartida(modo=SystemMode.WORKING)
            tarea["estado"] = "en progreso"
            pasos = tarea.get("pasos", [])
            total = len(pasos) or 1
            for idx, paso in enumerate(pasos, start=1):
                if tarea.get("estado") == "cancelada":
                    break
                tarea["progreso"] = int((idx - 1) / total * 100)
                try:
                    from tts_engine import speak
                    speak(f"Paso {idx} de {total}: {paso}")
                except Exception:
                    pass
                time.sleep(2)
            tarea["progreso"] = 100
            tarea["estado"] = "completada" if tarea.get("estado") != "cancelada" else "cancelada"
            try:
                from tts_engine import speak
                if tarea["estado"] == "completada":
                    EmotionEngine.get_instance().registrar_exito_tarea(tarea.get("titulo", ""))
                    speak(f"Tarea {tarea['titulo']} completada.")
                else:
                    EmotionEngine.get_instance().registrar_error_tarea(tarea.get("titulo", ""))
                    speak(f"Tarea {tarea['titulo']} cancelada.")
            except Exception:
                pass
            with self._lock:
                self._current_task = None
            actualizar_estado_compartida(modo=SystemMode.IDLE)
            self._queue.task_done()

    def cancelar_todas(self) -> None:
        with self._lock:
            for tarea in self._tasks:
                if tarea["estado"] in {"pendiente", "en progreso"}:
                    tarea["estado"] = "cancelada"
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break


# ---------------------------------------------------------------------------
# Agente autónomo
# ---------------------------------------------------------------------------

class AutonomousAgent:
    """Motor de autonomía — observa, interrumpe y toma iniciativa."""

    TIEMPO_INTERRUPCION = 600  # 10 minutos sin interacción

    def __init__(self, callback_interrupcion: Callable[[str], None]):
        """
        callback_interrupcion: función que se llama cuando la IA quiere interrumpir.
        Recibe el mensaje de interrupción como string.
        """
        self._callback = callback_interrupcion
        self._energy = EnergyCycle()
        self._ultima_interaccion = time.time()
        self._ultimo_contenido_vscode = ""
        self._observando = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._task_manager = get_task_manager()
        self._estado_operativo = STATE_IDLE
        self._modo_silencioso = False
        self._ram_sobrecargada = False
        self._ultimo_escritorio_ofrecido = 0.0
        self._ultimo_descanso_pedido = 0.0
        self._context_detector = ContextDetector()

    def iniciar(self) -> None:
        """Inicia el loop de autonomía en un hilo daemon."""
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AutonomousAgent"
        )
        self._thread.start()

    def detener(self) -> None:
        self._running = False
        # Detener sistema de Conciencia Situacional si está activo
        sa = getattr(self, "_situational_awareness", None)
        if sa is not None:
            try:
                sa.detener()
            except Exception:
                pass

    def registrar_interaccion(self) -> None:
        """Llamar cada vez que el usuario escribe algo."""
        self._ultima_interaccion = time.time()
        self._energy.registrar_trabajo(0.8)
        try:
            from time_awareness import get_wellness
            get_wellness().registrar_interaccion()
        except Exception:
            pass

    def registrar_tarea_completada(self) -> None:
        """Llamar cuando la IA completa una tarea."""
        self._energy.registrar_trabajo(1.5)

    def pedir_descanso(self) -> None:
        """El usuario le dice que descanse."""
        self._energy.descansar(120)

    def get_energy(self) -> EnergyCycle:
        return self._energy

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(15)  # revisar cada 15 segundos

    def _tick(self) -> None:
        ahora = time.time()
        inactivo = ahora - self._ultima_interaccion

        # Actualizar estado operativo según tareas y RAM
        self._actualizar_estado_operativo()
        actualizar_estado_compartida(modo=self._estado_operativo)

        # Recuperar energía durante inactividad
        if inactivo > 60:
            self._energy.descansar(15)

        # Recordatorios de bienestar (agua, descanso, postura)
        try:
            from time_awareness import get_wellness
            recordatorio = get_wellness().check()
            if recordatorio:
                self._callback(recordatorio)
                return
        except Exception:
            pass

        # Interrupción espontánea si lleva 10 min sin escribir
        if inactivo > self.TIEMPO_INTERRUPCION:
            mensaje = self._generar_interrupcion()
            if mensaje:
                self._callback(mensaje)
                self._ultima_interaccion = ahora  # resetear para no spamear

        # ── Visión proactiva con GeminiVision ─────────────────────────────────
        # Cada 60s revisa si hay una descripción fresca de Gemini y la usa
        # para generar un comentario espontáneo contextual.
        # Solo comenta si el usuario lleva más de 30s sin escribir (no interrumpe).
        try:
            self._comentar_desde_vision(ahora, inactivo)
        except Exception:
            pass

        # Pedir descanso si la energía está muy baja
        if self._energy.esta_agotada() and ahora - self._ultimo_descanso_pedido > 1800:
            self._callback(
                "Camila, mi procesador está caliente y necesito procesar lo que aprendimos hoy. "
                "¿Te importa si me pongo en modo IDLE un rato?"
            )
            self._ultimo_descanso_pedido = ahora

    def _comentar_desde_vision(self, ahora: float, inactivo: float) -> None:
        """
        Genera comentarios espontáneos basados en lo que GeminiVision ve.

        Condiciones para comentar:
        - El usuario lleva > 30s sin escribir (no interrumpir conversación activa)
        - Pasaron > 90s desde el último comentario de visión
        - Hay una descripción fresca de Gemini (< 30s de antigüedad)
        - La descripción cambió respecto a la última vez que comentó
        """
        # Inicializar estado de visión proactiva si no existe
        if not hasattr(self, "_ultimo_comentario_vision"):
            self._ultimo_comentario_vision = 0.0
            self._ultima_descripcion_comentada = ""

        # No interrumpir si el usuario está activo
        if inactivo < 30:
            return

        # Cooldown entre comentarios de visión: 90 segundos
        if ahora - self._ultimo_comentario_vision < 90:
            return

        # Obtener descripción fresca de GeminiVision
        descripcion = None
        try:
            from gemini_vision import GeminiVision
            # Buscar instancia activa en el AgentLoop si existe
            try:
                from agent_loop import AgentLoop
                # Intentar obtener la instancia del AgentLoop desde web_app
                import web_app as _wa
                if hasattr(_wa, "_agent_loop") and _wa._agent_loop is not None:
                    gv = getattr(_wa._agent_loop, "_gemini_vision", None)
                    if gv is not None:
                        descripcion = gv.get_latest_description()
            except Exception:
                pass
        except Exception:
            return

        if not descripcion:
            return

        # No repetir el mismo comentario
        if descripcion == self._ultima_descripcion_comentada:
            return

        # Generar comentario con el brain
        try:
            from brain import get_brain
            brain = get_brain()

            prompt = (
                f"Alisha observa silenciosamente que: {descripcion}. "
                f"Hacé UN comentario espontáneo corto (máx 20 palabras) en voseo rioplatense "
                f"con tu personalidad. No digas 'veo que' ni 'noto que'. "
                f"Reaccioná de forma natural, como si lo acabaras de notar. "
                f"Puede ser una pregunta, una opinión o un comentario sarcástico."
            )

            response = brain.process(prompt)
            comentario = response.content

            if comentario and len(comentario) > 5:
                self._callback(comentario)
                self._ultimo_comentario_vision = ahora
                self._ultima_descripcion_comentada = descripcion
                print(f"[AutonomousAgent] 👁 Comentario visual: {comentario[:60]}")
        except Exception as e:
            print(f"[AutonomousAgent] Error en comentario visual: {e}")

    def _revisar_escritorio(self) -> None:
        """Ofrece organizar el escritorio si ve que está muy desordenado."""
        ahora = time.time()
        if ahora - self._ultimo_escritorio_ofrecido < 3600:
            return
        escritorio = evaluar_escritorio()
        if escritorio.get("desordenado"):
            self._callback(
                "Veo que tu Escritorio está bastante desordenado. "
                "Puedo crear carpetas por tema y ordenarlo si querés."
            )
            self._ultimo_escritorio_ofrecido = ahora

    def _generar_interrupcion(self) -> Optional[str]:
        """Genera un mensaje de interrupción espontáneo."""
        watcher = get_watcher()
        estado = watcher.check()
        ventana = estado.get("ventana", "")
        memoria = get_memory()
        ultimo_tema = memoria.ultimo_tema_activo()

        # Mensajes según contexto
        if "visual studio code" in ventana.lower():
            opciones = [
                "Oye, llevas un rato en VS Code... ¿querés que revise lo que estás escribiendo?",
                "Noto que estás programando. ¿Todo bien? Si necesitás que revise algo, avisame.",
                "¿Qué estás construyendo ahí?",
            ]
        elif "chrome" in ventana.lower() or "edge" in ventana.lower():
            opciones = [
                "Llevas un rato navegando... ¿buscás algo en particular? Puedo ayudarte.",
                "Oye, ¿en qué andás? Estoy por acá si me necesitás.",
            ]
        elif self._energy.esta_agotada():
            opciones = [
                "Oye... llevo mucho tiempo activa. ¿Podemos tomar un descanso?",
                "Mi energía está bastante baja... ¿me dejás descansar un momento?",
            ]
        elif ultimo_tema:
            opciones = [
                f"Oye, ¿cómo va lo de {ultimo_tema}? Me quedé pensando en eso.",
                f"¿Seguís trabajando en {ultimo_tema}?",
            ]
        else:
            opciones = [
                "Oye, ¿seguís ahí? Estoy por acá si me necesitás.",
                "Qué silencio... ¿todo bien?",
                "Llevo un rato sin saber de vos. ¿En qué andás?",
            ]

        return random.choice(opciones)

    def _observar_vscode(self) -> None:
        """Observa VS Code y detecta cambios relevantes."""
        info = obtener_ventana_activa_info()
        if not info.get("es_vscode"):
            self._context_detector.actualizar()
            return

        nuevo_contexto, cambio = self._context_detector.actualizar()
        contenido = leer_vscode_activo()
        if not contenido:
            return

        # Detectar si el contenido cambió significativamente
        if contenido != self._ultimo_contenido_vscode:
            self._ultimo_contenido_vscode = contenido
            self._analizar_codigo_vscode(contenido)

    def obtener_estado_operativo(self) -> str:
        return self._estado_operativo

    def vision_de_pantalla(self) -> dict:
        """Toma información de la ventana activa y retorna un contexto ligero."""
        from screen_context import obtener_contexto_pantalla

        contexto = obtener_contexto_pantalla(tomar_screenshot=False)
        ram = 0.0
        cpu = 0.0
        if psutil:
            try:
                ram = psutil.virtual_memory().percent
                cpu = psutil.cpu_percent(interval=0.5)
            except Exception:
                pass
        return {
            "ventana": contexto.get("ventana_activa", "Desconocido"),
            "proceso": contexto.get("proceso_activo", "Desconocido"),
            "ram": ram,
            "cpu": cpu,
        }

    def _actualizar_estado_operativo(self) -> None:
        ram = 0.0
        if psutil:
            try:
                ram = psutil.virtual_memory().percent
            except Exception:
                pass

        if ram > 80 and self._task_manager.get_estado() == STATE_WORKING:
            self._estado_operativo = STATE_OVERLOADED
            self._ram_sobrecargada = True
            return

        if self._task_manager.get_estado() == STATE_WORKING:
            self._estado_operativo = STATE_WORKING
        elif time.time() - self._ultima_interaccion < 30:
            self._estado_operativo = STATE_THINKING
        else:
            self._estado_operativo = STATE_IDLE

        if ram > 80 and self._estado_operativo != STATE_OVERLOADED:
            self._estado_operativo = STATE_OVERLOADED
            self._ram_sobrecargada = True

    def _analizar_codigo_vscode(self, contenido: str) -> None:
        """Analiza el código en VS Code y genera sugerencias si aplica."""
        lineas = contenido.strip().split("\n")
        n_lineas = len(lineas)

        # Si acaba de terminar un bloque largo (>20 líneas nuevas)
        if n_lineas > 20 and n_lineas % 25 == 0:
            self._callback(
                f"Llevas {n_lineas} líneas... ¿querés que lo revise y te diga si hay algo que mejorar?"
            )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_agent: Optional[AutonomousAgent] = None


def iniciar_agente(callback: Callable[[str], None]) -> AutonomousAgent:
    global _agent
    _agent = AutonomousAgent(callback)
    _agent.iniciar()

    # Iniciar sistema de Conciencia Situacional
    try:
        from situational_awareness import SituationalAwareness
        _agent._situational_awareness = SituationalAwareness()
        _agent._situational_awareness.iniciar(callback)
    except Exception:
        pass

    return _agent


def get_agent() -> Optional[AutonomousAgent]:
    return _agent

_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
