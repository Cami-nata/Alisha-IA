"""
news_bot.py — Agente secundario de noticias para Alisha.

Funciona en un hilo daemon independiente:
1. Lee el perfil de Camila desde MongoDB Atlas para saber sus intereses
2. Obtiene titulares de GNews API (gratuita) + RSS de Infobae como fallback
3. Filtra noticias relevantes según los intereses del perfil
4. Guarda los resúmenes en la colección `noticias` de MongoDB Atlas
5. Expone get_resumen_noticias() para que Alisha responda "¿Qué hay de nuevo?"

Dependencias: requests (ya en requirements.txt)
Opcional: beautifulsoup4 para parseo RSS (pip install beautifulsoup4)
"""
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger("news_bot")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# GNews API gratuita — 100 requests/día sin costo
# Obtené tu key en https://gnews.io (registro gratuito)
# Si no tenés key, el bot usa RSS de Infobae como fallback automático
GNEWS_API_KEY = ""  # Dejá vacío para usar solo RSS

GNEWS_URL = "https://gnews.io/api/v4/top-headlines"
GNEWS_LANG = "es"
GNEWS_COUNTRY = "ar"  # Argentina — noticias en español rioplatense
GNEWS_MAX = 10

# Fuentes RSS de fallback (no requieren API key)
RSS_FEEDS = [
    "https://www.infobae.com/feeds/rss/",
    "https://www.lanacion.com.ar/arc/outboundfeeds/rss/",
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
]

# Intervalo de actualización en segundos (cada 30 minutos)
INTERVALO_ACTUALIZACION = 30 * 60

# Máximo de noticias guardadas en Atlas por ciclo
MAX_NOTICIAS_GUARDAR = 5

# Intereses por defecto si el perfil no tiene gustos definidos
INTERESES_DEFAULT = [
    "tecnología", "programación", "python", "inteligencia artificial",
    "diseño", "argentina", "ciencia"
]

# ---------------------------------------------------------------------------
# Estado interno del bot
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_noticias_cache: list[dict] = []   # últimas noticias filtradas en memoria
_ultima_actualizacion: Optional[datetime] = None
_bot_activo = False


# ---------------------------------------------------------------------------
# Obtención de intereses desde el perfil
# ---------------------------------------------------------------------------

def _obtener_intereses() -> list[str]:
    """Lee los gustos del perfil de Camila desde MongoDB Atlas."""
    perfil = {}

    try:
        from mongodb_client import get_db
        db = get_db()
        if db:
            perfil = db.get_collection("perfil").find_one({"_id": "perfil_usuario"}) or {}
    except Exception:
        pass

    # Fallback: leer ia_memoria.json local
    if not perfil:
        try:
            import json
            from config import DATA_DIR
            data = json.loads((DATA_DIR / "ia_memoria.json").read_text(encoding="utf-8"))
            perfil = data.get("perfil", {})
        except Exception:
            pass

    # Extraer intereses de todos los campos del perfil
    intereses = set()

    for campo in ("gustos", "trabajo", "gustos_musicales"):
        valor = perfil.get(campo, "")
        if isinstance(valor, list):
            intereses.update(v.strip().lower() for v in valor if v.strip())
        elif isinstance(valor, str) and valor.strip():
            intereses.update(g.strip().lower() for g in valor.split(",") if g.strip())

    # Datos personales también pueden dar contexto (ej: ciudad para noticias locales)
    for dato in perfil.get("datos_personales", []):
        if len(dato) > 2:
            intereses.add(dato.lower().strip())

    return list(intereses) if intereses else INTERESES_DEFAULT


# ---------------------------------------------------------------------------
# Obtención de noticias — GNews API
# ---------------------------------------------------------------------------

def _fetch_gnews(intereses: list[str]) -> list[dict]:
    """Obtiene noticias de GNews API filtradas por intereses."""
    if not GNEWS_API_KEY:
        return []

    noticias = []
    # Buscar por los primeros 3 intereses para no agotar el cupo diario
    for interes in intereses[:3]:
        try:
            resp = requests.get(
                GNEWS_URL,
                params={
                    "q": interes,
                    "lang": GNEWS_LANG,
                    "country": GNEWS_COUNTRY,
                    "max": 5,
                    "apikey": GNEWS_API_KEY,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for art in data.get("articles", []):
                    noticias.append({
                        "titulo": art.get("title", ""),
                        "descripcion": art.get("description", ""),
                        "url": art.get("url", ""),
                        "fuente": art.get("source", {}).get("name", "GNews"),
                        "fecha": art.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                        "interes": interes,
                    })
        except Exception as e:
            logger.debug(f"GNews error para '{interes}': {e}")

    return noticias


# ---------------------------------------------------------------------------
# Obtención de noticias — RSS fallback
# ---------------------------------------------------------------------------

def _fetch_rss(intereses: list[str]) -> list[dict]:
    """Parsea feeds RSS de Infobae/LaNacion como fallback sin API key."""
    noticias = []

    # Intentar usar BeautifulSoup si está disponible
    try:
        from bs4 import BeautifulSoup
        _bs4_ok = True
    except ImportError:
        _bs4_ok = False

    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={
                "User-Agent": "AlishaNewsBot/1.0"
            })
            if resp.status_code != 200:
                continue

            if _bs4_ok:
                soup = BeautifulSoup(resp.content, "xml")
                items = soup.find_all("item")
            else:
                # Parseo manual básico con xml.etree si no hay bs4
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                ns = {"": ""}
                items_raw = root.findall(".//item")
                # Convertir a objetos con interfaz similar a bs4
                class _Item:
                    def __init__(self, el):
                        self._el = el
                    def find(self, tag):
                        found = self._el.find(tag)
                        return _TextWrapper(found.text if found is not None else "") if found is not None else None
                class _TextWrapper:
                    def __init__(self, text): self.text = text
                items = [_Item(i) for i in items_raw]

            for item in items[:20]:
                titulo_el = item.find("title")
                desc_el = item.find("description")
                link_el = item.find("link")
                pub_el = item.find("pubDate")

                titulo = titulo_el.text.strip() if titulo_el else ""
                descripcion = desc_el.text.strip() if desc_el else ""
                url = link_el.text.strip() if link_el else feed_url
                fecha = pub_el.text.strip() if pub_el else datetime.now(timezone.utc).isoformat()

                if not titulo:
                    continue

                # Filtrar por relevancia con los intereses
                texto_lower = (titulo + " " + descripcion).lower()
                interes_match = next(
                    (i for i in intereses if i in texto_lower), None
                )
                if interes_match or not intereses:
                    noticias.append({
                        "titulo": titulo,
                        "descripcion": descripcion[:300],
                        "url": url,
                        "fuente": feed_url.split("/")[2],  # dominio
                        "fecha": fecha,
                        "interes": interes_match or "general",
                    })

        except Exception as e:
            logger.debug(f"RSS error {feed_url}: {e}")

    return noticias


# ---------------------------------------------------------------------------
# Filtro de relevancia
# ---------------------------------------------------------------------------

def _filtrar_relevantes(noticias: list[dict], intereses: list[str]) -> list[dict]:
    """
    Puntúa cada noticia según cuántos intereses coinciden en título + descripción.
    Retorna las top MAX_NOTICIAS_GUARDAR ordenadas por relevancia.
    """
    puntuadas = []
    titulos_vistos = set()

    for n in noticias:
        titulo = n.get("titulo", "")
        # Deduplicar por título similar
        titulo_key = titulo[:50].lower()
        if titulo_key in titulos_vistos:
            continue
        titulos_vistos.add(titulo_key)

        texto = (titulo + " " + n.get("descripcion", "")).lower()
        puntos = sum(1 for i in intereses if i in texto)
        if puntos > 0 or n.get("interes") != "general":
            puntuadas.append((puntos, n))

    # Ordenar por puntuación descendente
    puntuadas.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in puntuadas[:MAX_NOTICIAS_GUARDAR]]


# ---------------------------------------------------------------------------
# Guardado en MongoDB Atlas
# ---------------------------------------------------------------------------

def _guardar_en_atlas(noticias: list[dict]) -> int:
    """
    Guarda las noticias en la colección `noticias` de Atlas.
    Evita duplicados por URL. Retorna cantidad guardada.
    TTL: las noticias se eliminan automáticamente después de 7 días.
    """
    if not noticias:
        return 0

    guardadas = 0
    try:
        from mongodb_client import get_db
        db = get_db()
        if not db:
            return 0

        col = db.get_collection("noticias")

        # Crear índice TTL de 7 días si no existe (se ignora si ya existe)
        try:
            col.create_index("fecha_expira", expireAfterSeconds=0)
        except Exception:
            pass

        for noticia in noticias:
            url = noticia.get("url", "")
            # Evitar duplicados: verificar si ya existe esta URL hoy
            existente = col.find_one({"url": url}) if url else None
            if existente:
                continue

            doc = {
                "tipo": "noticia",
                "fecha": datetime.now(timezone.utc).isoformat(),
                "fecha_expira": datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).replace(day=datetime.now(timezone.utc).day + 7),  # TTL 7 días
                "titulo": noticia.get("titulo", ""),
                "descripcion": noticia.get("descripcion", ""),
                "url": noticia.get("url", ""),
                "fuente": noticia.get("fuente", ""),
                "interes": noticia.get("interes", "general"),
                "leida": False,
            }
            col.insert_one(doc)
            guardadas += 1

    except Exception as e:
        logger.warning(f"Error guardando noticias en Atlas: {e}")

    return guardadas


# ---------------------------------------------------------------------------
# Ciclo principal del bot
# ---------------------------------------------------------------------------

def _ciclo_noticias() -> None:
    """Un ciclo completo: fetch → filtrar → guardar → actualizar caché."""
    global _noticias_cache, _ultima_actualizacion

    logger.info("[NewsBot] Iniciando ciclo de noticias...")
    intereses = _obtener_intereses()
    logger.info(f"[NewsBot] Intereses detectados: {intereses}")

    # Intentar GNews primero, RSS como fallback
    noticias_raw = _fetch_gnews(intereses)
    if not noticias_raw:
        logger.info("[NewsBot] GNews sin resultados, usando RSS...")
        noticias_raw = _fetch_rss(intereses)

    if not noticias_raw:
        logger.info("[NewsBot] No se obtuvieron noticias en este ciclo.")
        return

    # Filtrar por relevancia
    relevantes = _filtrar_relevantes(noticias_raw, intereses)
    logger.info(f"[NewsBot] {len(relevantes)} noticias relevantes de {len(noticias_raw)} totales.")

    # Guardar en Atlas
    guardadas = _guardar_en_atlas(relevantes)
    logger.info(f"[NewsBot] {guardadas} noticias nuevas guardadas en Atlas.")

    # Actualizar caché en memoria
    with _lock:
        _noticias_cache = relevantes
        _ultima_actualizacion = datetime.now()


def _loop_bot() -> None:
    """Loop daemon del bot — corre indefinidamente cada INTERVALO_ACTUALIZACION."""
    global _bot_activo
    _bot_activo = True

    # Primer ciclo con delay de 10s para no bloquear el arranque de Alisha
    time.sleep(10)

    while _bot_activo:
        try:
            _ciclo_noticias()
        except Exception as e:
            logger.error(f"[NewsBot] Error en ciclo: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def iniciar_bot() -> None:
    """Inicia el bot de noticias en un hilo daemon. Llamar desde main.py."""
    hilo = threading.Thread(target=_loop_bot, daemon=True, name="NewsBot")
    hilo.start()
    logger.info("[NewsBot] Hilo daemon iniciado.")


def detener_bot() -> None:
    """Detiene el loop del bot."""
    global _bot_activo
    _bot_activo = False


def get_resumen_noticias(max_noticias: int = 5) -> str:
    """
    Retorna un resumen de las últimas noticias relevantes para Alisha.
    Primero busca en Atlas, luego en el caché en memoria.
    Formato con voseo rioplatense para que Alisha lo use directamente.
    """
    noticias = _leer_desde_atlas(max_noticias)

    if not noticias:
        # Fallback al caché en memoria
        with _lock:
            noticias = _noticias_cache[:max_noticias]

    if not noticias:
        return (
            "Che, todavía no recolecté noticias. "
            "El bot arranca a los 10 segundos de que inicio y actualiza cada 30 minutos. "
            "¡Preguntame de nuevo en un ratito!"
        )

    # Construir resumen con toque personal de Alisha
    cuando = ""
    if _ultima_actualizacion:
        minutos = int((datetime.now() - _ultima_actualizacion).total_seconds() / 60)
        cuando = f" (actualizado hace {minutos} min)" if minutos < 60 else ""

    lineas = [f"¡Acá te traigo lo más importante de hoy{cuando}! 📰\n"]

    for i, n in enumerate(noticias, 1):
        titulo = n.get("titulo", "Sin título")
        desc = n.get("descripcion", "")
        fuente = n.get("fuente", "")
        interes = n.get("interes", "")

        # Truncar descripción larga
        if len(desc) > 120:
            desc = desc[:117] + "..."

        linea = f"{i}. **{titulo}**"
        if desc:
            linea += f"\n   {desc}"
        if fuente:
            linea += f"\n   — {fuente}"
        if interes and interes != "general":
            linea += f" · #{interes}"
        lineas.append(linea)

    lineas.append("\n¿Querés que te cuente más sobre alguna de estas?")
    return "\n".join(lineas)


def _leer_desde_atlas(max_noticias: int) -> list[dict]:
    """Lee las noticias más recientes desde la colección `noticias` de Atlas."""
    try:
        from mongodb_client import get_db
        db = get_db()
        if not db:
            return []

        col = db.get_collection("noticias")
        cursor = col.find({"leida": False}).sort("fecha", -1)
        docs = list(cursor)[:max_noticias]

        # Marcar como leídas
        for doc in docs:
            if "_id" in doc:
                try:
                    col.replace_one(
                        {"_id": doc["_id"]},
                        {**doc, "leida": True}
                    )
                except Exception:
                    pass
            doc.pop("_id", None)

        return docs

    except Exception as e:
        logger.debug(f"Error leyendo noticias de Atlas: {e}")
        return []


def forzar_actualizacion() -> str:
    """Fuerza un ciclo inmediato. Útil para testing o si el usuario lo pide."""
    try:
        _ciclo_noticias()
        with _lock:
            n = len(_noticias_cache)
        return f"Actualización forzada completada. {n} noticias en caché."
    except Exception as e:
        return f"Error al forzar actualización: {e}"
