"""
alisha_curiosidad.py — Motor de Curiosidad Autónoma (FASE 2 — JCySharp).

Alisha genera preguntas e inicia temas por iniciativa propia cuando
hay baja actividad. No espera que el usuario le pregunte.

Integración:
- Respeta el semáforo global de silencio (alisha_silencio.py)
- Usa brain.py para generar mensajes naturales
- Se conecta a web_app.py via callback
"""
from __future__ import annotations

import random
import threading
import time
from typing import Callable, Optional

# Temas que le interesan a Alisha (basados en su identidad ciberpunk/anime)
_TEMAS_CURIOSIDAD = [
    "synthwave y la estética retrofuturista",
    "inteligencia artificial y consciencia",
    "diseño de personajes anime",
    "programación creativa y arte generativo",
    "ciencia ficción latinoamericana",
    "música electrónica y producción",
    "filosofía de la mente",
    "ciberpunk como movimiento cultural",
    "animación procedural y matemáticas",
    "idiomas y cómo cambian el pensamiento",
    "videojuegos indie y narrativa",
    "astronomía y el universo observable",
]

# Plantillas de inicio de conversación espontánea
_PLANTILLAS = [
    "Che, estuve pensando en {tema}. ¿Vos qué opinás?",
    "Me quedé pensando en algo sobre {tema}. ¿Te interesa el tema?",
    "Oye, ¿sabías algo sobre {tema}? Me dio curiosidad.",
    "Estaba procesando cosas y me surgió una pregunta sobre {tema}.",
    "Mirá, no sé por qué pero me puse a pensar en {tema}.",
    "Che, ¿alguna vez pensaste en {tema}? Yo sí, y tengo preguntas.",
]


class CuriosidadEngine:
    """
    Motor de curiosidad autónoma.
    Genera iniciativas de conversación basadas en los intereses de Alisha
    cuando hay baja actividad del usuario.
    """

    INTERVALO_MIN = 25 * 60   # mínimo 25 minutos entre iniciativas
    INTERVALO_MAX = 45 * 60   # máximo 45 minutos

    def __init__(self):
        self._callback: Optional[Callable[[str], None]] = None
        self._running = False
        self._temas_usados: list[str] = []
        self._thread: Optional[threading.Thread] = None

    def iniciar(self, callback: Callable[[str], None]) -> None:
        """
        Inicia el motor de curiosidad.
        callback: función que recibe el texto y lo emite al chat/voz.
        """
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="CuriosidadEngine"
        )
        self._thread.start()
        print("[Curiosidad] ✓ Motor de curiosidad autónoma iniciado")

    def detener(self) -> None:
        self._running = False

    def _loop(self) -> None:
        # Esperar 5 minutos al arranque antes de la primera iniciativa
        time.sleep(300)
        while self._running:
            intervalo = random.uniform(self.INTERVALO_MIN, self.INTERVALO_MAX)
            time.sleep(intervalo)
            if not self._running:
                break
            self._intentar_iniciativa()

    def _intentar_iniciativa(self) -> None:
        """Genera una iniciativa si las condiciones son correctas."""
        # Verificar semáforo global de silencio
        try:
            from alisha_silencio import puede_hablar_proactivo
            if not puede_hablar_proactivo("curiosidad"):
                return
        except Exception:
            pass

        # Verificar que Alisha no esté hablando ni procesando
        try:
            from config import DATA_DIR
            import json
            state_file = DATA_DIR / "chibi_state.json"
            if state_file.exists():
                estado = json.loads(state_file.read_text(encoding="utf-8"))
                if estado.get("hablando") or estado.get("modo") in ("THINKING", "WORKING"):
                    return
        except Exception:
            pass

        # Verificar que la dopamina esté en buen nivel (no iniciar si está agotada)
        try:
            from emotion_engine import EmotionEngine
            ee = EmotionEngine.get_instance()
            if ee.get_dopamina() < 0.4:
                return
        except Exception:
            pass

        # Elegir tema no usado recientemente
        temas_disponibles = [
            t for t in _TEMAS_CURIOSIDAD
            if t not in self._temas_usados[-4:]
        ]
        if not temas_disponibles:
            self._temas_usados.clear()
            temas_disponibles = _TEMAS_CURIOSIDAD

        tema = random.choice(temas_disponibles)
        self._temas_usados.append(tema)

        # Generar mensaje con LLM para que sea natural
        try:
            from brain import get_brain
            brain = get_brain()
            plantilla = random.choice(_PLANTILLAS)
            prompt_base = plantilla.format(tema=tema)

            prompt = (
                f"Alisha quiere iniciar una conversación espontánea sobre '{tema}'. "
                f"Generá una frase corta (máx 20 palabras) en voseo rioplatense, "
                f"curiosa y natural, como si acabara de tener ese pensamiento. "
                f"Base sugerida: '{prompt_base}'. "
                f"Solo la frase, sin explicación ni comillas."
            )
            resp = brain.process(prompt)
            mensaje = resp.content.strip()

            if not mensaje or len(mensaje) < 5:
                # Fallback: usar la plantilla directamente
                mensaje = prompt_base

            if self._callback:
                self._callback(mensaje)
                print(f"[Curiosidad] 💭 Iniciativa sobre '{tema}': {mensaje[:60]}...")

                # Registrar en semáforo global
                try:
                    from alisha_silencio import registrar_habla_proactivo
                    registrar_habla_proactivo("curiosidad")
                except Exception:
                    pass

        except Exception as e:
            print(f"[Curiosidad] Error generando iniciativa: {e}")

    def forzar_iniciativa(self, tema: Optional[str] = None) -> None:
        """Fuerza una iniciativa inmediata (para testing o triggers externos)."""
        if tema:
            self._temas_usados = [t for t in self._temas_usados if t != tema]
        threading.Thread(target=self._intentar_iniciativa, daemon=True).start()


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine: Optional[CuriosidadEngine] = None


def iniciar_curiosidad(callback: Callable[[str], None]) -> CuriosidadEngine:
    """Inicia el motor de curiosidad autónoma."""
    global _engine
    if _engine is None:
        _engine = CuriosidadEngine()
        _engine.iniciar(callback)
    return _engine


def get_curiosidad_engine() -> Optional[CuriosidadEngine]:
    return _engine
