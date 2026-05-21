"""
State_Vector — generación y validación del State_Vector.
Parte del sistema de Conciencia Situacional de Alisha.
"""

import json
from collections import Counter
from datetime import datetime


# Campos requeridos del modelo de datos
_CAMPOS_REQUERIDOS = [
    "timestamp_inicio",
    "timestamp_fin",
    "duracion_minutos",
    "actividad_detectada",
    "apps_unicas",
    "titulo_mas_frecuente",
    "total_cambios_ventana",
    "cambios_ventana_por_minuto",
    "ritmo_escritura_promedio",
    "hora_del_dia",
    "bateria",
    "app_dominante",
]

_LIMITE_BYTES = 2048


def generar_state_vector(eventos: list[dict]) -> dict:
    """
    Genera un State_Vector a partir de una lista de eventos del Silent_Buffer.

    Args:
        eventos: Lista de eventos con estructura {timestamp, tipo, datos}.

    Returns:
        Diccionario con todos los campos del modelo de datos.
        Si la lista está vacía, retorna un dict con actividad_detectada=False
        y el resto de campos en valores neutros.
    """
    if not eventos:
        return _state_vector_vacio()

    # Filtrar solo eventos de tipo "contexto" y "teclado"
    eventos_contexto = [e for e in eventos if e.get("tipo") == "contexto"]
    eventos_teclado = [e for e in eventos if e.get("tipo") == "teclado"]

    # Calcular timestamps de inicio y fin
    timestamps = _extraer_timestamps(eventos)
    timestamp_inicio, timestamp_fin = timestamps[0], timestamps[-1]
    duracion_minutos = _calcular_duracion_minutos(timestamp_inicio, timestamp_fin)

    # Apps únicas y dominante
    apps_counter = _contar_apps(eventos_contexto)
    apps_unicas = list(apps_counter.keys())
    app_dominante = apps_counter.most_common(1)[0][0] if apps_counter else None

    # Título más frecuente
    titulo_mas_frecuente = _titulo_mas_frecuente(eventos_contexto)

    # Cambios de ventana
    total_cambios_ventana = _sumar_cambios_ventana(eventos_contexto)
    cambios_ventana_por_minuto = (
        round(total_cambios_ventana / duracion_minutos, 4)
        if duracion_minutos > 0
        else 0.0
    )

    # Ritmo de escritura promedio
    ritmo_escritura_promedio = _ritmo_escritura_promedio(eventos_contexto, eventos_teclado)

    # Hora del día (del último evento de contexto)
    hora_del_dia = _hora_del_dia(eventos_contexto, timestamp_fin)

    # Batería (último valor disponible)
    bateria = _ultima_bateria(eventos_contexto)

    sv = {
        "timestamp_inicio": timestamp_inicio,
        "timestamp_fin": timestamp_fin,
        "duracion_minutos": round(duracion_minutos, 4),
        "actividad_detectada": True,
        "apps_unicas": apps_unicas,
        "titulo_mas_frecuente": titulo_mas_frecuente,
        "total_cambios_ventana": total_cambios_ventana,
        "cambios_ventana_por_minuto": cambios_ventana_por_minuto,
        "ritmo_escritura_promedio": ritmo_escritura_promedio,
        "hora_del_dia": hora_del_dia,
        "bateria": bateria,
        "app_dominante": app_dominante,
    }

    return truncar_si_necesario(sv)


def es_identico(sv1: dict, sv2: dict) -> bool:
    """
    Compara dos State_Vectors por los campos clave.

    Retorna True si app_dominante, titulo_mas_frecuente y
    ritmo_escritura_promedio son idénticos en ambos.
    """
    campos = ("app_dominante", "titulo_mas_frecuente", "ritmo_escritura_promedio")
    return all(sv1.get(c) == sv2.get(c) for c in campos)


def truncar_si_necesario(sv: dict) -> dict:
    """
    Recorta apps_unicas y titulo_mas_frecuente hasta que
    json.dumps(sv) sea ≤ 2048 bytes.

    Retorna un nuevo dict (no modifica el original).
    """
    sv = dict(sv)

    # Truncar título primero (más agresivo en bytes)
    while len(json.dumps(sv, ensure_ascii=False).encode("utf-8")) > _LIMITE_BYTES:
        titulo = sv.get("titulo_mas_frecuente") or ""
        apps = sv.get("apps_unicas") or []

        if titulo and len(titulo) > 10:
            sv["titulo_mas_frecuente"] = titulo[: len(titulo) // 2]
        elif apps and len(apps) > 1:
            sv["apps_unicas"] = apps[:-1]
        elif titulo and len(titulo) > 0:
            sv["titulo_mas_frecuente"] = titulo[: max(1, len(titulo) - 1)]
        else:
            # Último recurso: vaciar ambos
            sv["titulo_mas_frecuente"] = ""
            sv["apps_unicas"] = []
            break

    return sv


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _state_vector_vacio() -> dict:
    """Retorna un State_Vector con actividad_detectada=False y valores neutros."""
    ahora = datetime.now().isoformat(timespec="seconds")
    return {
        "timestamp_inicio": ahora,
        "timestamp_fin": ahora,
        "duracion_minutos": 0,
        "actividad_detectada": False,
        "apps_unicas": [],
        "titulo_mas_frecuente": None,
        "total_cambios_ventana": 0,
        "cambios_ventana_por_minuto": 0.0,
        "ritmo_escritura_promedio": 0,
        "hora_del_dia": datetime.now().strftime("%H:%M"),
        "bateria": None,
        "app_dominante": None,
    }


def _extraer_timestamps(eventos: list[dict]) -> list[str]:
    """Extrae y ordena los timestamps de los eventos."""
    ts = [e.get("timestamp", "") for e in eventos if e.get("timestamp")]
    ts.sort()
    if not ts:
        ahora = datetime.now().isoformat(timespec="seconds")
        return [ahora, ahora]
    return ts


def _calcular_duracion_minutos(ts_inicio: str, ts_fin: str) -> float:
    """Calcula la duración en minutos entre dos timestamps ISO 8601."""
    try:
        inicio = datetime.fromisoformat(ts_inicio)
        fin = datetime.fromisoformat(ts_fin)
        delta = (fin - inicio).total_seconds()
        return max(delta / 60.0, 0.0)
    except Exception:
        return 0.0


def _contar_apps(eventos_contexto: list[dict]) -> Counter:
    """Cuenta la frecuencia de cada app activa en los eventos de contexto."""
    counter: Counter = Counter()
    for e in eventos_contexto:
        datos = e.get("datos") or {}
        app = datos.get("app_activa")
        if app:
            counter[app] += 1
    return counter


def _titulo_mas_frecuente(eventos_contexto: list[dict]) -> str | None:
    """Retorna el título de ventana más frecuente."""
    counter: Counter = Counter()
    for e in eventos_contexto:
        datos = e.get("datos") or {}
        titulo = datos.get("titulo_ventana")
        if titulo:
            counter[titulo] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _sumar_cambios_ventana(eventos_contexto: list[dict]) -> int:
    """Suma el total de cambios de ventana reportados en los eventos."""
    total = 0
    for e in eventos_contexto:
        datos = e.get("datos") or {}
        cambios = datos.get("cambios_ventana")
        if isinstance(cambios, (int, float)):
            total += int(cambios)
    return total


def _ritmo_escritura_promedio(
    eventos_contexto: list[dict], eventos_teclado: list[dict]
) -> float:
    """Calcula el ritmo de escritura promedio en teclas por minuto."""
    # Primero intentar desde eventos de tipo "teclado"
    ritmos_teclado = []
    for e in eventos_teclado:
        datos = e.get("datos") or {}
        tpm = datos.get("teclas_por_minuto")
        if isinstance(tpm, (int, float)):
            ritmos_teclado.append(float(tpm))

    if ritmos_teclado:
        return round(sum(ritmos_teclado) / len(ritmos_teclado), 4)

    # Fallback: desde campo teclas_por_minuto en eventos de contexto
    ritmos = []
    for e in eventos_contexto:
        datos = e.get("datos") or {}
        tpm = datos.get("teclas_por_minuto")
        if isinstance(tpm, (int, float)):
            ritmos.append(float(tpm))

    if ritmos:
        return round(sum(ritmos) / len(ritmos), 4)

    return 0


def _hora_del_dia(eventos_contexto: list[dict], timestamp_fin: str) -> str:
    """Retorna la hora del día del último evento de contexto o del timestamp_fin."""
    # Intentar desde el campo "hora" del último evento de contexto
    for e in reversed(eventos_contexto):
        datos = e.get("datos") or {}
        hora = datos.get("hora")
        if hora:
            return hora

    # Fallback: extraer del timestamp_fin
    try:
        dt = datetime.fromisoformat(timestamp_fin)
        return dt.strftime("%H:%M")
    except Exception:
        return datetime.now().strftime("%H:%M")


def _ultima_bateria(eventos_contexto: list[dict]) -> int | None:
    """Retorna el último nivel de batería disponible."""
    for e in reversed(eventos_contexto):
        datos = e.get("datos") or {}
        bateria = datos.get("bateria")
        if isinstance(bateria, (int, float)):
            return int(bateria)
    return None
