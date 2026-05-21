"""
profile_learner.py — Aprendizaje automático del perfil de Camila.

Alisha extrae variables del perfil directamente de la conversación,
sin que el usuario tenga que usar comandos especiales.

Detecta y guarda:
- Nombre del usuario
- Gustos, hobbies e intereses
- Estado de ánimo actual
- Trabajo / profesión / proyectos
- Preferencias de música, comida, etc.
- Datos personales relevantes (cumpleaños, ciudad, etc.)

Todo se persiste en MongoDB Atlas y en ia_memoria.json como fallback.
"""
import re
import threading
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Patrones de extracción — sin comandos, solo lenguaje natural
# ---------------------------------------------------------------------------

# Nombre del usuario
_PATRONES_NOMBRE = [
    r"(?:me llamo|soy|mi nombre es|llamame|llamá(?:me)?)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,20})",
    r"(?:soy|me llamo)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,20})",
]

# Gustos e intereses
_PATRONES_GUSTOS = [
    r"(?:me gusta(?:n)?|amo|adoro|me encanta(?:n)?|soy fan de|me apasiona(?:n)?)\s+(?:el |la |los |las |hacer |jugar |ver |escuchar )?(.{3,60}?)(?:\.|,|$|\n)",
    r"(?:mi hobby es|mis hobbies son|me dedico a|practico)\s+(.{3,60}?)(?:\.|,|$|\n)",
    r"(?:estoy aprendiendo|quiero aprender|me interesa(?:n)?)\s+(.{3,60}?)(?:\.|,|$|\n)",
]

# Estado de ánimo
_PATRONES_ESTADO = [
    r"(?:estoy|me siento|hoy estoy|ando)\s+(bien|mal|cansad[ao]|feliz|triste|estresad[ao]|ansios[ao]|motivad[ao]|aburrido|emocionad[ao]|nervios[ao])",
    r"(?:tuve un día|fue un día)\s+(bueno|malo|largo|difícil|genial|horrible|tranquilo)",
]

# Trabajo / proyectos
_PATRONES_TRABAJO = [
    r"(?:trabajo(?:ndo)? (?:en|de|como)|soy|me dedico a)\s+(.{3,60}?)(?:\.|,|$|\n)",
    r"(?:mi proyecto|estoy haciendo|estoy desarrollando|estoy creando)\s+(?:se llama |es )?\s*(.{3,60}?)(?:\.|,|$|\n)",
]

# Música
_PATRONES_MUSICA = [
    r"(?:escucho|me gusta(?:n)? la música de|mi artista favorito es|mi banda favorita es)\s+(.{3,50}?)(?:\.|,|$|\n)",
]

# Datos personales
_PATRONES_PERSONALES = [
    r"(?:mi cumpleaños es|nací el|cumplo años el)\s+(.{3,30}?)(?:\.|,|$|\n)",
    r"(?:vivo en|soy de|estoy en)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{2,30}?)(?:\.|,|$|\n)",
]

# Palabras a ignorar (demasiado genéricas)
_IGNORAR = {
    "eso", "esto", "algo", "nada", "todo", "mucho", "poco", "bien", "mal",
    "hacer", "ver", "ir", "estar", "ser", "tener", "poder", "querer",
    "la", "el", "los", "las", "un", "una", "unos", "unas",
}

# ---------------------------------------------------------------------------
# Extractor principal
# ---------------------------------------------------------------------------

def extraer_variables_perfil(texto: str) -> dict:
    """
    Analiza un texto de conversación y extrae variables del perfil.
    Retorna un dict con los campos detectados (solo los que encontró).
    """
    texto_lower = texto.lower().strip()
    resultado = {}

    # Nombre
    for patron in _PATRONES_NOMBRE:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            nombre = m.group(1).strip().title()
            if len(nombre) >= 3 and nombre.lower() not in _IGNORAR:
                resultado["nombre"] = nombre
                break

    # Gustos
    gustos_encontrados = []
    for patron in _PATRONES_GUSTOS:
        for m in re.finditer(patron, texto_lower, re.IGNORECASE):
            gusto = m.group(1).strip().rstrip(".,;")
            if len(gusto) >= 3 and gusto not in _IGNORAR and len(gusto) < 60:
                gustos_encontrados.append(gusto)
    if gustos_encontrados:
        resultado["gustos_nuevos"] = gustos_encontrados

    # Estado de ánimo
    for patron in _PATRONES_ESTADO:
        m = re.search(patron, texto_lower, re.IGNORECASE)
        if m:
            resultado["estado"] = m.group(1).strip()
            break

    # Trabajo / proyectos
    for patron in _PATRONES_TRABAJO:
        m = re.search(patron, texto_lower, re.IGNORECASE)
        if m:
            trabajo = m.group(1).strip().rstrip(".,;")
            if len(trabajo) >= 4 and trabajo not in _IGNORAR:
                resultado["trabajo"] = trabajo
                break

    # Música
    for patron in _PATRONES_MUSICA:
        m = re.search(patron, texto_lower, re.IGNORECASE)
        if m:
            musica = m.group(1).strip().rstrip(".,;")
            if len(musica) >= 2:
                resultado["musica"] = musica
                break

    # Datos personales
    for patron in _PATRONES_PERSONALES:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            dato = m.group(1).strip().rstrip(".,;")
            if len(dato) >= 3:
                resultado["dato_personal"] = dato
                break

    return resultado


# ---------------------------------------------------------------------------
# Aplicador al perfil
# ---------------------------------------------------------------------------

def actualizar_perfil_desde_conversacion(
    memoria: dict,
    entrada_usuario: str,
    respuesta_ia: str = "",
) -> tuple[dict, list[str]]:
    """
    Extrae variables del mensaje del usuario y las aplica al perfil.
    Retorna (memoria_actualizada, lista_de_cambios_detectados).

    Los cambios se pueden usar para que Alisha confirme lo que aprendió.
    """
    variables = extraer_variables_perfil(entrada_usuario)
    if not variables:
        return memoria, []

    perfil = memoria.setdefault("perfil", {"nombre": None, "gustos": "", "estado": None})
    cambios = []

    # Nombre
    if "nombre" in variables and not perfil.get("nombre"):
        perfil["nombre"] = variables["nombre"]
        cambios.append(f"nombre: {variables['nombre']}")

    # Gustos — acumular sin duplicar
    if "gustos_nuevos" in variables:
        gustos_actuales = set(
            g.strip().lower()
            for g in (perfil.get("gustos") or "").split(",")
            if g.strip()
        )
        nuevos = []
        for g in variables["gustos_nuevos"]:
            g_norm = g.lower().strip()
            if g_norm not in gustos_actuales and len(g_norm) >= 3:
                gustos_actuales.add(g_norm)
                nuevos.append(g)

        if nuevos:
            gustos_lista = [g for g in (perfil.get("gustos") or "").split(",") if g.strip()]
            gustos_lista.extend(nuevos)
            perfil["gustos"] = ", ".join(gustos_lista)
            cambios.append(f"gustos: {', '.join(nuevos)}")

    # Estado de ánimo
    if "estado" in variables:
        perfil["estado"] = variables["estado"]
        perfil["ultima_actualizacion_estado"] = datetime.now().isoformat()
        cambios.append(f"estado: {variables['estado']}")

    # Trabajo
    if "trabajo" in variables:
        perfil["trabajo"] = variables["trabajo"]
        cambios.append(f"trabajo: {variables['trabajo']}")

    # Música
    if "musica" in variables:
        musica_actual = perfil.get("gustos_musicales", "")
        if variables["musica"].lower() not in musica_actual.lower():
            perfil["gustos_musicales"] = (
                f"{musica_actual}, {variables['musica']}" if musica_actual
                else variables["musica"]
            )
            cambios.append(f"música: {variables['musica']}")

    # Dato personal
    if "dato_personal" in variables:
        perfil.setdefault("datos_personales", [])
        dato = variables["dato_personal"]
        if dato not in perfil["datos_personales"]:
            perfil["datos_personales"].append(dato)
            cambios.append(f"dato personal: {dato}")

    # Persistir si hubo cambios
    if cambios:
        _persistir_perfil_async(memoria, perfil)

    return memoria, cambios


def _persistir_perfil_async(memoria: dict, perfil: dict) -> None:
    """Guarda el perfil en background para no bloquear la respuesta."""
    def _guardar():
        try:
            from memory import guardar_perfil
            guardar_perfil(memoria, nombre=perfil.get("nombre"), gustos=perfil.get("gustos"))
        except Exception:
            pass
        # También actualizar gustos_musicales y trabajo si existen
        try:
            from mongodb_client import get_db
            db = get_db()
            if db:
                db.get_collection("perfil").replace_one(
                    {"_id": "perfil_usuario"},
                    {"_id": "perfil_usuario", **perfil},
                    upsert=True,
                )
        except Exception:
            pass

    threading.Thread(target=_guardar, daemon=True, name="ProfileSaver").start()


# ---------------------------------------------------------------------------
# Enriquecedor del prompt — inyecta el perfil completo en el contexto
# ---------------------------------------------------------------------------

def construir_contexto_perfil(perfil: dict) -> str:
    """
    Genera un bloque de texto con todo lo que Alisha sabe de Camila,
    para incluirlo en el prompt del sistema.
    """
    lineas = []

    if perfil.get("nombre"):
        lineas.append(f"Se llama {perfil['nombre']}.")

    if perfil.get("gustos"):
        lineas.append(f"Le gusta: {perfil['gustos']}.")

    if perfil.get("trabajo"):
        lineas.append(f"Trabaja/estudia en: {perfil['trabajo']}.")

    if perfil.get("gustos_musicales"):
        lineas.append(f"Escucha: {perfil['gustos_musicales']}.")

    if perfil.get("datos_personales"):
        lineas.append(f"Datos personales: {', '.join(perfil['datos_personales'])}.")

    if perfil.get("estado"):
        lineas.append(f"Hoy se siente: {perfil['estado']}.")

    return "\n".join(lineas) if lineas else "Todavía no sé mucho sobre ella, pero voy aprendiendo."
