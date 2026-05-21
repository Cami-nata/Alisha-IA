"""Acciones de sistema extendidas: volumen, música, archivos, brillo, código."""
import os
import subprocess
import sys
from typing import Optional

import pyautogui

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore[import]
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL  # type: ignore[import]
    _PYCAW_AVAILABLE = True
except Exception:
    _PYCAW_AVAILABLE = False

try:
    import screen_brightness_control as sbc  # type: ignore[import]
    _SBC_AVAILABLE = True
except ImportError:
    _SBC_AVAILABLE = False

try:
    import psutil  # type: ignore[import]
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Volumen
# ---------------------------------------------------------------------------

def _get_volume_interface():
    """Retorna la interfaz de volumen de pycaw o None."""
    if not _PYCAW_AVAILABLE:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def controlar_volumen(accion: str, valor: Optional[int] = None) -> str:
    """Controla el volumen del sistema.

    accion: 'subir' | 'bajar' | 'silenciar' | 'restaurar' | 'establecer'
    valor: 0-100 (solo para 'establecer', 'subir', 'bajar')
    """
    accion = accion.strip().lower()
    vol = _get_volume_interface()

    if vol is not None:
        try:
            if accion == "silenciar":
                vol.SetMute(1, None)
                return "Volumen silenciado."
            elif accion == "restaurar":
                vol.SetMute(0, None)
                return "Volumen restaurado."
            elif accion == "establecer":
                nivel = max(0, min(100, int(valor or 50))) / 100.0
                vol.SetMasterVolumeLevelScalar(nivel, None)
                return f"Volumen establecido al {int(nivel * 100)}%."
            elif accion == "subir":
                actual = vol.GetMasterVolumeLevelScalar()
                nuevo = min(1.0, actual + (int(valor or 10) / 100.0))
                vol.SetMasterVolumeLevelScalar(nuevo, None)
                return f"Volumen subido al {int(nuevo * 100)}%."
            elif accion == "bajar":
                actual = vol.GetMasterVolumeLevelScalar()
                nuevo = max(0.0, actual - (int(valor or 10) / 100.0))
                vol.SetMasterVolumeLevelScalar(nuevo, None)
                return f"Volumen bajado al {int(nuevo * 100)}%."
        except Exception as e:
            return f"Error controlando volumen con pycaw: {e}"

    # Fallback: teclas multimedia
    if accion == "silenciar":
        pyautogui.press("volumemute")
        return "Volumen silenciado (tecla multimedia)."
    elif accion == "restaurar":
        pyautogui.press("volumemute")
        return "Volumen restaurado (tecla multimedia)."
    elif accion == "subir":
        pasos = max(1, int(valor or 10) // 5)
        for _ in range(pasos):
            pyautogui.press("volumeup")
        return f"Volumen subido ({pasos} pasos)."
    elif accion == "bajar":
        pasos = max(1, int(valor or 10) // 5)
        for _ in range(pasos):
            pyautogui.press("volumedown")
        return f"Volumen bajado ({pasos} pasos)."
    return f"Acción de volumen no reconocida: {accion}"


# ---------------------------------------------------------------------------
# Música
# ---------------------------------------------------------------------------

def reproducir_musica(accion: str, query: Optional[str] = None) -> str:
    """Controla la reproducción de música.

    accion: 'reproducir' | 'pausar' | 'siguiente' | 'anterior' | 'detener'
    """
    accion = accion.strip().lower()
    if accion == "reproducir":
        if query:
            import webbrowser
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Buscando '{query}' en YouTube."
        pyautogui.press("playpause")
        return "Reproducción iniciada."
    elif accion == "pausar":
        pyautogui.press("playpause")
        return "Reproducción pausada."
    elif accion == "siguiente":
        pyautogui.press("nexttrack")
        return "Siguiente pista."
    elif accion == "anterior":
        pyautogui.press("prevtrack")
        return "Pista anterior."
    elif accion == "detener":
        pyautogui.press("stop")
        return "Reproducción detenida."
    return f"Acción de música no reconocida: {accion}"


# ---------------------------------------------------------------------------
# Búsqueda de archivos
# ---------------------------------------------------------------------------

def buscar_archivo(nombre: str, directorio_base: Optional[str] = None) -> list:
    """Busca archivos por nombre. Retorna hasta 10 rutas encontradas.

    Omite directorios de sistema y ocultos para evitar cuelgues y errores de permisos.
    """
    base = directorio_base or os.path.expanduser("~")
    if not os.path.exists(base):
        base = os.path.expanduser("~")

    # Directorios que no vale la pena recorrer
    _SKIP_DIRS = {
        "windows", "system32", "syswow64", "winsxs",
        "$recycle.bin", "programdata", "appdata",
        "__pycache__", ".git", "node_modules",
    }

    resultados = []
    nombre_lower = nombre.lower()
    try:
        for raiz, dirs, archivos in os.walk(base):
            # Filtrar subdirectorios a ignorar (in-place para que os.walk no los recorra)
            dirs[:] = [
                d for d in dirs
                if d.lower() not in _SKIP_DIRS and not d.startswith(".")
            ]
            for archivo in archivos:
                if nombre_lower in archivo.lower():
                    resultados.append(os.path.join(raiz, archivo))
                    if len(resultados) >= 10:
                        return resultados
    except PermissionError:
        pass
    return resultados


# ---------------------------------------------------------------------------
# Brillo
# ---------------------------------------------------------------------------

def controlar_brillo(accion: str, valor: Optional[int] = None) -> str:
    """Controla el brillo de la pantalla.

    accion: 'subir' | 'bajar' | 'establecer'
    valor: 0-100
    """
    if not _SBC_AVAILABLE:
        return "screen-brightness-control no está instalado."

    accion = accion.strip().lower()
    try:
        actual = sbc.get_brightness(display=0)
        if isinstance(actual, list):
            actual = actual[0]
        actual = int(actual)

        if accion == "establecer":
            nuevo = max(0, min(100, int(valor or 50)))
        elif accion == "subir":
            nuevo = min(100, actual + int(valor or 10))
        elif accion == "bajar":
            nuevo = max(0, actual - int(valor or 10))
        else:
            return f"Acción de brillo no reconocida: {accion}"

        sbc.set_brightness(nuevo, display=0)
        return f"Brillo establecido al {nuevo}%."
    except Exception as e:
        return f"Error controlando brillo: {e}"


# ---------------------------------------------------------------------------
# Ejecución segura de código Python
# ---------------------------------------------------------------------------

# AST-based analysis — más robusto que búsqueda de strings
import ast as _ast

# Módulos completamente prohibidos
_MODULOS_PROHIBIDOS = {
    "os", "subprocess", "shutil", "importlib", "ctypes",
    "socket", "multiprocessing", "threading", "signal",
    "pty", "atexit", "gc", "sys", "builtins",
    "winreg", "msvcrt", "msilib",
}

# Atributos peligrosos que no deben llamarse aunque el módulo esté permitido
_ATRIBUTOS_PELIGROSOS = {
    "system", "popen", "exec", "eval", "compile",
    "rmtree", "remove", "unlink", "rename", "move",
    "__import__", "__builtins__",
}


def _analizar_ast(codigo: str) -> Optional[str]:
    """Analiza el AST del código y retorna descripción del problema o None si es seguro."""
    try:
        tree = _ast.parse(codigo)
    except SyntaxError as e:
        return f"Error de sintaxis: {e}"

    for nodo in _ast.walk(tree):
        # Import de módulos prohibidos
        if isinstance(nodo, (_ast.Import, _ast.ImportFrom)):
            modulo = ""
            if isinstance(nodo, _ast.Import):
                for alias in nodo.names:
                    modulo = alias.name.split(".")[0]
                    if modulo in _MODULOS_PROHIBIDOS:
                        return f"import de módulo prohibido: '{modulo}'"
            else:
                modulo = (nodo.module or "").split(".")[0]
                if modulo in _MODULOS_PROHIBIDOS:
                    return f"import de módulo prohibido: '{modulo}'"

        # Llamadas a atributos peligrosos (ej: os.system, shutil.rmtree)
        if isinstance(nodo, _ast.Call):
            func = nodo.func
            if isinstance(func, _ast.Attribute) and func.attr in _ATRIBUTOS_PELIGROSOS:
                return f"llamada peligrosa: '.{func.attr}'"
            # __import__("os") directo
            if isinstance(func, _ast.Name) and func.id in {"__import__", "eval", "exec", "compile"}:
                return f"función prohibida: '{func.id}'"

        # Acceso a __builtins__, __class__, etc.
        if isinstance(nodo, _ast.Attribute) and nodo.attr.startswith("__"):
            return f"acceso a atributo dunder prohibido: '{nodo.attr}'"

    return None  # código seguro


def ejecutar_codigo_seguro(codigo: str, timeout: int = 10) -> str:
    """Ejecuta un snippet de Python en subprocess aislado con timeout.

    Usa análisis AST para detectar código peligroso antes de ejecutar.
    Más robusto que búsqueda de strings — no se puede evadir con espacios o aliases.
    """
    if not codigo or not codigo.strip():
        return "No se proporcionó código para ejecutar."

    # Análisis estático primero
    problema = _analizar_ast(codigo)
    if problema:
        return f"Ejecución rechazada: {problema}."

    try:
        resultado = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            timeout=timeout,
            # Aislar variables de entorno sensibles
            env={"PYTHONPATH": "", "PATH": os.environ.get("PATH", "")},
        )
        salida = resultado.stdout.strip()
        errores = resultado.stderr.strip()
        if errores:
            return f"Error:\n{errores}"
        return salida or "(sin salida)"
    except subprocess.TimeoutExpired:
        return f"Tiempo de ejecución agotado ({timeout}s)."
    except Exception as e:
        return f"Error ejecutando código: {e}"
