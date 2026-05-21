"""
alisha_media.py — Detector de medios de Windows.

Lee los metadatos de la sesión de medios activa (Spotify, YouTube, etc.)
usando la API de Windows Media Control (winsdk).
Fail-silent: si falla, retorna None sin lanzar excepción.
"""
from __future__ import annotations
import asyncio
import threading
import time
from typing import Optional


# ── Estado compartido ─────────────────────────────────────────────────────────
_media_info: dict = {}   # {"title": ..., "artist": ..., "app": ...}
_last_update: float = 0.0
_UPDATE_INTERVAL = 5.0   # actualizar cada 5 segundos


def get_media_info() -> Optional[dict]:
    """Retorna info del medio activo o None si no hay nada."""
    if not _media_info:
        return None
    # Si la info tiene más de 30s, considerarla obsoleta
    if time.time() - _last_update > 30.0:
        return None
    return dict(_media_info)


def get_media_description() -> Optional[str]:
    """
    Retorna una descripción semántica del medio activo.
    Ej: "Spotify: 'Blinding Lights' de The Weeknd"
    """
    info = get_media_info()
    if not info:
        return None
    title  = info.get("title", "")
    artist = info.get("artist", "")
    app    = info.get("app", "")

    if title and artist:
        return f"{app}: '{title}' de {artist}"
    elif title:
        return f"{app}: '{title}'"
    return None


async def _fetch_media_async():
    """Obtiene metadatos de medios via Windows Media Control."""
    global _media_info, _last_update
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager
        )
        manager = await Manager.request_async()
        session = manager.get_current_session()
        if not session:
            _media_info = {}
            return

        info = await session.try_get_media_properties_async()
        if not info:
            _media_info = {}
            return

        # Obtener nombre de la app
        app_id = session.source_app_user_model_id or ""
        app_name = "Música"
        if "spotify" in app_id.lower():
            app_name = "Spotify"
        elif "chrome" in app_id.lower() or "msedge" in app_id.lower():
            app_name = "YouTube"
        elif "vlc" in app_id.lower():
            app_name = "VLC"

        _media_info = {
            "title":  info.title or "",
            "artist": info.artist or "",
            "album":  info.album_title or "",
            "app":    app_name,
        }
        _last_update = time.time()

    except Exception:
        _media_info = {}


def _update_loop():
    """Loop daemon que actualiza los metadatos cada 5 segundos."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(_fetch_media_async())
        except Exception:
            pass
        time.sleep(_UPDATE_INTERVAL)


# Iniciar el loop en background al importar el módulo
_thread = threading.Thread(target=_update_loop, daemon=True)
_thread.start()
