"""
task_orchestrator.py — Orquestador de tareas autónomas para Alisha.

Cuando el usuario pide algo que requiere múltiples pasos, Alisha los
encadena automáticamente sin que el usuario tenga que hacer nada.

Ejemplos:
  "escribí algo en el bloc de notas"
  → 1. Abrir notepad  2. Esperar  3. Escribir texto

  "buscá algo en Google"
  → 1. Abrir Chrome  2. Navegar a google.com  3. Escribir búsqueda

  "abrí VS Code y creá un archivo"
  → 1. Abrir VS Code  2. Esperar  3. Crear archivo

El orquestador también detecta si la app ya está abierta para no
abrirla dos veces.
"""
import subprocess
import time
from typing import Optional

try:
    import win32gui
    import win32process
    import psutil
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False

import pyautogui

# ---------------------------------------------------------------------------
# Mapa de intenciones → secuencia de pasos
# ---------------------------------------------------------------------------

# Cada entrada: (palabras_clave_en_mensaje, app_a_abrir, espera_segundos)
_INTENT_MAP = [
    # Bloc de notas
    ({"bloc de notas", "notepad", "bloc", "nota de texto", "archivo de texto"},
     "notepad", 1.5),

    # VS Code
    ({"vs code", "vscode", "visual studio code", "code", "editor de código"},
     "code", 3.0),

    # Word
    ({"word", "documento word", "microsoft word", "docx"},
     "word", 4.0),

    # Excel
    ({"excel", "planilla", "hoja de cálculo", "spreadsheet"},
     "excel", 4.0),

    # Chrome
    ({"chrome", "google chrome", "navegador chrome"},
     "chrome", 2.5),

    # Edge
    ({"edge", "microsoft edge", "navegador edge"},
     "edge", 2.5),

    # Firefox
    ({"firefox", "mozilla"},
     "firefox", 2.5),

    # Calculadora
    ({"calculadora", "calculator"},
     "calc", 1.5),

    # Paint
    ({"paint", "mspaint", "dibujo"},
     "mspaint", 1.5),

    # PowerPoint
    ({"powerpoint", "presentación", "pptx", "diapositivas"},
     "powerpnt", 4.0),

    # Explorador de archivos
    ({"explorador", "explorador de archivos", "carpetas", "mis documentos"},
     "explorador", 1.5),

    # Spotify
    ({"spotify", "música en spotify"},
     "spotify", 3.0),

    # Discord
    ({"discord"},
     "discord", 3.0),

    # Canva (web)
    ({"canva"},
     None, 0),  # Canva es web, se abre con el navegador
]

# Acciones que implican escribir texto en una app
_ACCIONES_ESCRITURA = {
    "escribir", "escribí", "escriba", "tipear", "tipeá",
    "anotá", "anotar", "poner", "poné", "agregar", "agregá",
    "redactar", "redactá", "crear nota", "nueva nota",
}

# Acciones que implican buscar en la web
_ACCIONES_BUSQUEDA_WEB = {
    "buscá", "buscar", "busca", "googleá", "googlear",
    "buscame", "buscame en google", "buscá en google",
}


# ---------------------------------------------------------------------------
# Detector de app activa
# ---------------------------------------------------------------------------

def _app_esta_abierta(nombre_proceso: str) -> Optional[int]:
    """
    Retorna el PID si el proceso está corriendo, None si no.
    nombre_proceso: ej. "notepad.exe", "chrome.exe"
    """
    if not _WIN32_OK:
        return None
    try:
        nombre_lower = nombre_proceso.lower()
        if not nombre_lower.endswith(".exe"):
            nombre_lower += ".exe"
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"].lower() == nombre_lower:
                return proc.info["pid"]
    except Exception:
        pass
    return None


def _enfocar_ventana_de_proceso(pid: int) -> bool:
    """Trae al frente la ventana del proceso con ese PID."""
    if not _WIN32_OK:
        return False
    try:
        def _callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                if wpid == pid:
                    hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(_callback, hwnds)
        if hwnds:
            hwnd = hwnds[0]
            win32gui.ShowWindow(hwnd, 9)   # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def _esperar_ventana(titulo_parcial: str, timeout: float = 8.0) -> bool:
    """Espera hasta que aparezca una ventana con ese título parcial."""
    if not _WIN32_OK:
        time.sleep(timeout * 0.5)
        return True

    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            def _check(hwnd, found):
                if win32gui.IsWindowVisible(hwnd):
                    titulo = win32gui.GetWindowText(hwnd).lower()
                    if titulo_parcial.lower() in titulo:
                        found.append(hwnd)
                return True
            found = []
            win32gui.EnumWindows(_check, found)
            if found:
                win32gui.SetForegroundWindow(found[0])
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

# Mapa de nombre_app → nombre_proceso para verificar si está abierta
_PROCESO_MAP = {
    "notepad":   "notepad.exe",
    "code":      "code.exe",
    "word":      "winword.exe",
    "excel":     "excel.exe",
    "chrome":    "chrome.exe",
    "edge":      "msedge.exe",
    "firefox":   "firefox.exe",
    "calc":      "calculator.exe",
    "mspaint":   "mspaint.exe",
    "powerpnt":  "powerpnt.exe",
    "spotify":   "spotify.exe",
    "discord":   "discord.exe",
}

# Mapa de nombre_app → título de ventana esperado (para esperar que cargue)
_TITULO_MAP = {
    "notepad":   "bloc de notas",
    "code":      "visual studio code",
    "word":      "word",
    "excel":     "excel",
    "chrome":    "google chrome",
    "edge":      "edge",
    "firefox":   "mozilla firefox",
    "calc":      "calculadora",
    "mspaint":   "paint",
    "powerpnt":  "powerpoint",
    "spotify":   "spotify",
    "discord":   "discord",
}


def asegurar_app_abierta(nombre_app: str, espera: float = 2.0) -> str:
    """
    Abre la app si no está corriendo, o la enfoca si ya está abierta.
    Retorna mensaje de estado.
    """
    proceso = _PROCESO_MAP.get(nombre_app.lower())

    # Verificar si ya está abierta
    if proceso:
        pid = _app_esta_abierta(proceso)
        if pid:
            enfocada = _enfocar_ventana_de_proceso(pid)
            time.sleep(0.5)
            return f"'{nombre_app}' ya estaba abierta — la traje al frente."

    # Abrir la app
    try:
        from app_discovery import resolver_app
        _NO_WIN = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        if nombre_app == "explorador":
            subprocess.Popen(["explorer"], creationflags=_NO_WIN)
        else:
            ruta = resolver_app(nombre_app)
            subprocess.Popen([ruta], creationflags=_NO_WIN)

        # Esperar a que la ventana aparezca
        titulo_esperado = _TITULO_MAP.get(nombre_app.lower(), nombre_app)
        encontrada = _esperar_ventana(titulo_esperado, timeout=espera + 4)

        if not encontrada:
            time.sleep(espera)

        return f"'{nombre_app}' abierta y lista."

    except ValueError as e:
        try:
            _NO_WIN = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            subprocess.Popen(nombre_app, shell=False, creationflags=_NO_WIN)
            time.sleep(espera)
            return f"'{nombre_app}' lanzada."
        except Exception:
            return f"No pude abrir '{nombre_app}': {e}"
    except Exception as e:
        return f"Error abriendo '{nombre_app}': {e}"


def detectar_app_necesaria(mensaje: str) -> Optional[tuple[str, float]]:
    """
    Analiza el mensaje y retorna (nombre_app, espera) si detecta
    que se necesita abrir una app. Retorna None si no aplica.
    """
    msg_lower = mensaje.lower()
    for palabras_clave, app, espera in _INTENT_MAP:
        if any(p in msg_lower for p in palabras_clave):
            return (app, espera) if app else None
    return None


def orquestar_tarea(mensaje: str, accion_ia: dict) -> list[dict]:
    """
    Dado el mensaje del usuario y la acción que Ollama decidió,
    retorna una lista ordenada de acciones a ejecutar.

    Si la acción requiere una app que no está abierta, inserta
    'abrir_app' como primer paso automáticamente.
    """
    tipo = accion_ia.get("accion", "nada")
    pasos = []

    # Detectar si la acción implica escribir en una app de escritorio
    necesita_app = None

    if tipo in ("escribir_texto", "hotkey", "click", "doble_click"):
        # Verificar si el mensaje menciona una app específica
        app_detectada = detectar_app_necesaria(mensaje)
        if app_detectada:
            nombre_app, espera = app_detectada
            proceso = _PROCESO_MAP.get(nombre_app, nombre_app + ".exe")
            # Solo abrir si no está ya en foco
            if not _app_esta_en_foco(nombre_app):
                pasos.append({
                    "accion": "_abrir_y_esperar",
                    "app": nombre_app,
                    "espera": espera,
                    "mensaje": f"Abriendo {nombre_app}...",
                })

    # Agregar la acción original
    pasos.append(accion_ia)
    return pasos


def _app_esta_en_foco(nombre_app: str) -> bool:
    """Verifica si la app ya está en el foco actual."""
    if not _WIN32_OK:
        return False
    try:
        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd).lower()
        titulo_esperado = _TITULO_MAP.get(nombre_app.lower(), nombre_app.lower())
        return titulo_esperado in titulo
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Ejecutor de pasos orquestados
# ---------------------------------------------------------------------------

def ejecutar_pasos(pasos: list[dict], callback_ejecutar) -> str:
    """
    Ejecuta una lista de pasos en orden.
    callback_ejecutar: función que recibe un dict de acción y lo ejecuta
    (normalmente ia.ejecutar)
    """
    resultados = []
    for paso in pasos:
        if paso.get("accion") == "_abrir_y_esperar":
            resultado = asegurar_app_abierta(paso["app"], paso.get("espera", 2.0))
            resultados.append(resultado)
            time.sleep(0.3)  # pequeña pausa extra para que la ventana tome foco
        else:
            try:
                callback_ejecutar(paso)
                resultados.append(f"✓ {paso.get('accion', 'acción')}")
            except Exception as e:
                resultados.append(f"✗ {paso.get('accion')}: {e}")

    return " → ".join(resultados)


# ---------------------------------------------------------------------------
# Función de alto nivel — punto de entrada principal
# ---------------------------------------------------------------------------

def resolver_y_ejecutar(mensaje: str, accion_ia: dict, callback_ejecutar) -> str:
    """
    Punto de entrada principal del orquestador.

    1. Analiza el mensaje y la acción de la IA
    2. Determina si se necesitan pasos previos (abrir app, etc.)
    3. Ejecuta todo en orden
    4. Retorna resumen de lo que hizo
    """
    pasos = orquestar_tarea(mensaje, accion_ia)

    if len(pasos) == 1:
        # Sin pasos extra — ejecutar directamente
        try:
            callback_ejecutar(accion_ia)
        except Exception as e:
            return f"Error ejecutando acción: {e}"
        return ""

    # Hay pasos encadenados
    return ejecutar_pasos(pasos, callback_ejecutar)
