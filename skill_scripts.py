"""Librería de capacidades fundamentales para el asistente."""

import math
import os
import random
import shutil
import time
import webbrowser
from pathlib import Path
from typing import Any

import pyautogui

from actions import click_xy, doble_click_xy, abrir_web

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


def abrir_canva() -> str:
    abrir_web("https://www.canva.com")
    return "Abriendo Canva en el navegador."


def buscar_plantilla(query: str = "presentación") -> str:
    buscar = query.strip().replace(" ", "%20")
    abrir_web(f"https://www.canva.com/templates/search/{buscar}")
    return f"Buscando plantillas para '{query}' en Canva."


def clic_en_coordenada(x: int, y: int) -> str:
    mover_mouse_curvo(x, y)
    click_xy(x, y)
    return f"Clic realizado en la coordenada ({x}, {y})."


def organizar_ventanas_mosaico() -> str:
    try:
        # Windows: hacer mosaico con los atajos nativos
        pyautogui.hotkey("win", "left")
        time.sleep(0.2)
        pyautogui.hotkey("win", "right")
        time.sleep(0.2)
        pyautogui.hotkey("win", "up")
        return "Intenté organizar las ventanas en mosaico. Ajustá manualmente si es necesario."
    except Exception as e:
        return f"No pude organizar las ventanas automáticamente: {e}"


def organizar_escritorio_por_temas() -> str:
    """Organiza archivos del Escritorio en carpetas por tema simple."""
    desktop = Path.home() / "Desktop"
    if not desktop.exists() or not desktop.is_dir():
        return "No encontré el Escritorio."

    carpetas = {
        "Proyectos": ["py", "ipynb", "js", "html", "css", "md"],
        "Documentos": ["pdf", "docx", "txt", "xlsx", "pptx"],
        "Imagenes": ["png", "jpg", "jpeg", "gif", "webp"],
        "Descargas": ["zip", "rar", "7z", "exe"],
        "Notas": ["txt", "md"],
        "Diseño": ["svg", "psd", "ai", "fig"],
    }

    movidos = 0
    for item in desktop.iterdir():
        if item.name.startswith(".") or item.is_dir():
            continue
        ext = item.suffix.lower().lstrip(".")
        carpeta = None
        for nombre, extensiones in carpetas.items():
            if ext in extensiones:
                carpeta = desktop / nombre
                break
        if carpeta is None:
            continue
        carpeta.mkdir(exist_ok=True)
        try:
            shutil.move(str(item), str(carpeta / item.name))
            movidos += 1
        except Exception:
            pass

    if movidos:
        return f"Organicé {movidos} archivos del Escritorio en carpetas por tema." \
               "Revisá las nuevas carpetas si querés mover más cosas manualmente."
    return "No encontré archivos compatibles para organizar en el Escritorio."


def detectar_error_pantalla() -> str:
    nombre = "pantalla_error.png"
    try:
        pyautogui.screenshot(nombre)
    except Exception as e:
        return f"No pude capturar la pantalla: {e}"

    try:
        import pytesseract  # type: ignore[import]
        from PIL import Image
    except ImportError:
        return (
            "Capturé la pantalla, pero no pude analizarla porque falta pytesseract/Pillow. "
            f"La imagen quedó guardada en {nombre}."
        )

    try:
        imagen = Image.open(nombre)
        texto = pytesseract.image_to_string(imagen, lang="spa+eng")
        if texto.strip():
            return f"Detecté texto en pantalla. Podría haber un error visible: {texto.strip()[:240]}"
        return f"No encontré texto claro en la pantalla. Captura guardada en {nombre}."
    except Exception as e:
        return f"No pude analizar la captura: {e}"


def mover_mouse_curvo(x: int, y: int, duracion: float = 0.6, pasos: int = 30, energia: float = 1.0) -> str:
    origen_x, origen_y = pyautogui.position()
    if origen_x == x and origen_y == y:
        return "El cursor ya está en esa posición."

    duracion = duracion * max(1.0, 1.4 - energia)
    jitter = 0.0
    if energia < 0.4:
        jitter = 1.8 - energia * 3.0

    control_x = (origen_x + x) / 2 + (origen_y - y) * 0.2 + random.uniform(-jitter, jitter)
    control_y = (origen_y + y) / 2 + (x - origen_x) * 0.2 + random.uniform(-jitter, jitter)

    def punto_bezier(t: float) -> tuple[float, float]:
        a = (1 - t) ** 2
        b = 2 * (1 - t) * t
        c = t ** 2
        px = a * origen_x + b * control_x + c * x
        py = a * origen_y + b * control_y + c * y
        return px, py

    for i in range(1, pasos + 1):
        t = i / pasos
        px, py = punto_bezier(t)
        pyautogui.moveTo(px, py, duration=duracion / pasos)
    return f"Movimiento curvo completado hacia ({x}, {y})."


def abrir_ventana_nueva_app(nombre_app: str) -> str:
    try:
        abrir_web(nombre_app)
        return f"Solicité abrir: {nombre_app}."
    except Exception as e:
        return f"No pude abrir {nombre_app}: {e}"
