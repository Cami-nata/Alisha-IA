"""
agent_actions.py — Acciones autónomas de la IA agente.

Capacidades:
- Crear, leer y editar archivos de código
- Abrir VS Code y escribir en él
- Edición de video con MoviePy
- Automatización de escritorio avanzada
"""
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pyautogui

# ---------------------------------------------------------------------------
# VS Code
# ---------------------------------------------------------------------------

def abrir_vscode(ruta: Optional[str] = None) -> str:
    """Abre VS Code, opcionalmente con un archivo o carpeta."""
    try:
        cmd = ["code"]
        if ruta:
            cmd.append(ruta)
        subprocess.Popen(cmd, shell=False,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(2)
        return f"VS Code abierto{f' con {ruta}' if ruta else ''}."
    except Exception as e:
        return f"Error abriendo VS Code: {e}"


def crear_archivo_codigo(ruta: str, contenido: str) -> str:
    """Crea un archivo de código con el contenido dado."""
    try:
        path = Path(ruta)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contenido, encoding="utf-8")
        return f"Archivo creado: {ruta}"
    except Exception as e:
        return f"Error creando archivo: {e}"


def leer_archivo(ruta: str) -> str:
    """Lee el contenido de un archivo."""
    try:
        return Path(ruta).read_text(encoding="utf-8", errors="ignore")[:5000]
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def editar_archivo(ruta: str, buscar: str, reemplazar: str) -> str:
    """Reemplaza texto en un archivo."""
    try:
        path = Path(ruta)
        contenido = path.read_text(encoding="utf-8")
        if buscar not in contenido:
            return f"No se encontró '{buscar}' en {ruta}"
        nuevo = contenido.replace(buscar, reemplazar, 1)
        path.write_text(nuevo, encoding="utf-8")
        return f"Archivo editado: {ruta}"
    except Exception as e:
        return f"Error editando archivo: {e}"


def escribir_en_vscode(codigo: str, delay: float = 0.03) -> str:
    """
    Escribe código en VS Code con efecto de tipeo.
    Asume que VS Code está abierto y en foco.
    """
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd)
        if "visual studio code" not in titulo.lower():
            return "VS Code no está en foco. Abrilo primero."
    except Exception:
        pass

    try:
        # Escribir línea por línea para mayor control
        lineas = codigo.split("\n")
        for i, linea in enumerate(lineas):
            pyautogui.write(linea, interval=delay)
            if i < len(lineas) - 1:
                pyautogui.press("enter")
            time.sleep(0.05)
        return "Código escrito en VS Code."
    except Exception as e:
        return f"Error escribiendo en VS Code: {e}"


# ---------------------------------------------------------------------------
# MoviePy — Edición de video
# ---------------------------------------------------------------------------

def _check_moviepy() -> bool:
    try:
        import moviepy
        return True
    except ImportError:
        return False


def cortar_video(entrada: str, salida: str, inicio: float, fin: float) -> str:
    """Corta un clip de video entre inicio y fin (en segundos)."""
    if not _check_moviepy():
        return "MoviePy no está instalado. Ejecutá: pip install moviepy"
    try:
        from moviepy.editor import VideoFileClip
        with VideoFileClip(entrada) as clip:
            subclip = clip.subclip(inicio, fin)
            subclip.write_videofile(salida, logger=None)
        return f"Video cortado guardado en: {salida}"
    except Exception as e:
        return f"Error cortando video: {e}"


def unir_videos(archivos: list[str], salida: str) -> str:
    """Une múltiples clips de video en uno."""
    if not _check_moviepy():
        return "MoviePy no está instalado."
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        clips = [VideoFileClip(f) for f in archivos]
        final = concatenate_videoclips(clips)
        final.write_videofile(salida, logger=None)
        for c in clips:
            c.close()
        return f"Videos unidos en: {salida}"
    except Exception as e:
        return f"Error uniendo videos: {e}"


def agregar_audio_video(video: str, audio: str, salida: str) -> str:
    """Agrega o reemplaza el audio de un video."""
    if not _check_moviepy():
        return "MoviePy no está instalado."
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        with VideoFileClip(video) as v:
            with AudioFileClip(audio) as a:
                final = v.set_audio(a)
                final.write_videofile(salida, logger=None)
        return f"Audio agregado. Video guardado en: {salida}"
    except Exception as e:
        return f"Error agregando audio: {e}"


def extraer_audio(video: str, salida: str) -> str:
    """Extrae el audio de un video."""
    if not _check_moviepy():
        return "MoviePy no está instalado."
    try:
        from moviepy.editor import VideoFileClip
        with VideoFileClip(video) as v:
            v.audio.write_audiofile(salida, logger=None)
        return f"Audio extraído en: {salida}"
    except Exception as e:
        return f"Error extrayendo audio: {e}"


# ---------------------------------------------------------------------------
# Ejecutor de acciones desde el JSON de la IA
# ---------------------------------------------------------------------------

def ejecutar_accion_agente(accion: dict) -> str:
    """
    Ejecuta una acción de agente basada en el dict de la IA.
    Acciones soportadas: crear_archivo, leer_archivo, editar_archivo,
    abrir_vscode, escribir_vscode, cortar_video, unir_videos, agregar_audio
    """
    tipo = accion.get("accion_agente", "")

    if tipo == "crear_archivo":
        return crear_archivo_codigo(
            accion.get("ruta", "nuevo_archivo.py"),
            accion.get("contenido", "")
        )
    elif tipo == "leer_archivo":
        return leer_archivo(accion.get("ruta", ""))
    elif tipo == "editar_archivo":
        return editar_archivo(
            accion.get("ruta", ""),
            accion.get("buscar", ""),
            accion.get("reemplazar", "")
        )
    elif tipo == "abrir_vscode":
        return abrir_vscode(accion.get("ruta"))
    elif tipo == "escribir_vscode":
        return escribir_en_vscode(accion.get("codigo", ""))
    elif tipo == "cortar_video":
        return cortar_video(
            accion.get("entrada", ""),
            accion.get("salida", "output.mp4"),
            float(accion.get("inicio", 0)),
            float(accion.get("fin", 10))
        )
    elif tipo == "unir_videos":
        return unir_videos(
            accion.get("archivos", []),
            accion.get("salida", "output.mp4")
        )
    elif tipo == "agregar_audio":
        return agregar_audio_video(
            accion.get("video", ""),
            accion.get("audio", ""),
            accion.get("salida", "output.mp4")
        )
    else:
        return f"Acción de agente desconocida: {tipo}"
