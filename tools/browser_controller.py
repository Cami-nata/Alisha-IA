"""
tools/browser_controller.py — Automatización del navegador con Playwright.

Funciones:
  - search_google(query)          → 5 resultados con título y URL
  - read_gmail()                  → últimos 10 emails
  - send_email(to, subject, body) → envía email via Gmail
  - search_drive(query)           → archivos recientes de Drive
  - get_calendar_events()         → eventos de hoy en Calendar
  - search_youtube(query)         → busca video en YouTube
  - play_youtube(url)             → reproduce video
  - get_youtube_transcript(url)   → transcripción del video
  - spotify_control(action)       → play/pause/next/prev/search

Principio fail-silent: toda excepción retorna string descriptivo, sin raise.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("BrowserController")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

# ── Playwright (opcional) ──────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False
    logger.warning("playwright no instalado. Instalar con: pip install playwright && playwright install chromium")


# ══════════════════════════════════════════════════════════════════════════════
# GESTOR DE BROWSER (singleton)
# ══════════════════════════════════════════════════════════════════════════════

class BrowserManager:
    """Gestiona una instancia persistente de Playwright/Chromium."""

    def __init__(self):
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def get_page(self, headless: bool = False) -> Optional[Page]:
        """Retorna una nueva página del browser. Inicia el browser si no está activo."""
        if not _PLAYWRIGHT_OK:
            return None
        try:
            if self._pw is None:
                self._pw = sync_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = self._pw.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="es-419",
            )
            return context.new_page()
        except Exception as e:
            logger.warning("Error al obtener página del browser: %s", e)
            return None

    def close(self):
        """Cierra el browser y Playwright."""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._pw:
                self._pw.stop()
                self._pw = None
        except Exception:
            pass


_manager = BrowserManager()


def _get_page(headless: bool = False) -> Optional[Page]:
    return _manager.get_page(headless=headless)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SEARCH (Req 3.1)
# ══════════════════════════════════════════════════════════════════════════════

def search_google(query: str) -> list[dict]:
    """
    Busca en Google y retorna los primeros 5 resultados.

    Returns:
        Lista de dicts con {"title": str, "url": str, "snippet": str}
        o lista vacía si falla.
    """
    try:
        page = _get_page(headless=True)
        if page is None:
            return [{"title": "Error", "url": "", "snippet": "Playwright no disponible"}]

        page.goto(f"https://www.google.com/search?q={query}&hl=es", timeout=15000)
        page.wait_for_load_state("domcontentloaded")

        results = []
        # Selectores de resultados orgánicos de Google
        items = page.query_selector_all("div.g")
        for item in items[:5]:
            try:
                title_el = item.query_selector("h3")
                link_el  = item.query_selector("a")
                snip_el  = item.query_selector("div.VwiC3b, span.aCOpRe")
                title   = title_el.inner_text() if title_el else ""
                url     = link_el.get_attribute("href") if link_el else ""
                snippet = snip_el.inner_text() if snip_el else ""
                if title and url:
                    results.append({"title": title, "url": url, "snippet": snippet})
            except Exception:
                continue

        page.context.close()
        logger.info("Google search '%s': %d resultados", query, len(results))
        return results if results else [{"title": "Sin resultados", "url": "", "snippet": ""}]

    except Exception as e:
        logger.warning("Error en search_google: %s", e)
        return [{"title": "Error", "url": "", "snippet": str(e)}]


# ══════════════════════════════════════════════════════════════════════════════
# GMAIL (Req 3.2, 3.3)
# ══════════════════════════════════════════════════════════════════════════════

def read_gmail() -> list[dict]:
    """
    Lee los últimos 10 emails del inbox de Gmail.
    Requiere estar logueado en Chrome con la cuenta de Google.

    Returns:
        Lista de dicts con {"from": str, "subject": str, "snippet": str}
    """
    try:
        page = _get_page(headless=False)  # headless=False para usar sesión guardada
        if page is None:
            return [{"from": "Error", "subject": "Playwright no disponible", "snippet": ""}]

        page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        emails = []
        # Filas de emails en la bandeja de entrada
        rows = page.query_selector_all("tr.zA")
        for row in rows[:10]:
            try:
                sender_el  = row.query_selector("span.zF")
                subject_el = row.query_selector("span.bog")
                snippet_el = row.query_selector("span.y2")
                sender  = sender_el.inner_text() if sender_el else "Desconocido"
                subject = subject_el.inner_text() if subject_el else "(sin asunto)"
                snippet = snippet_el.inner_text() if snippet_el else ""
                emails.append({"from": sender, "subject": subject, "snippet": snippet})
            except Exception:
                continue

        page.context.close()
        logger.info("Gmail: %d emails leídos", len(emails))
        return emails if emails else [{"from": "", "subject": "Bandeja vacía o no logueado", "snippet": ""}]

    except Exception as e:
        logger.warning("Error en read_gmail: %s", e)
        return [{"from": "Error", "subject": str(e), "snippet": ""}]


def send_email(to: str, subject: str, body: str) -> str:
    """
    Redacta y envía un email desde Gmail.

    Returns:
        Mensaje de éxito o error.
    """
    try:
        page = _get_page(headless=False)
        if page is None:
            return "Error: Playwright no disponible."

        page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        # Clic en "Redactar"
        compose_btn = page.query_selector("div.T-I.T-I-KE.L3")
        if not compose_btn:
            page.context.close()
            return "No se encontró el botón de redactar. ¿Estás logueado en Gmail?"

        compose_btn.click()
        page.wait_for_selector("div.aoD.hl", timeout=5000)

        # Destinatario
        to_field = page.query_selector("input[name='to']")
        if to_field:
            to_field.fill(to)
            to_field.press("Tab")

        # Asunto
        subject_field = page.query_selector("input[name='subjectbox']")
        if subject_field:
            subject_field.fill(subject)

        # Cuerpo
        body_field = page.query_selector("div[aria-label='Cuerpo del mensaje']")
        if body_field:
            body_field.click()
            body_field.fill(body)

        # Enviar
        send_btn = page.query_selector("div[data-tooltip='Enviar ‪(Ctrl-Intro)‬']")
        if not send_btn:
            send_btn = page.query_selector("div.T-I.J-J5-Ji.aoO.v7.T-I-atl.L3")
        if send_btn:
            send_btn.click()
            time.sleep(2)
            page.context.close()
            logger.info("Email enviado a %s: %s", to, subject)
            return f"✓ Email enviado a {to} con asunto '{subject}'."
        else:
            page.context.close()
            return "No se encontró el botón de enviar."

    except Exception as e:
        logger.warning("Error en send_email: %s", e)
        return f"Error al enviar email: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE (Req 3.4)
# ══════════════════════════════════════════════════════════════════════════════

def search_drive(query: str = "") -> list[dict]:
    """
    Lista archivos recientes de Google Drive.

    Returns:
        Lista de dicts con {"name": str, "url": str, "type": str}
    """
    try:
        page = _get_page(headless=False)
        if page is None:
            return [{"name": "Error", "url": "", "type": "Playwright no disponible"}]

        url = f"https://drive.google.com/drive/search?q={query}" if query else "https://drive.google.com/drive/recent"
        page.goto(url, timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        files = []
        items = page.query_selector_all("div[data-target='doc']")
        for item in items[:10]:
            try:
                name_el = item.query_selector("div.KF4T6b")
                link_el = item.query_selector("a")
                name = name_el.inner_text() if name_el else "Archivo"
                url  = link_el.get_attribute("href") if link_el else ""
                files.append({"name": name, "url": url, "type": "archivo"})
            except Exception:
                continue

        page.context.close()
        return files if files else [{"name": "Sin resultados", "url": "", "type": ""}]

    except Exception as e:
        logger.warning("Error en search_drive: %s", e)
        return [{"name": "Error", "url": "", "type": str(e)}]


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE CALENDAR (Req 3.5)
# ══════════════════════════════════════════════════════════════════════════════

def get_calendar_events() -> list[dict]:
    """
    Lee los eventos de hoy en Google Calendar.

    Returns:
        Lista de dicts con {"title": str, "time": str, "description": str}
    """
    try:
        page = _get_page(headless=False)
        if page is None:
            return [{"title": "Error", "time": "", "description": "Playwright no disponible"}]

        page.goto("https://calendar.google.com/calendar/r/day", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        events = []
        items = page.query_selector_all("div[data-eventid]")
        for item in items[:10]:
            try:
                title_el = item.query_selector("span.YoRZAb")
                time_el  = item.query_selector("span.gVNoLb")
                title = title_el.inner_text() if title_el else "Evento"
                t     = time_el.inner_text() if time_el else ""
                events.append({"title": title, "time": t, "description": ""})
            except Exception:
                continue

        page.context.close()
        return events if events else [{"title": "Sin eventos hoy", "time": "", "description": ""}]

    except Exception as e:
        logger.warning("Error en get_calendar_events: %s", e)
        return [{"title": "Error", "time": "", "description": str(e)}]


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE (Req 3.15, 3.16)
# ══════════════════════════════════════════════════════════════════════════════

def search_youtube(query: str) -> list[dict]:
    """
    Busca un video en YouTube.

    Returns:
        Lista de dicts con {"title": str, "url": str, "channel": str}
    """
    try:
        page = _get_page(headless=True)
        if page is None:
            return [{"title": "Error", "url": "", "channel": "Playwright no disponible"}]

        page.goto(f"https://www.youtube.com/results?search_query={query}", timeout=15000)
        page.wait_for_load_state("domcontentloaded")

        results = []
        items = page.query_selector_all("ytd-video-renderer")
        for item in items[:5]:
            try:
                title_el   = item.query_selector("a#video-title")
                channel_el = item.query_selector("ytd-channel-name a")
                title   = title_el.get_attribute("title") if title_el else ""
                href    = title_el.get_attribute("href") if title_el else ""
                channel = channel_el.inner_text() if channel_el else ""
                url     = f"https://www.youtube.com{href}" if href else ""
                if title:
                    results.append({"title": title, "url": url, "channel": channel})
            except Exception:
                continue

        page.context.close()
        return results if results else [{"title": "Sin resultados", "url": "", "channel": ""}]

    except Exception as e:
        logger.warning("Error en search_youtube: %s", e)
        return [{"title": "Error", "url": "", "channel": str(e)}]


def play_youtube(url: str) -> str:
    """
    Abre y reproduce un video de YouTube en el navegador.

    Returns:
        Mensaje de éxito o error.
    """
    try:
        page = _get_page(headless=False)
        if page is None:
            return "Error: Playwright no disponible."

        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded")

        # Intentar hacer clic en el botón de play
        try:
            play_btn = page.query_selector("button.ytp-play-button")
            if play_btn:
                play_btn.click()
        except Exception:
            pass

        logger.info("YouTube reproduciendo: %s", url)
        return f"✓ Reproduciendo: {url}"

    except Exception as e:
        logger.warning("Error en play_youtube: %s", e)
        return f"Error al reproducir YouTube: {e}"


def get_youtube_transcript(url: str) -> str:
    """
    Obtiene la transcripción de un video de YouTube.

    Returns:
        Texto de la transcripción o mensaje de error.
    """
    try:
        # Intentar con youtube-transcript-api primero (más confiable)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            # Extraer video ID de la URL
            video_id = ""
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]

            if not video_id:
                return "No se pudo extraer el ID del video."

            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["es", "en"])
            text = " ".join([t["text"] for t in transcript])
            return text[:3000]  # limitar a 3000 chars

        except ImportError:
            pass  # fallback a Playwright

        # Fallback: abrir YouTube y copiar transcripción via UI
        page = _get_page(headless=False)
        if page is None:
            return "Error: Playwright no disponible."

        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        # Buscar botón de transcripción en el menú "..."
        try:
            more_btn = page.query_selector("button[aria-label='Más acciones']")
            if more_btn:
                more_btn.click()
                time.sleep(1)
                transcript_btn = page.query_selector("yt-formatted-string:has-text('Abrir transcripción')")
                if transcript_btn:
                    transcript_btn.click()
                    time.sleep(2)
                    segments = page.query_selector_all("ytd-transcript-segment-renderer")
                    text = " ".join([s.inner_text() for s in segments])
                    page.context.close()
                    return text[:3000] if text else "Transcripción no disponible para este video."
        except Exception:
            pass

        page.context.close()
        return "Transcripción no disponible para este video."

    except Exception as e:
        logger.warning("Error en get_youtube_transcript: %s", e)
        return f"Error al obtener transcripción: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# SPOTIFY (Req 3.17)
# ══════════════════════════════════════════════════════════════════════════════

def spotify_control(action: str, query: str = "") -> str:
    """
    Controla Spotify Web Player.

    Args:
        action: "play", "pause", "next", "prev", "search"
        query:  Nombre de canción/artista (solo para "search")

    Returns:
        Mensaje de resultado.
    """
    try:
        page = _get_page(headless=False)
        if page is None:
            return "Error: Playwright no disponible."

        # Abrir Spotify Web si no está abierto
        page.goto("https://open.spotify.com", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        if action == "play":
            btn = page.query_selector("button[data-testid='control-button-playpause']")
            if btn:
                btn.click()
                page.context.close()
                return "▶ Reproduciendo en Spotify."

        elif action == "pause":
            btn = page.query_selector("button[data-testid='control-button-playpause']")
            if btn:
                btn.click()
                page.context.close()
                return "⏸ Pausado en Spotify."

        elif action == "next":
            btn = page.query_selector("button[data-testid='control-button-skip-forward']")
            if btn:
                btn.click()
                page.context.close()
                return "⏭ Siguiente canción en Spotify."

        elif action == "prev":
            btn = page.query_selector("button[data-testid='control-button-skip-back']")
            if btn:
                btn.click()
                page.context.close()
                return "⏮ Canción anterior en Spotify."

        elif action == "search" and query:
            search_input = page.query_selector("input[data-testid='search-input']")
            if not search_input:
                # Navegar a búsqueda
                page.goto("https://open.spotify.com/search", timeout=10000)
                page.wait_for_load_state("domcontentloaded")
                search_input = page.query_selector("input[data-testid='search-input']")

            if search_input:
                search_input.fill(query)
                search_input.press("Enter")
                time.sleep(2)
                # Clic en primer resultado
                first = page.query_selector("div[data-testid='tracklist-row']")
                if first:
                    first.dblclick()
                    page.context.close()
                    return f"🎵 Reproduciendo '{query}' en Spotify."

        page.context.close()
        return f"Acción '{action}' ejecutada en Spotify."

    except Exception as e:
        logger.warning("Error en spotify_control: %s", e)
        return f"Error al controlar Spotify: {e}"
