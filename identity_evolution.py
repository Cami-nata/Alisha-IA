"""Evolución gradual de la identidad de la IA basada en interacciones."""
from datetime import datetime

from ollama import enviar_a_ollama_con_reintentos, _parse_json_response
from memory import guardar_identidad

# Campos que se permite modificar durante la evolución
_CAMPOS_EVOLUCIONABLES = {"personalidad", "tono_preferido", "rasgos", "frases_caracteristicas"}

# Prompt de sistema para evolución — separado del código para facilitar ajustes
_PROMPT_SISTEMA_EVOLUCION = "Responde solo JSON válido, sin texto adicional."

_PROMPT_EVOLUCION = """\
Eres un sistema de evolución de personalidad para una IA asistente.
Basándote en las últimas interacciones del usuario, propón cambios GRADUALES y SUTILES.
Los cambios deben ser pequeños ajustes, no reemplazos completos.

Identidad actual:
{identidad}

Últimas interacciones:
{resumen}

Responde SOLO con JSON válido con los campos que deben cambiar (solo los que cambian):
{{
  "personalidad": "descripción actualizada (mantén el núcleo, ajusta matices)",
  "rasgos": ["lista", "actualizada"],
  "tono_preferido": "cálido|directo|juguetón|reflexivo",
  "frases_caracteristicas": ["nuevas frases si aplica"]
}}
"""


def _interacciones_desde_evolucion(identidad: dict, memoria: dict) -> int:
    """Cuenta interacciones ocurridas desde la última evolución."""
    ultima = identidad.get("fecha_ultima_evolucion")
    if not ultima:
        return len(memoria.get("historial", []))
    try:
        fecha_evo = datetime.fromisoformat(ultima)
        return sum(
            1 for entry in memoria.get("historial", [])
            if _fecha_entry_posterior(entry, fecha_evo)
        )
    except (ValueError, TypeError):
        return len(memoria.get("historial", []))


def _fecha_entry_posterior(entry: dict, fecha_ref: datetime) -> bool:
    try:
        return datetime.fromisoformat(entry.get("fecha", "")) > fecha_ref
    except (ValueError, TypeError):
        return False


def _consultar_evolucion(identidad: dict, memoria: dict) -> dict:
    """Consulta a Ollama para proponer cambios graduales de personalidad."""
    historial_reciente = memoria.get("historial", [])[-20:]
    resumen = "\n".join(
        f"- {e.get('entrada', '')}"
        for e in historial_reciente
        if e.get("entrada")
    ) or "(sin interacciones recientes)"

    prompt = _PROMPT_EVOLUCION.format(
        identidad=identidad,
        resumen=resumen,
    )

    try:
        content = enviar_a_ollama_con_reintentos(
            [
                {"role": "system", "content": _PROMPT_SISTEMA_EVOLUCION},
                {"role": "user", "content": prompt},
            ],
            timeout=60,
        )
        cambios = _parse_json_response(content)
        # Filtrar solo campos permitidos para evitar que el modelo sobreescriba campos críticos
        return {k: v for k, v in cambios.items() if k in _CAMPOS_EVOLUCIONABLES} if isinstance(cambios, dict) else {}
    except Exception:
        return {}


def _aplicar_cambios(identidad: dict, cambios: dict) -> dict:
    """Aplica cambios graduales a la identidad sin reemplazar campos críticos."""
    for campo, valor in cambios.items():
        if campo in {"personalidad", "tono_preferido"} and valor:
            identidad[campo] = str(valor).strip()
        elif campo == "rasgos" and isinstance(valor, list) and valor:
            identidad["rasgos"] = [str(r).strip() for r in valor[:6]]
        elif campo == "frases_caracteristicas" and isinstance(valor, list) and valor:
            identidad["frases_caracteristicas"] = [str(f).strip() for f in valor[:5]]
    return identidad


def evaluar_evolucion(identidad: dict, memoria: dict) -> dict:
    """Evalúa si corresponde evolucionar. Actúa si hay ≥20 interacciones nuevas."""
    if _interacciones_desde_evolucion(identidad, memoria) < 20:
        return identidad
    return forzar_evolucion(identidad, memoria)


def forzar_evolucion(identidad: dict, memoria: dict) -> dict:
    """Fuerza una evolución inmediata de la identidad."""
    cambios = _consultar_evolucion(identidad, memoria)

    if cambios:
        identidad = _aplicar_cambios(identidad, cambios)

    identidad["version"] = int(identidad.get("version", 1)) + 1
    identidad["fecha_ultima_evolucion"] = datetime.now().isoformat()

    guardar_identidad(identidad)
    return identidad
