"""
screen_context.py — Contexto de pantalla inteligente.

Detecta si un mensaje requiere screenshot y provee contexto ligero
(título de ventana activa) sin tomar capturas innecesarias.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import pyautogui

# Palabras clave que implican necesidad de ver la pantalla
PALABRAS_VISION = {
    "qué hay",
    "qué ves",
    "qué dice",
    "qué muestra",
    "captura",
    "screenshot",
    "pantalla",
    "dónde está",
    "puedes ver",
    "mira",
    "observa",
    "describe lo que",
    "qué está abierto",
    "qué ventana",
}


def necesita_screenshot(mensaje: str) -> bool:
    """True si el mensaje implica necesidad de ver la pantalla.

    Función pura y determinista: no modifica estado global.
    """
    if not mensaje:
        return False
    texto = mensaje.strip().lower()
    return any(palabra in texto for palabra in PALABRAS_VISION)


def _obtener_ventana_activa() -> tuple[str, str]:
    """Retorna (titulo_ventana, nombre_proceso) usando win32gui si está disponible."""
    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd) or "Desconocido"

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            proceso = proc.name()
        except Exception:
            proceso = "Desconocido"

        return titulo, proceso
    except ImportError:
        pass

    # Fallback sin pywin32
    return "Desconocido", "Desconocido"


TMP_SCREENSHOT_DIR = Path(__file__).parent / "static" / "tmp"
TMP_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def obtener_contexto_pantalla(tomar_screenshot: bool = True) -> dict:
    """Retorna contexto de pantalla y guarda un screenshot temporal.

    El origen (0,0) corresponde a la esquina superior izquierda.
    """
    ventana, proceso = _obtener_ventana_activa()
    resolucion = pyautogui.size()

    ruta_screenshot: Optional[str] = None
    if tomar_screenshot:
        nombre = datetime.now().strftime("pantalla_%Y%m%d_%H%M%S.png")
        path = TMP_SCREENSHOT_DIR / nombre
        pyautogui.screenshot(str(path))
        ruta_screenshot = str(path)

    return {
        "ventana_activa": ventana,
        "proceso_activo": proceso,
        "screenshot": ruta_screenshot,
        "resolucion": (resolucion.width, resolucion.height),
        "origen_coordenadas": "esquina superior izquierda",
    }


def evaluar_escritorio() -> dict[str, object]:
    """Evalúa si el escritorio parece desordenado y cuántos archivos hay."""
    desktop = Path.home() / "Desktop"
    if not desktop.exists() or not desktop.is_dir():
        return {"desordenado": False, "cantidad": 0}

    items = [p for p in desktop.iterdir() if not p.name.startswith(".")]
    cantidad = len(items)
    return {
        "desordenado": cantidad >= 18,
        "cantidad": cantidad,
        "archivos": [p.name for p in items[:20]],
    }
