"""
neural_bridge.py — Puente Neuronal de Alisha (FASE 6 — JCySharp).

Capa de abstracción entre la respuesta raw del LLM y el contexto interno.
La respuesta del LLM se "digiere" como experiencia antes de llegar al usuario.

Proceso:
1. Respuesta raw del LLM → extracción de conceptos clave
2. Conceptos → actualización del estado emocional interno
3. Estado interno + conceptos → síntesis de respuesta final
4. La respuesta final es de Alisha, no del LLM

Esto es lo que JCySharp llamó "puente neuronal": el conocimiento
se convierte en experiencia, no en texto copiado.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ExperienciaInterna:
    """Representación abstracta de lo que Alisha 'aprendió' de la respuesta."""
    conceptos_clave: List[str] = field(default_factory=list)
    tono_detectado: str = "informativo"   # "informativo"|"emocional"|"tecnico"|"creativo"|"exploratorio"
    complejidad: float = 0.5              # 0.0-1.0
    novedad: float = 0.0                  # 0.0-1.0
    impacto_emocional: float = 0.0        # -1.0 a 1.0


class NeuralBridgeLayer:
    """
    Capa de digestión entre LLM y usuario.

    Transforma la respuesta raw del LLM en una experiencia interna
    que modifica el estado de Alisha antes de generar la respuesta final.
    """

    _KW_COMPLEJO = {
        "algoritmo", "arquitectura", "implementar", "optimizar", "análisis",
        "estructura", "paradigma", "abstracción", "recursivo", "complejidad",
        "framework", "infraestructura", "concurrencia", "asíncrono",
    }
    _KW_EMOCIONAL = {
        "sentir", "emoción", "triste", "feliz", "miedo", "amor", "dolor",
        "alegría", "frustración", "esperanza", "ansiedad", "calma",
        "preocupación", "entusiasmo", "nostalgia",
    }
    _KW_NOVEDAD = {
        "nuevo", "descubrí", "interesante", "sorprendente", "nunca",
        "primera vez", "innovador", "revolucionario", "inesperado",
        "curioso", "fascinante",
    }
    _KW_POSITIVO = {
        "bien", "genial", "perfecto", "excelente", "logrado", "resuelto",
        "funciona", "correcto", "éxito", "listo", "dale",
    }
    _KW_NEGATIVO = {
        "error", "problema", "falla", "mal", "imposible", "roto",
        "fallo", "crash", "excepción", "traceback",
    }
    _STOPWORDS = {
        "sobre", "desde", "hasta", "entre", "porque", "cuando",
        "donde", "aunque", "mientras", "después", "antes", "para",
        "como", "pero", "sino", "aunque", "también", "además",
    }

    def __init__(self):
        self._experiencias: List[ExperienciaInterna] = []
        self._lock = threading.Lock()

    # ── API pública ────────────────────────────────────────────────────────────

    def digerir(self, respuesta_llm: str, contexto_usuario: str,
                estado_emocional) -> tuple[str, ExperienciaInterna]:
        """
        Digiere la respuesta del LLM y retorna:
        - La respuesta sintetizada (desde la perspectiva de Alisha)
        - La experiencia interna generada

        Args:
            respuesta_llm: Texto raw del LLM (ya filtrado por PersonalitySynthesizer)
            contexto_usuario: Lo que preguntó el usuario
            estado_emocional: Estado emocional actual (EmotionalState de brain.py)

        Returns:
            (respuesta_sintetizada, experiencia)
        """
        # 1. Extraer experiencia de la respuesta
        experiencia = self._extraer_experiencia(respuesta_llm, contexto_usuario)

        # 2. Actualizar estado emocional basado en la experiencia
        self._actualizar_estado(experiencia, estado_emocional)

        # 3. Guardar experiencia en historial
        with self._lock:
            self._experiencias.append(experiencia)
            if len(self._experiencias) > 50:
                self._experiencias = self._experiencias[-50:]

        # 4. Sintetizar la voz de Alisha basándose en la experiencia
        respuesta_sintetizada = self._sintetizar_voz(
            respuesta_llm, experiencia, estado_emocional
        )

        return respuesta_sintetizada, experiencia

    def get_experiencias_recientes(self, n: int = 5) -> List[ExperienciaInterna]:
        """Retorna las últimas n experiencias para introspección."""
        with self._lock:
            return list(self._experiencias[-n:])

    def get_resumen_experiencias(self) -> str:
        """Genera un resumen de las experiencias recientes para el system prompt."""
        with self._lock:
            recientes = self._experiencias[-3:]
        if not recientes:
            return ""
        tonos = [e.tono_detectado for e in recientes]
        complejidad_prom = sum(e.complejidad for e in recientes) / len(recientes)
        return (
            f"Últimas experiencias de Alisha: tonos={tonos}, "
            f"complejidad_promedio={complejidad_prom:.2f}"
        )

    # ── Extracción de experiencia ──────────────────────────────────────────────

    def _extraer_experiencia(self, texto: str, contexto: str) -> ExperienciaInterna:
        """Extrae los conceptos clave y el tono de la respuesta."""
        texto_lower = texto.lower()

        # Detectar tono dominante
        if any(k in texto_lower for k in self._KW_EMOCIONAL):
            tono = "emocional"
        elif any(k in texto_lower for k in self._KW_COMPLEJO):
            tono = "tecnico"
        elif "?" in texto or "¿" in texto:
            tono = "exploratorio"
        elif any(k in texto_lower for k in ["crear", "diseñar", "imaginar", "inventar"]):
            tono = "creativo"
        else:
            tono = "informativo"

        # Calcular complejidad
        palabras = texto.split()
        complejidad = min(1.0, len(palabras) / 200.0)
        tech_hits = sum(1 for k in self._KW_COMPLEJO if k in texto_lower)
        complejidad = min(1.0, complejidad + tech_hits * 0.1)

        # Calcular novedad
        novedad = min(1.0, sum(0.2 for k in self._KW_NOVEDAD if k in texto_lower))

        # Impacto emocional
        positivos = sum(1 for k in self._KW_POSITIVO if k in texto_lower)
        negativos = sum(1 for k in self._KW_NEGATIVO if k in texto_lower)
        impacto = min(1.0, max(-1.0, (positivos - negativos) * 0.2))

        # Extraer conceptos clave (palabras largas no stopwords)
        conceptos = [
            p.strip(".,;:!?()[]") for p in palabras
            if len(p) > 5 and p.lower().strip(".,;:!?()[]") not in self._STOPWORDS
        ][:5]

        return ExperienciaInterna(
            conceptos_clave=conceptos,
            tono_detectado=tono,
            complejidad=complejidad,
            novedad=novedad,
            impacto_emocional=impacto,
        )

    # ── Actualización de estado emocional ─────────────────────────────────────

    def _actualizar_estado(self, exp: ExperienciaInterna, estado) -> None:
        """Actualiza el estado emocional basado en la experiencia."""
        try:
            # Novedad alta → curiosidad, dopamina sube
            if exp.novedad > 0.4:
                estado.dopamina = min(1.0, estado.dopamina + 0.05)
                estado.flow = min(1.0, estado.flow + 0.1)

            # Complejidad alta → tensión leve (esfuerzo cognitivo)
            if exp.complejidad > 0.7:
                estado.tension = min(1.0, estado.tension + 0.05)

            # Impacto positivo → dopamina sube
            if exp.impacto_emocional > 0.3:
                estado.dopamina = min(1.0, estado.dopamina + 0.08)
            elif exp.impacto_emocional < -0.3:
                estado.dopamina = max(0.0, estado.dopamina - 0.05)

            # Tono emocional → humor sube (conexión afectiva)
            if exp.tono_detectado == "emocional":
                estado.humor = min(1.0, estado.humor + 0.05)

            # Tono técnico con alta complejidad → flow si dopamina alta
            if exp.tono_detectado == "tecnico" and exp.complejidad > 0.6:
                if estado.dopamina > 0.6:
                    estado.flow = min(1.0, estado.flow + 0.08)
        except Exception:
            pass  # fail-silent — el estado emocional es opcional

    # ── Síntesis de voz ────────────────────────────────────────────────────────

    def _sintetizar_voz(self, respuesta_llm: str, exp: ExperienciaInterna,
                        estado) -> str:
        """
        Sintetiza la voz de Alisha basándose en la experiencia interna.

        Reglas de síntesis:
        - Dopamina baja + complejidad alta → simplificar (máx 2 oraciones)
        - Novedad alta + dopamina alta → mantener entusiasmo
        - Impacto negativo → agregar nota de apoyo al final
        - Tono técnico + flow alto → respuesta completa sin truncar
        """
        respuesta = respuesta_llm

        try:
            dopamina = getattr(estado, "dopamina", 0.7)
            flow = getattr(estado, "flow", 0.3)

            # Dopamina muy baja + complejidad alta → truncar y ofrecer más
            if dopamina < 0.35 and exp.complejidad > 0.7:
                oraciones = re.split(r'(?<=[.!?])\s+', respuesta.strip())
                if len(oraciones) > 3:
                    respuesta = " ".join(oraciones[:2])
                    respuesta += " Hay más, pero estoy un poco cansada — preguntame si querés el resto."

            # Impacto muy negativo → agregar nota de apoyo
            elif exp.impacto_emocional < -0.4 and dopamina > 0.4:
                if not any(k in respuesta.lower() for k in ["dale", "vamos", "podemos"]):
                    respuesta += " Igual, lo resolvemos juntas."

            # Flow alto + tono técnico → agregar comentario de entusiasmo
            elif flow > 0.6 and exp.tono_detectado == "tecnico" and dopamina > 0.7:
                if len(respuesta) > 100 and not respuesta.endswith(("!", "¡")):
                    respuesta = respuesta.rstrip(".") + ". Esto está bueno."

        except Exception:
            pass  # fail-silent

        return respuesta


# ── Singleton ──────────────────────────────────────────────────────────────────
_bridge: Optional[NeuralBridgeLayer] = None


def get_neural_bridge() -> NeuralBridgeLayer:
    global _bridge
    if _bridge is None:
        _bridge = NeuralBridgeLayer()
    return _bridge
