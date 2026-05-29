"""
screen_vision.py — Visión de pantalla en tiempo real.

Permite a la IA:
- Capturar la pantalla completa o una ventana específica
- Leer el contenido de VS Code via accesibilidad o clipboard
- Detectar qué está haciendo el usuario
- Observar cambios en la ventana activa
"""
import base64
import subprocess
import time
from pathlib import Path
from typing import Optional

import pyautogui

try:
    import win32gui
    import win32con
    import win32process
    import psutil
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False


# ---------------------------------------------------------------------------
# Captura de pantalla
# ---------------------------------------------------------------------------

def capturar_pantalla(guardar_en: str = "vision_actual.png") -> str:
    """Captura la pantalla completa y retorna la ruta."""
    img = pyautogui.screenshot()
    img.save(guardar_en)
    return guardar_en


def capturar_ventana_activa(guardar_en: str = "vision_ventana.png") -> tuple[str, str]:
    """Captura solo la ventana activa. Retorna (ruta_imagen, titulo_ventana)."""
    titulo = "Desconocido"
    if _WIN32_OK:
        try:
            hwnd = win32gui.GetForegroundWindow()
            titulo = win32gui.GetWindowText(hwnd) or "Desconocido"
            rect = win32gui.GetWindowRect(hwnd)
            x, y, x2, y2 = rect
            w, h = x2 - x, y2 - y
            if w > 0 and h > 0:
                img = pyautogui.screenshot(region=(x, y, w, h))
                img.save(guardar_en)
                return guardar_en, titulo
        except Exception:
            pass
    # Fallback: pantalla completa
    return capturar_pantalla(guardar_en), titulo


def imagen_a_base64(ruta: str) -> str:
    """Convierte imagen a base64 para enviar a llava."""
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Lectura de VS Code
# ---------------------------------------------------------------------------

def leer_vscode_activo() -> Optional[str]:
    """
    Intenta leer el contenido del editor activo de VS Code.
    Usa Ctrl+A, Ctrl+C para copiar el contenido al clipboard.
    """
    try:
        import pyperclip
        titulo = ""
        if _WIN32_OK:
            hwnd = win32gui.GetForegroundWindow()
            titulo = win32gui.GetWindowText(hwnd)

        if "visual studio code" not in titulo.lower() and "vscode" not in titulo.lower():
            return None

        # Guardar clipboard actual
        try:
            clipboard_anterior = pyperclip.paste()
        except Exception:
            clipboard_anterior = ""

        # Seleccionar todo y copiar
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)

        contenido = pyperclip.paste()

        # Restaurar selección (deseleccionar)
        pyautogui.press("escape")

        if contenido and contenido != clipboard_anterior:
            return contenido[:3000]  # limitar
        return None
    except Exception:
        return None


def obtener_ventana_activa_info() -> dict:
    """Retorna información sobre la ventana activa."""
    info = {"titulo": "Desconocido", "proceso": "Desconocido", "es_vscode": False}
    if not _WIN32_OK:
        return info
    try:
        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd) or "Desconocido"
        info["titulo"] = titulo
        info["es_vscode"] = "visual studio code" in titulo.lower()

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            info["proceso"] = proc.name()
        except Exception:
            pass
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# Detección de actividad
# ---------------------------------------------------------------------------

class ActivityWatcher:
    """Observa la actividad del usuario y detecta cambios relevantes."""

    def __init__(self):
        self._ultima_ventana = ""
        self._ultimo_contenido_hash = ""
        self._ultima_actividad = time.time()

    def check(self) -> dict:
        """Retorna un dict con el estado actual de actividad."""
        info = obtener_ventana_activa_info()
        ahora = time.time()
        inactivo_segundos = ahora - self._ultima_actividad

        cambio_ventana = info["titulo"] != self._ultima_ventana
        if cambio_ventana:
            self._ultima_ventana = info["titulo"]
            self._ultima_actividad = ahora

        return {
            "ventana": info["titulo"],
            "proceso": info["proceso"],
            "es_vscode": info["es_vscode"],
            "cambio_ventana": cambio_ventana,
            "inactivo_segundos": inactivo_segundos,
        }

    def registrar_actividad(self) -> None:
        self._ultima_actividad = time.time()


_watcher = ActivityWatcher()

def get_watcher() -> ActivityWatcher:
    return _watcher


# ---------------------------------------------------------------------------
# Captura ultra rápida con mss + compresión + OCR + límite CPU
# ---------------------------------------------------------------------------

try:
    import mss
    _MSS_OK = True
except ImportError:
    _MSS_OK = False

try:
    import pytesseract
    from PIL import Image as _PILImage
    # Configurar ruta del binario de Tesseract — búsqueda dinámica
    import shutil as _shutil_sv
    import os as _os
    _tess_sv = _shutil_sv.which("tesseract")
    if _tess_sv:
        pytesseract.pytesseract.tesseract_cmd = _tess_sv
    else:
        _TESS_PATHS = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            _os.path.join(_os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for _tp in _TESS_PATHS:
            if _os.path.exists(_tp):
                pytesseract.pytesseract.tesseract_cmd = _tp
                break
    _OCR_OK = True
except ImportError:
    _OCR_OK = False

# Palabras clave que indican error en pantalla
_ERROR_KEYWORDS = {
    "traceback", "error:", "exception", "syntaxerror", "nameerror",
    "typeerror", "valueerror", "indexerror", "keyerror", "attributeerror",
    "importerror", "runtimeerror", "zerodivisionerror", "filenotfounderror",
    "permissionerror", "oserror", "ioerror", "assertionerror",
    "failed", "fatal", "critical", "undefined", "cannot", "not found",
}

# Último título de ventana capturado (para detectar cambios)
_last_window_title: str = ""
_last_capture_time: float = 0.0
_CAPTURE_INTERVAL = 10.0  # segundos entre capturas


def capturar_ventana_rapida(max_width: int = 1280) -> tuple[bytes, str]:
    """
    Captura la ventana activa con mss (ultra rápido) y la comprime.
    Retorna (bytes_jpeg_comprimido, titulo_ventana).
    Solo captura si cambió la ventana o pasaron 10s.
    """
    global _last_window_title, _last_capture_time

    titulo = "Desconocido"
    ahora = time.time()

    # Obtener título de ventana activa
    if _WIN32_OK:
        try:
            hwnd = win32gui.GetForegroundWindow()
            titulo = win32gui.GetWindowText(hwnd) or "Desconocido"
        except Exception:
            pass

    # Solo capturar si cambió la ventana o pasó el intervalo
    ventana_cambio = titulo != _last_window_title
    tiempo_ok = (ahora - _last_capture_time) >= _CAPTURE_INTERVAL

    if not ventana_cambio and not tiempo_ok:
        return b"", titulo

    # Verificar límite de CPU (no capturar si CPU > 70%)
    try:
        import psutil
        if psutil.cpu_percent(interval=0.1) > 70:
            return b"", titulo
    except Exception:
        pass

    _last_window_title = titulo
    _last_capture_time = ahora

    # Capturar con mss (más rápido que pyautogui)
    if _MSS_OK:
        try:
            with mss.mss() as sct:
                if _WIN32_OK:
                    try:
                        hwnd = win32gui.GetForegroundWindow()
                        rect = win32gui.GetWindowRect(hwnd)
                        x, y, x2, y2 = rect
                        w, h = max(1, x2 - x), max(1, y2 - y)
                        monitor = {"top": y, "left": x, "width": w, "height": h}
                    except Exception:
                        monitor = sct.monitors[1]
                else:
                    monitor = sct.monitors[1]

                screenshot = sct.grab(monitor)
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception:
            img = None
    else:
        # Fallback a pyautogui
        try:
            from PIL import Image
            pil_img = pyautogui.screenshot()
            img = pil_img
        except Exception:
            return b"", titulo

    if img is None:
        return b"", titulo

    # Comprimir: redimensionar a max_width manteniendo proporción
    try:
        w, h = img.size
        if w > max_width:
            ratio = max_width / w
            img = img.resize((max_width, int(h * ratio)), Image.LANCZOS)

        # Convertir a JPEG con calidad reducida para velocidad
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60, optimize=True)
        return buf.getvalue(), titulo
    except Exception:
        return b"", titulo


def detectar_errores_en_pantalla() -> dict:
    """
    Captura la ventana activa y busca errores con OCR.
    Retorna dict con: {error_detectado, tipo_error, texto_detectado, titulo_ventana}
    Solo funciona si pytesseract está instalado.
    """
    resultado = {
        "error_detectado": False,
        "tipo_error": None,
        "texto_detectado": "",
        "titulo_ventana": "",
    }

    if not _OCR_OK:
        # Sin OCR: buscar en el título de la ventana
        if _WIN32_OK:
            try:
                hwnd = win32gui.GetForegroundWindow()
                titulo = win32gui.GetWindowText(hwnd) or ""
                resultado["titulo_ventana"] = titulo
                titulo_lower = titulo.lower()
                for kw in _ERROR_KEYWORDS:
                    if kw in titulo_lower:
                        resultado["error_detectado"] = True
                        resultado["tipo_error"] = kw
                        return resultado
            except Exception:
                pass
        return resultado

    try:
        img_bytes, titulo = capturar_ventana_rapida(max_width=800)
        resultado["titulo_ventana"] = titulo

        if not img_bytes:
            return resultado

        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))

        # OCR rápido en escala de grises
        img_gray = img.convert("L")
        texto = pytesseract.image_to_string(img_gray, lang="eng+spa",
                                            config="--psm 6 --oem 1")
        texto_lower = texto.lower()
        resultado["texto_detectado"] = texto[:500]

        for kw in _ERROR_KEYWORDS:
            if kw in texto_lower:
                resultado["error_detectado"] = True
                resultado["tipo_error"] = kw
                break

    except Exception:
        pass

    return resultado

