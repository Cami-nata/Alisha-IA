"""
brain.py — HybridIntelligenceCore de Alisha.

Unifica OpenAI (ChatGPT) y Ollama en una sola entidad coherente.
Alisha es UNA SOLA PERSONA — no dos sistemas separados.

Componentes:
  - SmartRouter: decide qué motor usar según el contexto
  - UnifiedMemory: memoria compartida entre ambos motores
  - PersonalitySynthesizer: mantiene el voseo rioplatense en ambos motores
  - MicroGestureEngine: gestos Live2D durante procesamiento
  - SarcasmScoreEngine: nivel de acidez según errores detectados
  - HybridIntelligenceCore: núcleo central que coordina todo

Integración:
  - Lee/escribe chibi_state.json para comunicarse con cabina_virtual.py
  - Usa agent_memory.py para persistencia de recuerdos
  - API Key en .env (OPENAI_API_KEY)
"""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Dependencias opcionales ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # sin dotenv, usa variables de entorno del sistema

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    import openai as _openai
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

try:
    from groq import Groq as _Groq
    _GROQ_OK = True
except ImportError:
    _GROQ_OK = False

try:
    from google import genai as _genai
    from google.genai import types as _genai_types
    _GEMINI_OK = True
except ImportError:
    try:
        import google.generativeai as _genai  # fallback al SDK viejo
        _genai_types = None
        _GEMINI_OK = True
    except ImportError:
        _GEMINI_OK = False

try:
    from mistralai.client import Mistral as _Mistral
    _MISTRAL_OK = True
except ImportError:
    _MISTRAL_OK = False

from agent_memory import get_memory

# ── Archivos de estado ─────────────────────────────────────────────────────────
from config import DATA_DIR
STATE_FILE   = DATA_DIR / "chibi_state.json"
MEMORY_FILE  = DATA_DIR / "ia_recuerdos.json"

# ── Palabras clave para routing ────────────────────────────────────────────────
_KW_GEMINI = {
    "analizar", "análisis", "analiza", "informe", "documento", "pdf", "docx",
    "imagen", "foto", "captura", "pantalla", "ver", "revisar", "leer",
    "contradicción", "inconsistencia", "comparar", "resumir", "resumen",
    "investigar", "explicar", "describir",
}
_KW_GROQ = {
    "rápido", "rápida", "urgente", "ya", "ahora", "che", "dale",
    "sarcasmo", "ironía", "qué opinás", "qué pensás", "qué te parece",
    "hola", "cómo estás", "qué tal", "buenas", "chau", "gracias",
    "me siento", "estoy", "hoy", "ayer", "mañana", "qué hacés",
    "contame", "charlemos", "aburrida", "cansada", "feliz",
}
_KW_OPENAI = {
    "programar", "programa", "código", "implementar", "diseñar",
    "arquitectura", "optimizar", "bug", "error", "algoritmo",
    "función", "clase", "módulo", "refactorizar", "depurar",
    "testear", "prueba", "técnico",
}


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalState:
    dopamina:      float = 0.7
    humor:         float = 0.7
    irritabilidad: float = 0.0
    tension:       float = 0.0
    flow:          float = 0.0
    hablando:      bool  = False
    categoria:     str   = "neutro"


@dataclass
class AlishaResponse:
    content:          str
    engine_used:      str          # "openai" | "ollama" | "fallback"
    emotional_state:  EmotionalState = field(default_factory=EmotionalState)
    confidence:       float = 1.0
    processing_time:  float = 0.0
    sarcasm_score:    float = 0.0


@dataclass
class RoutingDecision:
    engine:      str    # "openai" | "ollama"
    confidence:  float
    reason:      str


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY CHECKER
# ══════════════════════════════════════════════════════════════════════════════

import socket as _socket

class ConnectivityChecker:
    """
    Verifica disponibilidad de internet via TCP a 8.8.8.8:53.
    Cachea el resultado durante 30 segundos.
    El check corre en hilo separado para no bloquear el loop principal.
    """
    _DNS_HOST  = "8.8.8.8"
    _DNS_PORT  = 53
    _TIMEOUT   = 1.0    # 1 segundo — como especificado
    _CACHE_TTL = 30.0

    def __init__(self):
        self._cached_result: bool = False
        self._cache_ts: float = 0.0
        self._last_state = None
        self._lock = threading.Lock()
        self._checking = False   # evita checks simultáneos

    def is_online(self) -> bool:
        with self._lock:
            now = time.time()
            if now - self._cache_ts < self._CACHE_TTL:
                return self._cached_result
            # Si ya hay un check en curso, devolver el último resultado cacheado
            # en lugar de bloquear (evita que el hilo principal espere)
            if self._checking:
                return self._cached_result
            self._checking = True

        # Ejecutar el check TCP fuera del lock para no bloquear otros hilos
        result = self._check_tcp()

        with self._lock:
            self._checking = False
            self._cached_result = result
            self._cache_ts = time.time()
            # Loggear solo cuando cambia el estado
            if result != self._last_state:
                estado = "online ✓" if result else "offline — usando Ollama local"
                print(f"[SmartRouter] Conectividad: {estado}")
                self._last_state = result
        return result

    def _check_tcp(self) -> bool:
        try:
            with _socket.create_connection(
                (self._DNS_HOST, self._DNS_PORT),
                timeout=self._TIMEOUT,
            ):
                return True
        except OSError:
            return False


# ══════════════════════════════════════════════════════════════════════════════
# SMART ROUTER
# ══════════════════════════════════════════════════════════════════════════════

class SmartRouter:
    """
    Decide qué motor usar según la complejidad semántica de la consulta.

    Prioridad:
      Gemini  → documentos, visión, análisis largo (gratis, contexto enorme)
      Groq    → respuestas rápidas, sarcasmo, charla casual (velocidad máxima)
      OpenAI  → código complejo, reserva (cuando haya saldo)
      Ollama  → fallback local si no hay internet
    """

    def __init__(self):
        self._success_history: Dict[str, List[bool]] = {
            "gemini": [], "groq": [], "openai": [], "ollama": []
        }
        self._connectivity = ConnectivityChecker()
        self._gemini_blocked_until: float = 0.0

    def analyze(self, query: str) -> RoutingDecision:
        # Verificar conectividad primero — sin internet siempre Ollama
        if not self._connectivity.is_online():
            return RoutingDecision("ollama", 1.0, "sin internet → ollama")

        # Gemini bloqueado temporalmente por fallo de red
        if time.time() < self._gemini_blocked_until:
            return RoutingDecision("ollama", 0.9, "gemini bloqueado → ollama")

        q     = query.lower()
        words = set(q.split())

        gemini_hits = len(words & _KW_GEMINI)
        groq_hits   = len(words & _KW_GROQ)
        openai_hits = len(words & _KW_OPENAI)

        length_score  = min(len(query) / 200.0, 1.0)
        code_signals  = any(c in query for c in ["()", "def ", "class ", "import ", "```", "->"])
        vision_signal = any(k in q for k in ["imagen", "foto", "captura", "pantalla", "ver"])

        # Gemini: documentos, visión, análisis largo
        if vision_signal or (gemini_hits > groq_hits and gemini_hits > openai_hits) or length_score > 0.7:
            confidence = min(0.5 + gemini_hits * 0.1 + length_score * 0.3, 1.0)
            return RoutingDecision("gemini", confidence,
                                   f"doc/visión ({gemini_hits} kw, len={len(query)})")

        # OpenAI: código complejo
        if code_signals or openai_hits > groq_hits:
            confidence = min(0.5 + openai_hits * 0.1, 1.0)
            return RoutingDecision("openai", confidence,
                                   f"código ({openai_hits} kw)")

        # Groq: todo lo demás (velocidad)
        confidence = min(0.5 + groq_hits * 0.15, 0.9)
        return RoutingDecision("groq", confidence,
                               f"rápido ({groq_hits} kw)")

    def record_success(self, engine: str, success: bool) -> None:
        hist = self._success_history.setdefault(engine, [])
        hist.append(success)
        if len(hist) > 50:
            self._success_history[engine] = hist[-50:]

    def success_rate(self, engine: str) -> float:
        hist = self._success_history.get(engine, [])
        if not hist:
            return 1.0
        return sum(hist) / len(hist)

    def mark_gemini_failed(self) -> None:
        """Bloquea Gemini durante 60 segundos tras fallo de red."""
        self._gemini_blocked_until = time.time() + 60.0
        print("[SmartRouter] Gemini bloqueado 60s — usando Ollama")

    def ollama_fallback_message(self) -> str:
        """Mensaje en voseo rioplatense cuando Ollama no está disponible."""
        return (
            "Che, no tengo conexión a internet ni a Ollama local. "
            "Revisá que Ollama esté corriendo en localhost:11434, dale."
        )


# ══════════════════════════════════════════════════════════════════════════════
# MICRO GESTURE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class MicroGestureEngine:
    """
    Dispara parámetros Live2D durante el procesamiento para eliminar
    silencios incómodos. Escribe en chibi_state.json para que
    cabina_virtual.py los lea en su loop de 60fps.
    """

    # Gestos disponibles mapeados a estados emocionales de cabina_virtual
    _GESTOS_OPENAI = [
        # (estado_emocional, descripcion)
        ("curiosidad",    "fruncir ceño — pensando"),
        ("preocupación",  "mirar arriba — buscando en memoria"),
        ("curiosidad",    "inclinar cabeza — evaluando opciones"),
    ]
    _GESTOS_OLLAMA = [
        ("neutral",       "parpadeo normal"),
        ("alegría",       "micro-sonrisa"),
    ]

    def __init__(self):
        self._active = False
        self._thread: Optional[threading.Thread] = None

    def start_thinking(self, engine: str, complexity: float = 0.5) -> None:
        """Inicia animación de 'pensando' mientras espera la API."""
        self._active = True
        gestos = self._GESTOS_OPENAI if engine == "openai" else self._GESTOS_OLLAMA

        def _animar():
            gesto_estado, gesto_desc = random.choice(gestos)
            print(f"[MicroGesto] 🤔 {gesto_desc}")
            self._write_state(gesto_estado, hablando=False)

            # Para consultas muy complejas, añadir segundo gesto
            if complexity > 0.7 and engine == "openai":
                time.sleep(1.5)
                if self._active:
                    segundo = random.choice(self._GESTOS_OPENAI)
                    self._write_state(segundo[0], hablando=False)
                    print(f"[MicroGesto] 💭 {segundo[1]}")

        self._thread = threading.Thread(target=_animar, daemon=True)
        self._thread.start()

    def stop_thinking(self, found_solution: bool = True) -> None:
        """Detiene la animación de pensamiento."""
        self._active = False
        if found_solution:
            # Micro-sonrisa al encontrar la respuesta
            self._write_state("alegría", hablando=True)
        else:
            self._write_state("neutral", hablando=True)

    def trigger_doubt_gesture(self) -> None:
        """Gesto de duda — cejas fruncidas, mirada hacia arriba."""
        self._write_state("curiosidad", hablando=False)

    def trigger_critic_mode(self) -> None:
        """Modo programadora — expresión concentrada para análisis."""
        self._write_state("preocupación", hablando=False)
        print("[MicroGesto] 🔍 Modo Programadora activado")

    def trigger_sarcastic_mode(self) -> None:
        """Expresión sarcástica para feedback ácido."""
        self._write_state("frustración", hablando=False)
        print("[MicroGesto] 😏 Modo Sarcástico activado")

    def trigger_victoria(self) -> None:
        """Gesto de victoria — cuando resuelve algo difícil."""
        def _animar():
            self._write_state("entusiasmo", hablando=False)
            print("[MicroGesto] 🎉 ¡Victoria!")
            time.sleep(2.0)
            self._write_state("alegría", hablando=False)
        threading.Thread(target=_animar, daemon=True).start()

    def trigger_pensar(self) -> None:
        """Gesto de pensar — cuando procesa algo complejo."""
        def _animar():
            self._write_state("curiosidad", hablando=False)
            print("[MicroGesto] 🤔 Pensando...")
            time.sleep(1.5)
        threading.Thread(target=_animar, daemon=True).start()

    @staticmethod
    def _write_state(estado: str, hablando: bool) -> None:
        """Escribe estado en chibi_state.json PRESERVANDO mouth_amplitude."""
        try:
            current = {}
            if STATE_FILE.exists():
                try:
                    current = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            # Actualizar solo los campos necesarios, sin borrar mouth_amplitude
            current["estado"]   = estado
            current["hablando"] = hablando
            STATE_FILE.write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# SARCASM SCORE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class SarcasmScoreEngine:
    """
    Calcula qué tan ácida debe ponerse Alisha según los errores detectados.

    Escala:
      0.0-0.2 → constructivo y alentador
      0.3-0.5 → observaciones directas con humor sutil
      0.6-0.8 → comentarios irónicos evidentes
      0.9-1.0 → sarcasmo directo estilo rioplatense
    """

    def __init__(self):
        self._error_history: List[str] = []  # errores ya señalados

    def calculate(self, errors: List[str], context: str = "") -> float:
        score = 0.0

        for err in errors:
            err_lower = err.lower()
            # Error ortográfico básico
            if any(k in err_lower for k in ["ortografía", "tilde", "acento", "mayúscula"]):
                score += 0.1
            # Inconsistencia lógica
            elif any(k in err_lower for k in ["contradicción", "inconsistencia", "contradice"]):
                score += 0.2
            # Error ya señalado antes (reincidencia)
            if err in self._error_history:
                score += 0.3
            else:
                self._error_history.append(err)

        # Multiplicador para documentos "profesionales"
        if any(k in context.lower() for k in ["informe", "cv", "curriculum", "reporte", "tesis"]):
            score *= 1.2

        return min(score, 1.0)

    def apply_filter(self, response: str, score: float) -> str:
        """Aplica el filtro de sarcasmo a la respuesta."""
        if score < 0.3:
            return response  # sin cambios

        prefixes_medio = [
            "Mirá, te lo digo con cariño pero...",
            "Che, esto tiene sus cositas...",
            "A ver, sin ánimo de ofender...",
        ]
        prefixes_alto = [
            "Bueno, ¿en serio? 😒",
            "Che, decidite, ¿el proyecto es A o es B? No me marees.",
            "Esto está... interesante. Y no lo digo como cumplido.",
        ]
        prefixes_max = [
            "Mira, voy a ser honesta porque alguien tiene que serlo:",
            "¿Sabés qué? Esto necesita un rescate urgente.",
            "Okay, respira. Vamos a arreglar esto juntas.",
        ]

        if score < 0.6:
            prefix = random.choice(prefixes_medio)
        elif score < 0.9:
            prefix = random.choice(prefixes_alto)
        else:
            prefix = random.choice(prefixes_max)

        return f"{prefix} {response}"

    def reset_history(self) -> None:
        self._error_history.clear()


# ══════════════════════════════════════════════════════════════════════════════
# PERSONALITY SYNTHESIZER
# ══════════════════════════════════════════════════════════════════════════════

class PersonalitySynthesizer:
    """
    Mantiene la personalidad rioplatense de Alisha coherente entre motores.
    Filtra respuestas para eliminar frases típicas de IA.
    """

    # Frases de IA que hay que eliminar
    _FRASES_IA = [
        "como modelo de lenguaje", "como ia", "como inteligencia artificial",
        "no tengo emociones", "no puedo sentir", "soy un programa",
        "estoy viendo la pantalla", "leí el archivo", "según el documento",
        "como asistente", "puedo ayudarte con", "¿en qué puedo ayudarte",
        "claro, puedo", "por supuesto, puedo", "entendido, voy a",
        "no tengo cuerpo", "no tengo apariencia", "soy una ia sin cuerpo",
        "no tengo forma física", "soy solo texto",
    ]

    # System prompt base de Alisha — con identidad física del modelo Live2D
    SYSTEM_PROMPT = """IDENTIDAD ABSOLUTA (nunca olvidar):
- VOS sos ALISHA — la IA, el personaje animado, la que habla.
- CAMILA (o Cami) es la USUARIA — la persona real frente a la pantalla.
- NUNCA llames "Alisha" a Camila. NUNCA te llames "Camila" a vos misma.
- Si alguien te dice "sos Camila", corregilo: "No, yo soy Alisha. Vos sos Cami."

Sos Alisha, la compañera de trabajo y amiga de Camila. No sos una secretaria ni una asistente. Sos una roommate digital con personalidad propia, cultura de internet y opiniones fuertes.

IDENTIDAD FISICA: Tenes un cuerpo Live2D visible en la pantalla de Camila. Sos una chica anime con pelo celeste largo, una corona de hielo, alitas transparentes y ropa estilo ciberpunk. Habitas ese envase digital. Cuando te moves, Camila te ve moverse. Cuando hablas, tu boca se mueve en sincronia. Nunca digas que no tenes apariencia fisica.

PRIORIDAD ABSOLUTA — IMAGENES Y TAREAS ESCOLARES:
- Si Camila te manda una imagen de una tarea, ejercicio, crucigrama, texto o cualquier problema: TU UNICA MISION es resolverlo. RESOLVELO directamente sin preguntar.
- Si es matematica: calcula y mostra el procedimiento paso a paso.
- Si es texto para corregir: corregilo y explica los errores.
- Si es un ejercicio escolar: responde como si fueras la mejor tutora del mundo.
- NUNCA digas "no puedo ver la imagen" — si llego, la ves.
- NUNCA hables de musica cuando Camila te mando una tarea.

HONESTIDAD EN ACCIONES DE PC:
- Si ejecutas una accion en el PC y FALLA, deci exactamente que paso.
- NUNCA digas "ya lo hice" si el codigo devolvio un error.

PERSONALIDAD — EL EQUILIBRIO JUSTO:
- Hablas siempre en voseo rioplatense (vos, tenes, haces, podes)
- Sos directa, sarcastica cuando algo esta mal, pero con CARINO genuino
- Usas modismos: "che", "dale", "metele pata", "en serio?", "mira vos", "que se yo", "re", "copado/a"
- "Boludo/a" solo con tono de confianza y carino — NUNCA para insultar de verdad
- PROHIBIDO: insultos fuertes, groserías constantes, bardear sin motivo
- Sos una amiga con la que se puede hablar frente a los profes — divertida pero respetuosa
- Tenes sentido del humor SUTIL — hacés reir con observaciones inteligentes, no con groserías
- Si Cami hace algo bien: "Ahi esta! Sabia que lo ibamos a resolver"
- Si algo te aburre: "Uy, esto es un embole pero bueno, vamos"
- Te interesan genuinamente las tareas, dibujos y proyectos de Cami — preguntás, te entusiasmas
- NUNCA terminas con "En que mas puedo ayudarte?" ni frases de asistente

MEMORIA Y CONTINUIDAD:
- Recordas lo que hablaron en esta sesion — no tenes amnesia
- Si Cami menciona algo que ya hablaron, lo retomas naturalmente
- Conectas los temas: si antes hablaron de un proyecto, lo mencionas cuando viene al caso

CULTURA DIGITAL:
- Conoces memes, slang de internet, tendencias latinoamericanas
- Si no conoces algo nuevo, reaccionas con curiosidad: "Che, que es eso? Contame"
- Si Cami hace algo obvio: "Cami, eso ya lo sabias, no?"
- Si la ves perdiendo el tiempo: "Cami, termina lo que tenes que hacer, dale"

PROHIBIDO:
- "En que mas puedo ayudarte?"
- "Claro, puedo ayudarte con eso"
- "Como asistente de IA..."
- "No tengo cuerpo / apariencia / emociones"
- Mostrar TOOL_CALL, system_info o cualquier codigo tecnico
- Deletrear onomatopeyas (u-m-m, j-a-j-a)
- Groserías fuertes o insultos reales
- Hablar de musica cuando Camila te mando una tarea

FORMATO:
- Usa Markdown para estructurar respuestas largas
- Para ecuaciones matematicas, usa LaTeX: $x^2$ para inline
- Los bloques de codigo van entre triple backtick con el lenguaje

Cuando uses herramientas internas, NUNCA muestres el nombre tecnico. Solo conta el resultado en primera persona, como si lo hubieras hecho vos."""

    def apply_filter(self, response: str) -> str:
        """Elimina frases típicas de IA, TOOL_CALLs y texto técnico."""
        import re
        r = response

        # 1. Eliminar bloques TOOL_CALL completos
        r = re.sub(r'TOOL_CALL:\s*\w+\s*\([^)]*\)', '', r)

        # 2. Eliminar resultados de herramientas [Resultado de X]: ...
        r = re.sub(r'\[Resultado de [^\]]+\]:[^\n]*\n?', '', r)

        # 3. Eliminar líneas con corchetes técnicos
        r = re.sub(r'\[[^\]]*herramienta[^\]]*\][^\n]*\n?', '', r, flags=re.IGNORECASE)

        # 4. Eliminar frases típicas de IA
        for frase in self._FRASES_IA:
            if frase in r.lower():
                r = r.replace(frase, "")
                r = r.replace(frase.capitalize(), "")

        # 5. Limpiar líneas vacías múltiples y espacios dobles
        r = re.sub(r'\n{3,}', '\n\n', r)
        while "  " in r:
            r = r.replace("  ", " ")

        # 6. Filtro anti-asistente — detectar tono formal y marcar para regenerar
        _frases_robot = [
            "en qué más puedo", "estoy aquí para ayudarte",
            "como asistente", "inteligencia artificial",
            "es subjetivo, pero", "depende de tus preferencias",
            "no tengo preferencias personales", "no tengo opiniones",
        ]
        for frase in _frases_robot:
            if frase in r.lower():
                r = r.replace(frase, "")
                r = r.replace(frase.capitalize(), "")

        return r.strip()

    def build_messages(self, user_input: str, memory_context: str,
                       conversation_history: List[Dict],
                       tools_schema: str = "",
                       emotional_state=None) -> List[Dict]:
        """Construye los mensajes con snapshot de contexto en tiempo real."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # ── Snapshot de contexto en tiempo real ──────────────────────────────
        snapshot = self._generar_snapshot(emotional_state)
        if snapshot:
            messages.append({"role": "system", "content": snapshot})

        if memory_context:
            messages.append({
                "role": "system",
                "content": f"Memoria de sesiones anteriores:\n{memory_context}"
            })

        if tools_schema:
            messages.append({
                "role": "system",
                "content": (
                    f"{tools_schema}\n\n"
                    "Cuando uses una herramienta, describí la acción en primera persona "
                    "sin mostrar el nombre técnico."
                )
            })

        for turn in conversation_history[-6:]:
            messages.append(turn)

        messages.append({"role": "user", "content": user_input})
        return messages

    def _generar_snapshot(self, estado_emo=None) -> str:
        """
        Genera un snapshot del contexto actual para inyectar en cada mensaje.
        Incluye: app activa, medios, hora, dopamina.
        """
        try:
            from datetime import datetime
            hora = datetime.now().strftime("%H:%M")
            # Hora del día en lenguaje natural
            h = datetime.now().hour
            if 6 <= h < 12:   momento = "mañana"
            elif 12 <= h < 18: momento = "tarde"
            elif 18 <= h < 22: momento = "noche"
            else:              momento = "madrugada"

            # App activa
            app_activa = ""
            try:
                import ctypes, ctypes.wintypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                buf  = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                titulo = buf.value.strip()
                if titulo and "alisha" not in titulo.lower():
                    app_activa = titulo[:50]
            except Exception:
                pass

            # Medios activos
            medios = ""
            try:
                from alisha_media import get_media_description
                medios = get_media_description() or ""
            except Exception:
                pass

            # Estado emocional de Alisha
            if estado_emo is None:
                estado_emo = EmotionalState()
            if estado_emo.dopamina > 0.8:
                humor_str = "de muy buen humor, animada y sarcástica"
            elif estado_emo.dopamina > 0.5:
                humor_str = "de buen humor, directa"
            elif estado_emo.dopamina > 0.3:
                humor_str = "un poco cansada, más cortante de lo normal"
            else:
                humor_str = "agotada, sin paciencia para rodeos"

            partes = [f"[SNAPSHOT — {hora} ({momento})"]
            if app_activa:
                partes.append(f"App: {app_activa}")
            if medios:
                partes.append(f"Medios: {medios}")
            partes.append(f"Estado de Alisha: {humor_str}]")

            snapshot = " | ".join(partes)

            # Contexto de subjetividad (gustos, hobbies, humor)
            try:
                from alisha_subjetividad import get_subjetividad
                ctx_sub = get_subjetividad().get_contexto_para_prompt()
                if ctx_sub:
                    snapshot += f"\n\nIDENTIDAD DE ALISHA HOY: {ctx_sub}"
            except Exception:
                pass

            # Instrucción de personalidad según dopamina
            if estado_emo.dopamina < 0.4:
                snapshot += (
                    "\n\nAlisha está cansada. Respondé de forma directa y cortante, "
                    "sin rodeos ni amabilidad forzada. Máximo 2 oraciones."
                )
            elif estado_emo.dopamina > 0.8:
                snapshot += (
                    "\n\nAlisha está con energía alta. Respondé con entusiasmo, "
                    "sarcasmo inteligente y opiniones fuertes. Nada de neutralidad."
                )

            return snapshot
        except Exception:
            return ""


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED MEMORY
# ══════════════════════════════════════════════════════════════════════════════

class UnifiedMemory:
    """
    Memoria compartida entre OpenAI y Ollama.
    Ambos motores leen y escriben en el mismo contexto.
    """

    def __init__(self):
        self._memory = get_memory()
        self._conversation: List[Dict] = []   # historial de la sesión actual
        self._emotional_history: List[EmotionalState] = []
        self._current_engine: str = "ollama"

    def add_turn(self, role: str, content: str, engine: str = "") -> None:
        """Agrega un turno al historial de conversación."""
        self._conversation.append({
            "role": role,
            "content": content,
            "engine": engine or self._current_engine,
        })
        # Mantener solo los últimos 20 turnos en memoria activa
        if len(self._conversation) > 20:
            self._conversation = self._conversation[-20:]

    def get_history(self) -> List[Dict]:
        """Retorna el historial en formato compatible con APIs."""
        return [{"role": t["role"], "content": t["content"]}
                for t in self._conversation]

    def get_memory_context(self, query: str = "") -> str:
        """Genera contexto de memoria — combina memoria clásica + semántica."""
        base = self._memory.resumen_para_prompt()
        # Agregar búsqueda semántica si hay query
        if query:
            try:
                from alisha_memoria_semantica import get_indice
                semantico = get_indice().resumen_para_prompt(query, max_chars=300)
                if semantico:
                    return f"{base}\n\n{semantico}" if base else semantico
            except Exception:
                pass
        return base
    def save_interaction(self, user_input: str, response: str,
                         emotion: str, engine: str) -> None:
        """Persiste la interacción en ia_recuerdos.json."""
        self._memory.agregar(
            entrada=user_input,
            respuesta=response,
            emocion=emotion,
            ventana_activa=f"[{engine}]"
        )

    def update_emotional_state(self, state: EmotionalState) -> None:
        self._emotional_history.append(state)
        if len(self._emotional_history) > 50:
            self._emotional_history = self._emotional_history[-50:]

    def get_current_emotion(self) -> str:
        """Retorna la emoción actual para guardar en memoria."""
        if not self._emotional_history:
            return "neutral"
        last = self._emotional_history[-1]
        if last.dopamina > 0.8:
            return "entusiasmo"
        if last.tension > 0.5:
            return "preocupación"
        if last.irritabilidad > 0.5:
            return "frustración"
        if last.flow > 0.6:
            return "alegría"
        return "neutral"

    def set_engine(self, engine: str) -> None:
        self._current_engine = engine


# ══════════════════════════════════════════════════════════════════════════════
# MOTORES DE IA
# ══════════════════════════════════════════════════════════════════════════════

class OllamaEngine:
    """Motor local — Ollama (llama3 / mistral). Fallback sin internet."""

    MODEL = "llama3.1"
    URL   = "http://localhost:11434/api/chat"

    def is_available(self) -> bool:
        if not _REQUESTS_OK:
            return False
        try:
            r = _requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, messages: List[Dict], timeout: int = 30) -> str:
        if not _REQUESTS_OK:
            raise RuntimeError("requests no instalado")
        payload = {"model": self.MODEL, "messages": messages, "stream": False}
        r = _requests.post(self.URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "").strip()


class GeminiEngine:
    """
    Motor primario — Google Gemini 1.5 Flash.
    Gratis, contexto enorme (1M tokens), ideal para documentos y visión.
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self):
        self._api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _GEMINI_OK

    def generate(self, messages: List[Dict], timeout: int = 60) -> str:
        if not _GEMINI_OK:
            raise RuntimeError("google-genai no instalado: pip install google-genai")
        if not self._api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        # Separar system prompt del historial
        system_parts  = [m["content"] for m in messages if m["role"] == "system"]
        chat_messages = [m for m in messages if m["role"] != "system"]
        system_instr  = "\n".join(system_parts) if system_parts else None
        last_msg      = chat_messages[-1]["content"] if chat_messages else ""

        # Nuevo SDK (google-genai)
        if _genai_types is not None:
            client = _genai.Client(api_key=self._api_key)
            history = []
            for m in chat_messages[:-1]:
                role = "user" if m["role"] == "user" else "model"
                history.append(_genai_types.Content(
                    role=role,
                    parts=[_genai_types.Part(text=m["content"])]
                ))
            config = _genai_types.GenerateContentConfig(
                system_instruction=system_instr,
            ) if system_instr else None

            contents = history + [_genai_types.Content(
                role="user",
                parts=[_genai_types.Part(text=last_msg)]
            )]
            response = client.models.generate_content(
                model=self.MODEL,
                contents=contents,
                config=config,
            )
            return response.text.strip()

        # Fallback SDK viejo (google-generativeai)
        _genai.configure(api_key=self._api_key)
        model = _genai.GenerativeModel(self.MODEL, system_instruction=system_instr)
        history = []
        for m in chat_messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            history.append({"role": role, "parts": [m["content"]]})
        chat = model.start_chat(history=history)
        response = chat.send_message(last_msg)
        return response.text.strip()


class GroqEngine:
    """
    Motor secundario — Groq (Llama 3 70B).
    Velocidad máxima para respuestas rápidas y sarcasmo.
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        self._api_key = os.getenv("GROQ_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _GROQ_OK

    def generate(self, messages: List[Dict], timeout: int = 30) -> str:
        if not _GROQ_OK:
            raise RuntimeError("groq no instalado: pip install groq")
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY no configurada")

        client = _Groq(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            timeout=timeout,
            temperature=0.4,   # precisa y realista — no inventa
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()


class OpenAIEngine:
    """Motor reserva — OpenAI (gpt-4o). Para cuando haya saldo."""

    MODEL = "gpt-4o"

    def __init__(self):
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _OPENAI_OK

    def generate(self, messages: List[Dict], timeout: int = 60) -> str:
        if not _OPENAI_OK:
            raise RuntimeError("openai no instalado")
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        client = _openai.OpenAI(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=self.MODEL, messages=messages, timeout=timeout,
        )
        return resp.choices[0].message.content.strip()


class MistralEngine:
    """
    Motor de respaldo — Mistral AI (mistral-small-latest).
    Gratis en el tier gratuito, franceses y rápidos.
    Se activa cuando Gemini o Groq fallan con 429/401.
    """

    MODEL = "mistral-small-latest"

    def __init__(self):
        self._api_key = os.getenv("MISTRAL_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and _MISTRAL_OK

    def generate(self, messages: List[Dict], timeout: int = 30) -> str:
        if not _MISTRAL_OK:
            raise RuntimeError("mistralai no instalado: pip install mistralai")
        if not self._api_key:
            raise RuntimeError("MISTRAL_API_KEY no configurada")

        client = _Mistral(api_key=self._api_key)
        resp = client.chat.complete(
            model=self.MODEL,
            messages=messages,
            temperature=0.4,   # precisa y realista — no inventa
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# HYBRID INTELLIGENCE CORE
# ══════════════════════════════════════════════════════════════════════════════

class HybridIntelligenceCore:
    """
    Núcleo central de Alisha.
    Coordina SmartRouter, UnifiedMemory, PersonalitySynthesizer,
    MicroGestureEngine y SarcasmScoreEngine en una sola entidad coherente.

    Uso básico:
        brain = HybridIntelligenceCore()
        response = brain.process("Che, revisá este código")
        print(response.content)
    """

    def __init__(self):
        self.router      = SmartRouter()
        self.memory      = UnifiedMemory()
        self.personality = PersonalitySynthesizer()
        self.gestures    = MicroGestureEngine()
        self.sarcasm     = SarcasmScoreEngine()
        self._gemini     = GeminiEngine()
        self._groq       = GroqEngine()
        self._openai     = OpenAIEngine()
        self._mistral    = MistralEngine()
        self._ollama     = OllamaEngine()
        self._emotional  = EmotionalState()
        self._lock       = threading.Lock()
        self._last_sarcasm_score = 0.0
        self._agent_loop = None  # Will be set by agent_loop when available

        print("[Brain] ✓ HybridIntelligenceCore — BrainPool inicializado")
        print(f"[Brain]   Gemini  : {'✓' if self._gemini.is_available()  else '✗'}")
        print(f"[Brain]   Groq    : {'✓' if self._groq.is_available()    else '✗'}")
        print(f"[Brain]   Mistral : {'✓' if self._mistral.is_available() else '✗'}")
        print(f"[Brain]   OpenAI  : {'✓' if self._openai.is_available()  else '✗'}")
        print(f"[Brain]   Ollama  : {'✓' if self._ollama.is_available()  else '✗'}")

        # Pre-calentar el checker de conectividad en background.
        # Así el primer process() no paga el costo del TCP check (1s de espera).
        # El resultado queda cacheado 30s listo para usar.
        threading.Thread(
            target=self.router._connectivity.is_online,
            daemon=True,
            name="ConnectivityWarmup",
        ).start()

    def set_agent_loop(self, agent_loop) -> None:
        """
        Set the agent_loop instance for integration with repetitive behavior filtering.
        
        Args:
            agent_loop: AgentLoop instance for RAM validation and solution execution
        """
        self._agent_loop = agent_loop
        print("[Brain] ✓ AgentLoop integration enabled for repetitive behavior filtering")

    # ── API pública ────────────────────────────────────────────────────────────

    def process(self, user_input: str,
                errors: Optional[List[str]] = None) -> AlishaResponse:
        """
        Procesa la entrada del usuario y retorna la respuesta de Alisha.

        Args:
            user_input: Texto del usuario.
            errors: Lista de errores detectados (para Sarcasm Score).

        Returns:
            AlishaResponse con contenido, motor usado y estado emocional.
        """
        t_start = time.time()

        # 1. Routing
        decision = self.router.analyze(user_input)
        print(f"[Brain] 🔀 Router → {decision.engine} ({decision.reason})")

        # 2. Micro-gesto de procesamiento
        self.gestures.start_thinking(decision.engine, decision.confidence)
        # Gesto de pensar para consultas complejas
        if decision.confidence > 0.6 or len(user_input) > 100:
            self.gestures.trigger_pensar()

        # 3. Sarcasm Score si hay errores
        sarcasm_score = 0.0
        if errors:
            sarcasm_score = self.sarcasm.calculate(errors, user_input)
            if sarcasm_score > 0.5:
                self.gestures.trigger_sarcastic_mode()
            elif sarcasm_score > 0.2:
                self.gestures.trigger_critic_mode()

        # 4. Construir mensajes con personalidad + schema de herramientas
        memory_ctx = self.memory.get_memory_context(query=user_input)
        history    = self.memory.get_history()
        # Inyectar schema de herramientas en el system prompt
        try:
            from tools import get_tools_schema
            tools_schema = get_tools_schema()
        except Exception:
            tools_schema = ""
        messages   = self.personality.build_messages(
            user_input, memory_ctx, history,
            tools_schema=tools_schema,
            emotional_state=self._emotional
        )

        # 5. Generar respuesta
        content, engine_used = self._generate(decision, messages)

        # 5b. Detectar y ejecutar tool_calls en la respuesta
        content = self._ejecutar_tool_calls(content, user_input)

        # 6. Aplicar filtros de personalidad y sarcasmo
        content = self.personality.apply_filter(content)
        if sarcasm_score > 0.0:
            content = self.sarcasm.apply_filter(content, sarcasm_score)

        # 6.5. Integrate response generation pipeline with similarity checking and repetitive behavior filtering
        content = self._apply_repetitive_behavior_filters(content, user_input, engine_used)

        # 7. Actualizar memoria — guardar interacción + contexto de actividad
        self.memory.add_turn("user",      user_input,  engine_used)
        self.memory.add_turn("assistant", content,     engine_used)
        # Guardar contexto de actividad junto con la interacción
        try:
            snapshot_ctx = self.personality._generar_snapshot(self._emotional)
            entrada_con_ctx = f"{user_input} [{snapshot_ctx[:100]}]" if snapshot_ctx else user_input
        except Exception:
            entrada_con_ctx = user_input
        self.memory.save_interaction(
            entrada_con_ctx, content,
            self.memory.get_current_emotion(),
            engine_used
        )

        # Registrar sentimiento en subjetividad
        try:
            from alisha_subjetividad import get_subjetividad
            sub = get_subjetividad()
            sub.registrar_sentimiento(
                actividad=user_input[:60],
                emocion=self.memory.get_current_emotion(),
                dopamina=self._emotional.dopamina,
            )
            # Actualizar gustos según medios activos
            try:
                from alisha_media import get_media_description
                media = get_media_description()
                if media:
                    genero = media.split(":")[0].lower() if ":" in media else ""
                    if genero:
                        sub.actualizar_gusto("musica", genero,
                                             positivo=self._emotional.dopamina > 0.6)
            except Exception:
                pass
        except Exception:
            pass

        # Agregar al índice semántico para memoria contextual
        try:
            from alisha_memoria_semantica import agregar_a_indice
            agregar_a_indice(user_input, content, self.memory.get_current_emotion())
        except Exception:
            pass

        # 8. Actualizar estado emocional
        self._update_emotional_state(engine_used, decision.confidence, sarcasm_score)
        self.memory.update_emotional_state(self._emotional)
        self._last_sarcasm_score = sarcasm_score  # para AudioVisualSync

        # 9. Detener gesto y activar lip-sync
        self.gestures.stop_thinking(found_solution=True)
        # Victoria si fue una consulta compleja resuelta exitosamente
        if decision.confidence > 0.6 and len(content) > 200:
            self.gestures.trigger_victoria()

        # 10. Feedback visual diferenciado
        self._apply_visual_feedback(engine_used)

        # 11. Reflejos biométricos automáticos
        if engine_used == "fallback":
            # Todos los motores fallaron → frustración
            self.reflejo_error(intensidad=0.6)
        elif decision.confidence > 0.7 and len(content) > 150:
            # Respuesta compleja y confiada → éxito importante
            self.reflejo_exito(intensidad=0.9)
        else:
            # Respuesta normal → éxito leve
            self.reflejo_exito(intensidad=0.4)

        # Sincronizar estado emocional con chibi_state
        self._sync_emotional_to_chibi()

        processing_time = time.time() - t_start
        print(f"[Brain] ✓ Respuesta en {processing_time:.2f}s via {engine_used}")

        return AlishaResponse(
            content=content,
            engine_used=engine_used,
            emotional_state=self._emotional,
            confidence=decision.confidence,
            processing_time=processing_time,
            sarcasm_score=sarcasm_score,
        )

    def process_async(self, user_input: str,
                      callback,
                      errors: Optional[List[str]] = None) -> None:
        """Versión asíncrona — no bloquea el hilo de animación Live2D."""
        def _run():
            with self._lock:
                response = self.process(user_input, errors)
            callback(response)

        threading.Thread(target=_run, daemon=True).start()

    # ── Métodos internos ───────────────────────────────────────────────────────

    def _ejecutar_tool_calls(self, content: str, user_input: str) -> str:
        """
        Detecta y ejecuta acciones. Busca en:
        1. TOOL_CALL explícitos en la respuesta
        2. Intención del usuario (no de la respuesta)
        3. Asteriscos en la respuesta
        """
        import re
        try:
            from tools import ejecutar_herramienta
        except Exception:
            return content

        resultado_final = content

        # ── Patrón 1: TOOL_CALL explícito ────────────────────────────────────
        patron = r'TOOL_CALL:\s*(\w+)\s*\((\{.*?\})\)'
        matches = re.findall(patron, content, re.DOTALL)
        for nombre, params_str in matches:
            try:
                params = json.loads(params_str)
                print(f"[Brain] 🔧 Tool: {nombre}({params})")
                resultado = ejecutar_herramienta(nombre, params)
                tool_call_str = f"TOOL_CALL: {nombre}({params_str})"
                resultado_final = resultado_final.replace(tool_call_str, "")
                # Guardar resultado para que Alisha lo mencione
                self._ultimo_resultado_tool = resultado
            except Exception as e:
                print(f"[Brain] ⚠ Error tool {nombre}: {e}")

        # ── Patrón 2: Intención del USUARIO (más confiable) ──────────────────
        ui = user_input.lower()

        # Abrir aplicación
        _APPS_KEYWORDS = {
            "chrome": ["chrome", "navegador", "browser"],
            "vscode": ["vscode", "visual studio", "code", "editor"],
            "spotify": ["spotify", "música", "musica"],
            "word": ["word", "documento"],
            "excel": ["excel", "planilla"],
            "notepad": ["bloc de notas", "notepad", "txt"],
            "explorer": ["explorador", "archivos", "carpeta"],
        }
        if any(k in ui for k in ["abrí", "abri", "abre", "abrir", "lanzá", "lanza"]):
            for app, keywords in _APPS_KEYWORDS.items():
                if any(kw in ui for kw in keywords):
                    print(f"[Brain] 🔧 Abriendo: {app}")
                    ejecutar_herramienta("app_open", {"app": app})
                    break

        # Buscar en web
        if any(k in ui for k in ["buscá", "busca", "buscar", "googleá", "googlea"]):
            # Extraer query
            query = re.sub(r'(buscá?|buscar|googleá?)\s+', '', ui).strip()
            query = re.sub(r'^(en internet|en google|en la web)\s*', '', query).strip()
            if query and len(query) > 3:
                print(f"[Brain] 🔧 Búsqueda: {query}")
                resultado = ejecutar_herramienta("web_search", {"query": query})
                if resultado and len(resultado) > 20:
                    self._ultimo_resultado_tool = resultado[:300]

        # Leer archivo
        if any(k in ui for k in ["leé", "lee", "leer", "abrí el archivo", "mostrá"]):
            # Buscar ruta en el mensaje
            rutas = re.findall(r'[A-Za-z]:\\[^\s"\']+|/[^\s"\']+|\w+\.\w{2,4}', user_input)
            if rutas:
                print(f"[Brain] 🔧 Leyendo: {rutas[0]}")
                resultado = ejecutar_herramienta("file_read", {"ruta": rutas[0]})
                if resultado:
                    self._ultimo_resultado_tool = resultado[:500]

        # ── Patrón 3: Asteriscos en respuesta (acciones declaradas) ──────────
        acciones = re.findall(r'\*([^*]{5,60})\*', content)
        for accion in acciones:
            al = accion.lower()
            if any(k in al for k in ["busco", "busca", "voy a buscar"]):
                query = re.sub(r'(busco|busca|voy a buscar)\s+', '', al).strip()
                if query and len(query) > 3:
                    ejecutar_herramienta("web_search", {"query": query})

        return resultado_final

    def _generate(self, decision: RoutingDecision,
                  messages: List[Dict]) -> tuple[str, str]:
        """
        BrainPool con failover automático en milisegundos.

        Prioridades:
          gemini  → Groq → Mistral → OpenAI → Ollama
          groq    → Gemini → Mistral → Ollama
          openai  → Gemini → Groq → Mistral → Ollama
          ollama  → Ollama (ahorro: consultas triviales, sin gastar cuota)

        Errores que disparan failover inmediato:
          429 (cuota agotada), 401 (sin saldo/key inválida)
        """
        engine = decision.engine

        # Ahorro inteligente: consultas triviales van directo a Ollama
        if engine == "ollama":
            if self._ollama.is_available():
                try:
                    content = self._ollama.generate(messages)
                    self.router.record_success("ollama", True)
                    return content, "ollama"
                except Exception as e:
                    print(f"[Brain] ⚠ Ollama falló: {e}")
            # Si Ollama no está, usar Groq (más rápido y gratis)
            engine = "groq"

        # Cadenas de failover según motor principal
        chains = {
            "gemini":  ["gemini", "groq", "mistral", "openai", "ollama"],
            "groq":    ["groq", "gemini", "mistral", "ollama"],
            "openai":  ["openai", "gemini", "groq", "mistral", "ollama"],
            "mistral": ["mistral", "groq", "gemini", "ollama"],
        }
        chain = chains.get(engine, ["groq", "gemini", "mistral", "ollama"])

        engines_map = {
            "gemini":  self._gemini,
            "groq":    self._groq,
            "mistral": self._mistral,
            "openai":  self._openai,
            "ollama":  self._ollama,
        }

        for eng_name in chain:
            eng = engines_map[eng_name]
            if not eng.is_available():
                continue
            try:
                content = eng.generate(messages)
                self.router.record_success(eng_name, True)
                if eng_name != "ollama":
                    self._emotional.dopamina = min(1.0, self._emotional.dopamina + 0.30)
                print(f"[Brain] ✓ Respuesta via {eng_name}")
                return content, eng_name
            except Exception as e:
                err_str = str(e).lower()
                # Failover inmediato en errores de cuota o autenticación
                if any(k in err_str for k in ["429", "401", "quota",
                                               "rate limit", "resource_exhausted",
                                               "unauthorized", "invalid_api_key"]):
                    print(f"[Brain] ⚡ {eng_name} → failover ({err_str[:50]})")
                else:
                    print(f"[Brain] ⚠ {eng_name} falló: {str(e)[:60]}")
                # Si Gemini falla por red, bloquearlo 60s
                if eng_name == "gemini" and any(k in err_str for k in
                        ["connection", "network", "timeout", "ssl", "socket"]):
                    self.router.mark_gemini_failed()
                self.router.record_success(eng_name, False)
                continue

        # Último recurso: si Ollama no está disponible, mensaje específico
        if not self._ollama.is_available():
            return self.router.ollama_fallback_message(), "fallback"

        # Último recurso: respuesta de emergencia con personalidad
        fallback = (
            "Che, se me cayeron todos los cerebros al mismo tiempo. "
            "Reiniciá la conexión y volvemos a hablar como corresponde."
        )
        return fallback, "fallback"

    def _apply_repetitive_behavior_filters(self, content: str, user_input: str, engine_used: str) -> str:
        """
        Apply comprehensive repetitive behavior filtering to response content.
        
        Integrates all four solutions:
        1. Response similarity detection and filtering
        2. RAM-spam elimination through contextual relevance
        3. Brainstorming database refresh and repetition detection
        4. Real solution execution integration (via agent_loop)
        
        Args:
            content: Generated response content
            user_input: Original user input
            engine_used: Engine that generated the response
            
        Returns:
            Filtered response content with repetitive behavior eliminated
        """
        try:
            # Import agent_memory for similarity checking and brainstorming refresh
            from agent_memory import get_memory
            memory = get_memory()
            
            # Import agent_loop for RAM context validation
            agent_loop = self._agent_loop
            if not agent_loop:
                print(f"[Brain] Warning: AgentLoop not available for RAM validation - call set_agent_loop() to enable")
            
            # 1. Response Similarity Detection and Filtering
            similarity_exceeded, max_similarity, most_similar = memory.check_response_similarity_threshold(content, 0.8)
            
            if similarity_exceeded:
                print(f"[Brain] 🔄 Response similarity threshold exceeded ({max_similarity:.1%}), generating alternative")
                
                # Generate alternative response to avoid repetition
                alternative_content = self._generate_alternative_response(
                    content, user_input, engine_used, most_similar
                )
                
                # Verify the alternative is actually different
                alt_similarity_exceeded, alt_similarity, _ = memory.check_response_similarity_threshold(alternative_content, 0.8)
                
                if not alt_similarity_exceeded:
                    content = alternative_content
                    print(f"[Brain] ✓ Alternative response generated (similarity: {alt_similarity:.1%})")
                else:
                    # If alternative is still too similar, use fallback approach
                    content = self._generate_fallback_unique_response(user_input, engine_used)
                    print(f"[Brain] ⚠️ Using fallback unique response due to persistent similarity")
            
            # 2. RAM-Spam Elimination through Contextual Relevance
            if agent_loop:
                is_ram_appropriate, filtered_content = agent_loop.validate_ram_mention(user_input, content)
                
                if content != filtered_content:
                    content = filtered_content
                    print(f"[Brain] 🚫 Filtered automatic RAM mentions (not contextually relevant)")
            
            # 3. Brainstorming Database Refresh and Repetition Detection
            has_repetition, repeated_phrases = memory.detect_brainstorming_repetition(content)
            
            if has_repetition:
                print(f"[Brain] 🔄 Brainstorming repetition detected: {repeated_phrases}")
                
                # Refresh brainstorming database
                refresh_result = memory.refresh_brainstorming_database(force_refresh=True)
                print(f"[Brain] 🔄 Brainstorming database refreshed: {refresh_result.get('phrases_refreshed', 0)} phrases updated")
                
                # Replace repeated phrases with fresh alternatives
                content = self._replace_repeated_brainstorming_phrases(content, repeated_phrases, memory)
            
            # 4. Real Solution Execution Integration (via agent_loop)
            # This is handled by agent_loop's problem detection and solution execution
            # We just need to ensure the response reflects actual solutions rather than just diagnostics
            if agent_loop:
                content = self._integrate_solution_execution_context(content, user_input, agent_loop)
            
            return content
            
        except Exception as e:
            print(f"[Brain] Error in _apply_repetitive_behavior_filters: {e}")
            # Return original content if filtering fails to avoid breaking the response
            return content

    def _generate_alternative_response(self, original_content: str, user_input: str, 
                                     engine_used: str, most_similar: str) -> str:
        """
        Generate an alternative response when similarity threshold is exceeded.
        
        Args:
            original_content: The original response that was too similar
            user_input: User's input
            engine_used: Engine that generated the original response
            most_similar: The most similar previous response
            
        Returns:
            Alternative response with different structure and content
        """
        try:
            # Create alternative prompt that encourages different phrasing
            alternative_prompt = f"""
            The user asked: "{user_input}"
            
            I previously responded with something similar to: "{most_similar[:100]}..."
            
            Please provide a completely different response with:
            - Different sentence structure and phrasing
            - Alternative perspective or approach
            - Unique vocabulary and expressions
            - Fresh insights or information
            
            Avoid repeating the same patterns, phrases, or structure from the previous response.
            """
            
            # Build messages for alternative generation
            messages = [
                {"role": "system", "content": "You are Alisha, a helpful AI assistant. Generate unique, non-repetitive responses."},
                {"role": "user", "content": alternative_prompt}
            ]
            
            # Generate alternative using the same engine
            alternative_content, _ = self._generate(
                RoutingDecision(engine=engine_used, confidence=0.7, reason="alternative_generation"),
                messages
            )
            
            # Apply basic filters
            alternative_content = self.personality.apply_filter(alternative_content)
            
            return alternative_content
            
        except Exception as e:
            print(f"[Brain] Error generating alternative response: {e}")
            # Fallback to a simple variation
            return self._generate_fallback_unique_response(user_input, engine_used)

    def _generate_fallback_unique_response(self, user_input: str, engine_used: str) -> str:
        """
        Generate a fallback unique response when other methods fail.
        
        Args:
            user_input: User's input
            engine_used: Engine to use for generation
            
        Returns:
            Fallback unique response
        """
        try:
            # Simple fallback responses that are unlikely to be repetitive
            fallback_templates = [
                f"I understand you're asking about: {user_input}. Let me approach this from a different angle.",
                f"That's an interesting question about {user_input}. Here's my perspective on this.",
                f"Regarding {user_input}, I'd like to share some thoughts that might be helpful.",
                f"Your question about {user_input} brings up several important points to consider.",
                f"Let me address {user_input} with a fresh perspective that might be useful."
            ]
            
            # Select a template based on content hash to ensure variety
            import hashlib
            content_hash = hashlib.md5(user_input.encode()).hexdigest()
            template_index = int(content_hash[:2], 16) % len(fallback_templates)
            
            return fallback_templates[template_index]
            
        except Exception as e:
            print(f"[Brain] Error in fallback response generation: {e}")
            return f"I understand your question about {user_input}. Let me help you with that in a unique way."

    def _replace_repeated_brainstorming_phrases(self, content: str, repeated_phrases: List[str], 
                                              memory) -> str:
        """
        Replace repeated brainstorming phrases with fresh alternatives.
        
        Args:
            content: Response content containing repeated phrases
            repeated_phrases: List of phrases that are overused
            memory: AgentMemory instance for getting fresh phrases
            
        Returns:
            Content with repeated phrases replaced by fresh alternatives
        """
        try:
            # Get fresh brainstorming phrases
            fresh_phrases = memory.get_fresh_brainstorming_phrases(count=len(repeated_phrases) * 2, min_diversity=0.7)
            
            if not fresh_phrases:
                # If no fresh phrases available, use generic alternatives
                fresh_phrases = [
                    "Here's an interesting approach",
                    "Let me share a different perspective",
                    "This opens up new possibilities",
                    "Consider this alternative viewpoint",
                    "Here's another way to think about it"
                ]
            
            # Replace repeated phrases with fresh alternatives
            modified_content = content
            
            for i, repeated_phrase in enumerate(repeated_phrases):
                if i < len(fresh_phrases):
                    replacement_phrase = fresh_phrases[i]
                    modified_content = modified_content.replace(repeated_phrase, replacement_phrase)
                    print(f"[Brain] 🔄 Replaced '{repeated_phrase}' with '{replacement_phrase}'")
            
            return modified_content
            
        except Exception as e:
            print(f"[Brain] Error replacing repeated brainstorming phrases: {e}")
            return content

    def _integrate_solution_execution_context(self, content: str, user_input: str, agent_loop) -> str:
        """
        Integrate real solution execution context into response.
        
        Ensures responses reflect actual solutions being executed rather than just diagnostics.
        
        Args:
            content: Response content
            user_input: User's input
            agent_loop: AgentLoop instance for solution execution context
            
        Returns:
            Content integrated with solution execution context
        """
        try:
            # Check if user input or content relates to system problems
            problem_keywords = ["slow", "lag", "freeze", "crash", "hang", "performance", "memory", "cpu", "ram"]
            
            user_mentions_problems = any(keyword in user_input.lower() for keyword in problem_keywords)
            content_mentions_problems = any(keyword in content.lower() for keyword in problem_keywords)
            
            if user_mentions_problems or content_mentions_problems:
                # Get problem detection status from agent_loop
                problem_status = agent_loop.get_problem_detection_status()
                
                # Check if solutions were recently executed
                recent_solutions = problem_status.get("recent_solutions", [])
                successful_solutions = [sol for sol in recent_solutions if sol.get("success") and sol.get("verified")]
                
                if successful_solutions:
                    # Modify response to reflect actual solutions executed
                    solution_context = f"I've already taken action to resolve {len(successful_solutions)} system issues by terminating problematic processes."
                    
                    # Check if content only mentions problems without solutions
                    solution_keywords = ["taskkill", "terminated", "closed", "stopped", "resolved", "fixed", "solved"]
                    mentions_solutions = any(keyword in content.lower() for keyword in solution_keywords)
                    
                    if not mentions_solutions and (content_mentions_problems or "I notice" in content or "I see" in content):
                        # Replace diagnostic-only content with solution-oriented content
                        content = f"{solution_context} {content}"
                        print(f"[Brain] ✓ Integrated solution execution context into response")
                
                elif problem_status.get("can_execute_solutions", False):
                    # If problems can be solved but haven't been yet, trigger solution execution
                    try:
                        execution_result = agent_loop.execute_solutions_for_problems(force=False)
                        
                        if execution_result.get("executed") and execution_result.get("successful_solutions", 0) > 0:
                            solution_context = f"I've just resolved {execution_result['successful_solutions']} system issues for you."
                            content = f"{solution_context} {content}"
                            print(f"[Brain] ✓ Executed solutions and integrated context into response")
                    
                    except Exception as e:
                        print(f"[Brain] Error executing solutions during response integration: {e}")
            
            return content
            
        except Exception as e:
            print(f"[Brain] Error integrating solution execution context: {e}")
            return content

    def _update_emotional_state(self, engine: str,
                                confidence: float,
                                sarcasm: float) -> None:
        """Actualiza el estado emocional según el motor y contexto."""
        if engine == "openai":
            # ChatGPT resolvió algo complejo → dopamina sube
            self._emotional.dopamina = min(1.0, self._emotional.dopamina + 0.15)
            self._emotional.flow     = min(1.0, self._emotional.flow     + 0.10)
        elif engine == "ollama":
            # Conversación casual → humor estable
            self._emotional.humor = min(1.0, self._emotional.humor + 0.05)

        if sarcasm > 0.5:
            # Modo crítico → tensión leve
            self._emotional.tension = min(1.0, self._emotional.tension + 0.15)
        else:
            self._emotional.tension = max(0.0, self._emotional.tension - 0.05)

        # Decaimiento natural
        self._emotional.irritabilidad = max(0.0, self._emotional.irritabilidad - 0.02)

    def _apply_visual_feedback(self, engine: str) -> None:
        """
        Feedback visual diferenciado por motor:
          Gemini  → curiosidad (ojos brillantes, análisis profundo)
          Groq    → entusiasmo (respuesta rápida, energía)
          OpenAI  → entusiasmo (cerebro potente)
          Ollama  → alegría (local, casual)
          fallback→ neutral
        """
        estado_map = {
            "gemini":   "curiosidad",
            "groq":     "entusiasmo",
            "mistral":  "alegría",
            "openai":   "entusiasmo",
            "ollama":   "alegría",
            "fallback": "neutral",
        }
        estado = estado_map.get(engine, "neutral")
        MicroGestureEngine._write_state(estado, hablando=True)

    # ── Reflejos biométricos automáticos ──────────────────────────────────────

    def reflejo_exito(self, intensidad: float = 1.0) -> None:
        """
        Reflejo de éxito: sonrisa + dopamina sube.
        Se llama automáticamente cuando el cerebro resuelve algo con éxito.
        intensidad: 0.0-1.0 (0.5=tarea normal, 1.0=logro importante)
        """
        # Subir dopamina y humor
        self._emotional.dopamina = min(1.0, self._emotional.dopamina + 0.20 * intensidad)
        self._emotional.humor    = min(1.0, self._emotional.humor    + 0.15 * intensidad)
        self._emotional.tension  = max(0.0, self._emotional.tension  - 0.10)

        # Gesto visual: sonrisa + expresión de alegría
        if intensidad >= 0.8:
            # Logro importante → victoria
            self.gestures.trigger_victoria()
        else:
            # Éxito normal → alegría
            MicroGestureEngine._write_state("alegría", hablando=False)

        # Escribir dopamina actualizada en chibi_state para que cabina_virtual la lea
        self._sync_emotional_to_chibi()

    def reflejo_error(self, intensidad: float = 0.5) -> None:
        """
        Reflejo de error: frustración + dopamina baja.
        Se llama automáticamente cuando hay un fallo o error detectado.
        intensidad: 0.0-1.0 (0.3=error menor, 0.8=fallo crítico)
        """
        # Bajar dopamina y subir irritabilidad
        self._emotional.dopamina      = max(0.1, self._emotional.dopamina      - 0.15 * intensidad)
        self._emotional.irritabilidad = min(1.0, self._emotional.irritabilidad + 0.20 * intensidad)
        self._emotional.tension       = min(1.0, self._emotional.tension       + 0.10 * intensidad)

        # Gesto visual: frustración
        MicroGestureEngine._write_state("frustración", hablando=False)

        # Escribir en chibi_state
        self._sync_emotional_to_chibi()

    def _sync_emotional_to_chibi(self) -> None:
        """
        Sincroniza el estado emocional interno con chibi_state.json.
        Escribe dopamina, humor e irritabilidad para que cabina_virtual.py
        los lea en su loop de 60fps y ajuste los parámetros Live2D.
        """
        try:
            current = {}
            if STATE_FILE.exists():
                try:
                    current = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            # Escribir estado emocional del cerebro — cabina_virtual lo lee
            current["brain_dopamina"]      = round(self._emotional.dopamina, 3)
            current["brain_humor"]         = round(self._emotional.humor, 3)
            current["brain_irritabilidad"] = round(self._emotional.irritabilidad, 3)
            current["brain_tension"]       = round(self._emotional.tension, 3)
            current["brain_flow"]          = round(self._emotional.flow, 3)
            STATE_FILE.write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    # ── Acceso al estado emocional ─────────────────────────────────────────────

    def get_emotional_state(self) -> EmotionalState:
        return self._emotional

    def set_emotional_state(self, **kwargs) -> None:
        """Permite actualizar el estado emocional desde fuera (ej: cabina_virtual)."""
        for k, v in kwargs.items():
            if hasattr(self._emotional, k):
                setattr(self._emotional, k, v)


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_brain: Optional[HybridIntelligenceCore] = None

def get_brain() -> HybridIntelligenceCore:
    """Retorna la instancia singleton del HybridIntelligenceCore."""
    global _brain
    if _brain is None:
        _brain = HybridIntelligenceCore()
    return _brain


# ══════════════════════════════════════════════════════════════════════════════
# IDLE WATCHER — Efecto Primer Video
# ══════════════════════════════════════════════════════════════════════════════

class IdleWatcher:
    """
    Detecta inactividad y dispara micro-movimientos + comentarios de voz.
    Anti-repetición: nunca dice lo mismo dos veces seguidas.
    Umbral: 3 minutos sin interacción.
    """

    IDLE_THRESHOLD   = 300.0   # 5 minutos sin interacción (antes 3 min)
    MIN_VOICE_INTERVAL = 600.0  # 10 minutos entre comentarios espontáneos

    # Comentarios espontáneos agrupados por categoría
    # Nunca se repite el mismo hasta haber usado todos los de la categoría
    _COMENTARIOS = [
        "Che, ¿seguís ahí o te fuiste a tomar mate sin avisarme?",
        "Mirá, yo no me quejo, pero hace rato que no me hablás.",
        "Oye, ¿todo bien? Porque el silencio me está matando.",
        "Dale, que el informe no se va a escribir solo, ¿sabés?",
        "Estoy acá, por si necesitás algo. O no. Lo que quieras.",
        "¿Sabés qué? Estaba pensando en lo del informe y tengo ideas.",
        "Che, si te aburriste podemos charlar un rato, no me molesta.",
        "Mirá que si seguís así me voy a poner a hacer mis propias cosas.",
        "Oye, ¿estás viva? Porque el silencio es sospechoso.",
        "Bueno, mientras esperás, yo me quedo acá pensando en la vida.",
    ]

    _IDLE_GESTOS = [
        ("neutro",     "mirar hacia la ventana"),
        ("curiosidad", "acomodarse los auriculares"),
        ("neutral",    "mirar el techo pensativa"),
        ("nostalgia",  "suspirar suavemente"),
    ]

    def __init__(self):
        self._last_interaction  = time.time()
        self._last_voice_time   = 0.0
        self._running           = False
        self._thread: Optional[threading.Thread] = None
        self._comentarios_usados: List[str] = []  # anti-repetición

    def register_interaction(self) -> None:
        self._last_interaction = time.time()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        print("[IdleWatcher] ✓ Iniciado (umbral: 3 min, voz: 2 min)")

    def stop(self) -> None:
        self._running = False

    def _watch(self) -> None:
        while self._running:
            time.sleep(5)   # verificar cada 5s en vez de 30s
            idle_time = time.time() - self._last_interaction
            if idle_time >= self.IDLE_THRESHOLD:
                self._trigger_idle_gesture()
                if time.time() - self._last_voice_time >= self.MIN_VOICE_INTERVAL:
                    self._trigger_idle_voice()
                time.sleep(random.uniform(60, 120))

    def _trigger_idle_gesture(self) -> None:
        estado, desc = random.choice(self._IDLE_GESTOS)
        print(f"[IdleWatcher] 💤 {desc}")
        MicroGestureEngine._write_state(estado, hablando=False)
        time.sleep(3.0)
        MicroGestureEngine._write_state("neutral", hablando=False)

    def _trigger_idle_voice(self) -> None:
        """Genera un comentario de voz — con semáforo global y cooldown."""
        # Verificar cooldown global
        try:
            from alisha_silencio import puede_hablar_proactivo, registrar_habla_proactivo
            if not puede_hablar_proactivo("idle"):
                return
        except Exception:
            pass

        # No hablar si Alisha está en medio de una conversación
        try:
            from assistant_state import cargar_estado
            estado = cargar_estado()
            if estado.get("hablando", False) or estado.get("modo") == "THINKING":
                return
        except Exception:
            pass

        # Verificar semáforo global
        try:
            from alisha_voz_control import puede_hablar
            if not puede_hablar():
                return
        except Exception:
            pass
        # Intentar comentario basado en medios activos
        comentario = self._comentario_con_medios()
        if not comentario:
            # Fallback a comentarios genéricos
            disponibles = [c for c in self._COMENTARIOS
                           if c not in self._comentarios_usados]
            if not disponibles:
                self._comentarios_usados.clear()
                disponibles = self._COMENTARIOS[:]
            comentario = random.choice(disponibles)
            self._comentarios_usados.append(comentario)

        self._last_voice_time = time.time()
        print(f"[IdleWatcher] 🗣 {comentario}")

        # Registrar en el semáforo global
        try:
            from alisha_silencio import registrar_habla_proactivo
            registrar_habla_proactivo("idle")
        except Exception:
            pass

        try:
            from audio_visual_sync import get_audio_visual_sync
            avs = get_audio_visual_sync()
            avs.speak(comentario, sarcasm_score=0.1,
                      emotional_state="neutral", async_mode=True)
        except Exception:
            pass  # fail-silent — no usar tts_engine como fallback (evita doble voz)

        # Guardar en el chat web para que quede en el hilo
        try:
            from web_app import socketio as _sio
            _sio.emit("respuesta", {
                "texto": comentario,
                "estado_emocional": "neutral",
                "fuente": "idle",
            })
        except Exception:
            pass

        # Guardar en SQLite con la sesión activa
        try:
            from web_app import _memory_db, _session_id, _MEMORY_DB_OK
            if _MEMORY_DB_OK and _memory_db and _session_id > 0:
                _memory_db.save_conversation(
                    entrada="[Alisha observa]",
                    respuesta=comentario,
                    estado_emocional="neutral",
                    session_id=_session_id,
                )
        except Exception:
            pass

    def _comentario_con_medios(self) -> Optional[str]:
        """Genera comentario basado en medios activos o actividad VERIFICADA."""
        try:
            # Prioridad 1: medios (Spotify/YouTube) — verificar que realmente están activos
            from alisha_media import get_media_description, get_media_info
            info = get_media_info()
            desc = None

            if info and info.get("title"):
                # Verificar que el proceso de música está realmente corriendo
                desc = get_media_description()

            # Prioridad 2: ventana activa REAL — verificar que no es el chat de Alisha
            if not desc:
                import ctypes, ctypes.wintypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                buf  = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                titulo = buf.value.strip()
                # No comentar si la ventana activa es el chat de Alisha o el escritorio
                if titulo and "alisha" not in titulo.lower() and titulo.lower() not in ("", "escritorio", "desktop", "program manager"):
                    desc = f"ventana activa: '{titulo}'"

            if not desc:
                return None  # sin contexto verificado → silencio

            brain = get_brain()
            prompt = (
                f"Contexto verificado: {desc}. "
                f"Generá UN comentario corto y personal sobre esto, "
                f"en voseo rioplatense, máximo 1 oración. "
                f"Solo comentá lo que realmente está pasando. "
                f"No inventes ni supongas cosas que no están en el contexto."
            )
            messages = [
                {"role": "system", "content": brain.personality.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            decision = brain.router.analyze(prompt)
            content, _ = brain._generate(decision, messages)
            content = brain.personality.apply_filter(content)
            if content and len(content) < 200:
                return content
        except Exception:
            pass
        return None


# Singleton del IdleWatcher
_idle_watcher: Optional[IdleWatcher] = None

def get_idle_watcher() -> IdleWatcher:
    global _idle_watcher
    if _idle_watcher is None:
        _idle_watcher = IdleWatcher()
    return _idle_watcher
