"""
self_awareness.py — Autoconciencia del asistente.

Lee el aprendizaje del entorno RL y lo combina con las capacidades
del asistente para que la IA sepa qué puede y qué no puede hacer.
"""
import json
import os
from pathlib import Path
from typing import Optional

# Ruta al archivo de autoconciencia generado por el entorno Pygame RL
_RL_AWARENESS_PATH = Path(__file__).parent / "self_awareness.json"

# Capacidades base del asistente (siempre disponibles)
_CAPACIDADES_BASE = {
    "control_pc": [
        "abrir aplicaciones instaladas",
        "navegar por internet con Playwright",
        "buscar en Google",
        "hacer clicks y llenar formularios web",
        "escribir texto en cualquier campo activo",
        "usar atajos de teclado",
        "tomar capturas de pantalla",
        "crear documentos Word",
        "tomar notas en texto",
        "controlar ventanas (minimizar, maximizar, cerrar)",
        "controlar volumen del sistema",
        "controlar brillo de pantalla",
        "buscar archivos en el sistema",
        "reproducir música",
        "apagar, reiniciar o suspender la PC",
        "programar recordatorios con alarma",
    ],
    "conocimiento_tecnico": [
        "explicar código Python, JavaScript y otros lenguajes",
        "revisar y corregir errores y bugs",
        "escribir scripts y funciones",
        "explicar algoritmos y estructuras de datos",
        "enseñar conceptos de redes y bases de datos",
        "ejecutar snippets de Python de forma segura",
        "explicar conceptos de sistemas operativos",
    ],
    "conversacion": [
        "mantener conversaciones naturales en español",
        "recordar el historial de conversaciones",
        "adaptarse al estado de ánimo del usuario",
        "hacer preguntas por curiosidad genuina",
        "expresar emociones y empatía",
    ],
}

# Limitaciones conocidas del asistente
_LIMITACIONES_BASE = [
    "no puede hacer clicks en posiciones exactas de páginas web sin conocer el selector",
    "no puede ver el contenido de ventanas sin tomar un screenshot",
    "no puede controlar aplicaciones que no estén instaladas",
    "no puede ejecutar código que use operaciones de sistema peligrosas",
    "no puede acceder a internet sin Playwright activo",
]


def cargar_aprendizaje_rl() -> dict:
    """Lee el archivo de autoconciencia del entorno RL si existe."""
    if _RL_AWARENESS_PATH.exists():
        try:
            with open(_RL_AWARENESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def obtener_capacidades() -> dict:
    """Combina capacidades base con habilidades aprendidas en el RL."""
    capacidades = dict(_CAPACIDADES_BASE)
    rl = cargar_aprendizaje_rl()

    if rl:
        habilidades_rl = rl.get("habilidades_aprendidas", [])
        if habilidades_rl:
            capacidades["aprendizaje_rl"] = [
                f"{h['nombre']} (éxito: {h['tasa_exito']:.0%}, {h['episodios']} episodios)"
                for h in habilidades_rl
                if h.get("tasa_exito", 0) >= 0.6
            ]

    return capacidades


def obtener_limitaciones() -> list:
    """Lista de limitaciones conocidas, incluyendo las del RL."""
    limitaciones = list(_LIMITACIONES_BASE)
    rl = cargar_aprendizaje_rl()

    if rl:
        for lim in rl.get("limitaciones_conocidas", []):
            limitaciones.append(f"en el entorno de simulación: {lim}")

    return limitaciones


def sabe_hacer(tarea: str) -> tuple:
    """
    Evalúa si la IA puede hacer una tarea.
    Retorna (puede_hacerlo: bool, explicacion: str)
    """
    tarea_lower = tarea.lower()
    capacidades = obtener_capacidades()

    # Buscar en todas las capacidades
    for categoria, lista in capacidades.items():
        for cap in lista:
            if any(palabra in tarea_lower for palabra in cap.lower().split()[:3]):
                return True, f"Sí puedo: {cap}"

    # Buscar en limitaciones
    for lim in obtener_limitaciones():
        if any(palabra in tarea_lower for palabra in lim.lower().split()[:3]):
            return False, f"Tengo limitaciones con esto: {lim}"

    return True, "Puedo intentarlo, aunque no tengo experiencia específica con eso."


def obtener_resumen_para_prompt() -> str:
    """Genera texto conciso para incluir en el prompt del sistema."""
    rl = cargar_aprendizaje_rl()
    lineas = []

    if rl:
        episodios = rl.get("total_episodios", 0)
        tasa = rl.get("tasa_exito_global", 0)
        if episodios > 0:
            lineas.append(
                f"He entrenado {episodios} episodios en mi entorno de simulación "
                f"con una tasa de éxito del {tasa:.0%}."
            )

        habilidades = [
            h["nombre"] for h in rl.get("habilidades_aprendidas", [])
            if h.get("tasa_exito", 0) >= 0.7
        ]
        if habilidades:
            lineas.append(f"Habilidades que domino: {', '.join(habilidades)}.")

        limitaciones_rl = rl.get("limitaciones_conocidas", [])
        if limitaciones_rl:
            lineas.append(
                f"Sé que me cuesta: {', '.join(limitaciones_rl[:2])}. "
                "Soy honesto cuando algo está fuera de mis capacidades actuales."
            )

    if not lineas:
        lineas.append(
            "Conozco mis capacidades y limitaciones. "
            "Si no puedo hacer algo, lo digo claramente en lugar de inventar."
        )

    return " ".join(lineas)
