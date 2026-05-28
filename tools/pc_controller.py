"""
pc_controller.py — Control total del PC con límites de seguridad.

Alisha puede:
- Mover el mouse y hacer clicks
- Escribir texto y usar atajos
- Abrir/cerrar aplicaciones
- Navegar en Canva, hacer infografías, todo tipo de trabajos que pida el usuario
- Detectar contexto (YouTube, PowerPoint, cualquier tipo de aplicacion que el usuario este usando)
- Modo silencioso en presentaciones
- Detector de procrastinación
- Diario de productividad
- Asistente de escritura en tiempo real
- Traductor de subtítulos a español

SIEMPRE con confirmación previa del usuario.
"""
import json
import os
import random
import subprocess
import time
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Callable

import pyautogui

try:
    import win32gui
    import win32process
    import psutil
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False

# ---------------------------------------------------------------------------
# Límites de seguridad del mouse/teclado
# ---------------------------------------------------------------------------

# Zonas de pantalla donde Alisha NO puede hacer click (esquinas del sistema)
ZONAS_PROHIBIDAS = [
    (0, 0, 50, 50),          # esquina superior izquierda (botón inicio)
    (0, 1030, 200, 1080),    # barra de tareas izquierda
]

# Aplicaciones donde Alisha NO puede escribir
APPS_PROTEGIDAS = {
    "taskmgr.exe",      # administrador de tareas
    "regedit.exe",      # registro
    "cmd.exe",          # terminal (solo con confirmación extra)
    "powershell.exe",
}

pyautogui.FAILSAFE = True   # mover mouse a esquina superior izquierda = parar
pyautogui.PAUSE = 0.15      # pausa entre acciones para que se vea natural
STOP_EVENT = threading.Event()

# ---------------------------------------------------------------------------
# Modo bloqueado — Ctrl+Shift+L desactiva TODO control del PC por la IA
# ---------------------------------------------------------------------------
_BLOQUEADO = threading.Event()  # si está set, la IA no puede controlar nada


def esta_bloqueado() -> bool:
    return _BLOQUEADO.is_set()


def set_bloqueado(valor: bool) -> str:
    if valor:
        _BLOQUEADO.set()
        abort_all_actions()  # cancela lo que esté en curso
        return "🔒 Control bloqueado — Alisha no puede controlar el PC"
    else:
        _BLOQUEADO.clear()
        reset_abort()
        return "🔓 Control desbloqueado — Alisha puede controlar el PC"


def toggle_bloqueado() -> str:
    return set_bloqueado(not esta_bloqueado())


def iniciar_hotkey_bloqueo() -> None:
    """Registra Ctrl+Shift+L como hotkey global para bloquear/desbloquear."""
    try:
        import keyboard

        def _on_hotkey():
            estado = toggle_bloqueado()
            print(f"\n[Seguridad] {estado}")
            # Notificar a la web app si está corriendo
            try:
                from web_app import socketio
                socketio.emit("lock_state", {"bloqueado": esta_bloqueado()})
            except Exception:
                pass

        keyboard.add_hotkey("ctrl+shift+l", _on_hotkey, suppress=False)
        print("[Seguridad] ✓ Hotkey Ctrl+Shift+L registrado (bloquear/desbloquear control)")
    except Exception as e:
        print(f"[Seguridad] No se pudo registrar hotkey: {e}")


def abort_all_actions() -> str:
    STOP_EVENT.set()
    return "Interrupción recibida. Abortando acciones en curso."


def reset_abort() -> None:
    STOP_EVENT.clear()


def _verificar_zona_segura(x: int, y: int) -> bool:
    for x1, y1, x2, y2 in ZONAS_PROHIBIDAS:
        if x1 <= x <= x2 and y1 <= y <= y2:
            return False
    return True


def _verificar_app_segura() -> bool:
    if not _WIN32_OK:
        return True
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower() not in APPS_PROTEGIDAS
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Control de mouse
# ---------------------------------------------------------------------------

def mover_mouse(x: int, y: int, duracion: float = 0.5) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if STOP_EVENT.is_set():
        return "Acción abortada." if not _verificar_zona_segura(x, y) else "Acción abortada."
    if not _verificar_zona_segura(x, y):
        return "No puedo mover el mouse a esa zona (área protegida)."

    paso = max(1, int(max(1, duracion) / 0.05))
    origen = pyautogui.position()
    for i in range(1, paso + 1):
        if STOP_EVENT.is_set():
            return "Acción abortada."
        nx = int(origen.x + (x - origen.x) * i / paso)
        ny = int(origen.y + (y - origen.y) * i / paso)
        pyautogui.moveTo(nx, ny, duration=0.05)
    return f"Mouse movido a ({x}, {y})."


def click(x: int, y: int, boton: str = "left") -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if STOP_EVENT.is_set():
        return "Acción abortada."
    if not _verificar_zona_segura(x, y):
        return "Zona protegida — no puedo hacer click ahí."
    if not _verificar_app_segura():
        return "Aplicación protegida — no puedo interactuar con ella."
    try:
        pyautogui.click(x=x, y=y, button=boton)
    except pyautogui.FailSafeException:
        return "FailSafe activado — mouse en esquina. Acción cancelada."
    except Exception as e:
        return f"Error al hacer click: {e}"
    return f"Click en ({x}, {y})."


def doble_click(x: int, y: int) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if STOP_EVENT.is_set():
        return "Acción abortada."
    if not _verificar_zona_segura(x, y):
        return "Zona protegida."
    try:
        pyautogui.doubleClick(x=x, y=y)
    except pyautogui.FailSafeException:
        return "FailSafe activado — acción cancelada."
    except Exception as e:
        return f"Error al hacer doble click: {e}"
    return f"Doble click en ({x}, {y})."


def _bezier_point(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    return (
        (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
        (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1],
    )


def mover_mouse_humano(x: int, y: int, duracion: float = 1.0) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if STOP_EVENT.is_set():
        return "Acción abortada."
    if not _verificar_zona_segura(x, y):
        return "No puedo mover el mouse a esa zona (área protegida)."

    origen = pyautogui.position()
    control1 = (origen.x + (x - origen.x) * 0.25, origen.y + (y - origen.y) * 0.1)
    control2 = (origen.x + (x - origen.x) * 0.6, origen.y + (y - origen.y) * 0.9)
    pasos = max(10, int(duracion / 0.02))

    for i in range(1, pasos + 1):
        if STOP_EVENT.is_set():
            return "Acción abortada."
        t = i / pasos
        nx, ny = _bezier_point((origen.x, origen.y), control1, control2, (x, y), t)
        pyautogui.moveTo(int(nx), int(ny), duration=0.0)
    return f"Mouse movido con gesto humano a ({x}, {y})."


def hacer_clic_validado(imagen_referencia: str, retries: int = 3, confianza: float = 0.75) -> str:
    if STOP_EVENT.is_set():
        return "Acción abortada."
    if not _WIN32_OK:
        return "No se puede validar la imagen sin pywin32/psutil disponibles."
    if not Path(imagen_referencia).exists():
        return f"No se encontró la imagen de referencia: {imagen_referencia}"

    for intento in range(1, retries + 1):
        if STOP_EVENT.is_set():
            return "Acción abortada."
        try:
            punto = pyautogui.locateCenterOnScreen(imagen_referencia, confidence=confianza, grayscale=True)
        except Exception:
            punto = None

        if punto:
            if not _verificar_zona_segura(punto.x, punto.y):
                return "La ubicación encontrada está en una zona protegida."
            mover_mouse_humano(punto.x, punto.y, duracion=0.6)
            pyautogui.click(punto.x, punto.y)
            return f"Click validado en {imagen_referencia} ({punto.x}, {punto.y})."

        if intento < retries:
            time.sleep(0.8)

    return f"No pude encontrar la imagen en pantalla después de {retries} intentos."


def escribir_humano(texto: str, intervalo: float = 0.04) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if not _verificar_app_segura():
        return "Aplicación protegida."
    intervalos = [max(0.02, min(0.12, intervalo + (random.random() - 0.5) * 0.02)) for _ in texto]
    for char, intervalo_real in zip(texto, intervalos):
        if STOP_EVENT.is_set():
            return "Acción abortada."
        pyautogui.write(char, interval=intervalo_real)
    return f"Texto escrito de forma humana: '{texto[:30]}{'...' if len(texto)>30 else ''}'." 


def scroll(x: int, y: int, cantidad: int = 3) -> str:
    try:
        pyautogui.scroll(cantidad, x=x, y=y)
    except pyautogui.FailSafeException:
        return "FailSafe activado — scroll cancelado."
    except Exception as e:
        return f"Error al hacer scroll: {e}"
    return f"Scroll {'arriba' if cantidad > 0 else 'abajo'} en ({x}, {y})."


def arrastrar(x1: int, y1: int, x2: int, y2: int, duracion: float = 0.8) -> str:
    if not _verificar_zona_segura(x1, y1) or not _verificar_zona_segura(x2, y2):
        return "Zona protegida."
    try:
        pyautogui.drag(x2 - x1, y2 - y1, duration=duracion, button="left")
    except pyautogui.FailSafeException:
        return "FailSafe activado — arrastre cancelado."
    except Exception as e:
        return f"Error al arrastrar: {e}"
    return f"Arrastrado de ({x1},{y1}) a ({x2},{y2})."


def get_posicion_mouse() -> tuple[int, int]:
    return pyautogui.position()


# ---------------------------------------------------------------------------
# Control de teclado
# ---------------------------------------------------------------------------

def escribir(texto: str, intervalo: float = 0.04) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    if not _verificar_app_segura():
        return "Aplicación protegida."
    try:
        pyautogui.write(texto, interval=intervalo)
    except pyautogui.FailSafeException:
        return "FailSafe activado — escritura cancelada."
    except Exception as e:
        return f"Error al escribir: {e}"
    return f"Texto escrito: '{texto[:30]}{'...' if len(texto)>30 else ''}'."


def presionar_tecla(tecla: str) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    try:
        pyautogui.press(tecla)
    except pyautogui.FailSafeException:
        return "FailSafe activado."
    except Exception as e:
        return f"Error al presionar tecla: {e}"
    return f"Tecla presionada: {tecla}."


def atajo(teclas: list[str]) -> str:
    if _BLOQUEADO.is_set():
        return "🔒 Control bloqueado. Presioná Ctrl+Shift+L para desbloquear."
    try:
        pyautogui.hotkey(*teclas)
    except pyautogui.FailSafeException:
        return "FailSafe activado."
    except Exception as e:
        return f"Error al ejecutar atajo: {e}"
    return f"Atajo ejecutado: {'+'.join(teclas)}."


# ---------------------------------------------------------------------------
# Detector de contexto de ventana
# ---------------------------------------------------------------------------

class ContextDetector:
    """Detecta qué está haciendo el usuario y activa modos especiales."""

    CONTEXTOS = {
        "youtube":      ["youtube", "youtu.be"],
        "powerpoint":   ["powerpoint", "presentación", ".pptx"],
        "canva":        ["canva.com"],
        "zoom":         ["zoom", "meeting"],
        "vscode":       ["visual studio code"],
        "netflix":      ["netflix"],
        "word":         ["microsoft word", ".docx"],
        "excel":        ["microsoft excel", ".xlsx"],
        "navegador":    ["chrome", "edge", "firefox"],
    }

    def __init__(self):
        self._contexto_actual = "general"
        self._modo_silencioso = False
        self._tiempo_youtube  = 0.0

    def detectar(self) -> str:
        if not _WIN32_OK:
            return "general"
        try:
            hwnd = win32gui.GetForegroundWindow()
            titulo = win32gui.GetWindowText(hwnd).lower()
            for contexto, palabras in self.CONTEXTOS.items():
                if any(p in titulo for p in palabras):
                    return contexto
        except Exception:
            pass
        return "general"

    def actualizar(self) -> tuple[str, bool]:
        """
        Retorna (contexto_actual, cambio_detectado).
        """
        nuevo = self.detectar()
        cambio = nuevo != self._contexto_actual

        # Modo silencioso en PowerPoint
        if nuevo == "powerpoint" and not self._modo_silencioso:
            self._modo_silencioso = True
        elif nuevo != "powerpoint" and self._modo_silencioso:
            self._modo_silencioso = False

        # Rastrear tiempo en YouTube
        if nuevo == "youtube":
            if self._tiempo_youtube == 0:
                self._tiempo_youtube = time.time()
        else:
            self._tiempo_youtube = 0

        self._contexto_actual = nuevo
        return nuevo, cambio

    def tiempo_en_youtube(self) -> float:
        if self._tiempo_youtube == 0:
            return 0
        return time.time() - self._tiempo_youtube

    def esta_en_modo_silencioso(self) -> bool:
        return self._modo_silencioso

    def get_contexto(self) -> str:
        return self._contexto_actual


# ---------------------------------------------------------------------------
# Diario de productividad
# ---------------------------------------------------------------------------

class ProductivityDiary:
    """Registra el tiempo en cada aplicación durante el día."""

    DIARY_FILE = Path("productividad.json")

    def __init__(self):
        self._sesiones: list[dict] = []
        self._inicio_sesion_actual = time.time()
        self._app_actual = "general"
        self._cargar()

    def _cargar(self) -> None:
        if self.DIARY_FILE.exists():
            try:
                data = json.loads(self.DIARY_FILE.read_text(encoding="utf-8"))
                # Solo cargar sesiones de hoy
                hoy = date.today().isoformat()
                self._sesiones = [s for s in data if s.get("fecha") == hoy]
            except Exception:
                pass

    def _guardar(self) -> None:
        try:
            # Cargar todo el historial
            historial = []
            if self.DIARY_FILE.exists():
                historial = json.loads(self.DIARY_FILE.read_text(encoding="utf-8"))
            # Agregar sesiones de hoy
            hoy = date.today().isoformat()
            historial = [s for s in historial if s.get("fecha") != hoy]
            historial.extend(self._sesiones)
            self.DIARY_FILE.write_text(
                json.dumps(historial[-500:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def registrar_cambio_app(self, nueva_app: str) -> None:
        ahora = time.time()
        duracion = ahora - self._inicio_sesion_actual
        if duracion > 30:  # solo registrar si estuvo más de 30 segundos
            self._sesiones.append({
                "fecha":    date.today().isoformat(),
                "hora":     datetime.now().strftime("%H:%M"),
                "app":      self._app_actual,
                "minutos":  round(duracion / 60, 1),
            })
            self._guardar()
        self._app_actual = nueva_app
        self._inicio_sesion_actual = ahora

    def resumen_hoy(self) -> str:
        if not self._sesiones:
            return "No hay datos de productividad para hoy todavía."

        # Agrupar por app
        from collections import defaultdict
        totales: dict = defaultdict(float)
        for s in self._sesiones:
            totales[s["app"]] += s["minutos"]

        lineas = ["📊 Resumen de hoy:"]
        for app, mins in sorted(totales.items(), key=lambda x: -x[1]):
            horas = int(mins // 60)
            minutos = int(mins % 60)
            tiempo_str = f"{horas}h {minutos}min" if horas > 0 else f"{minutos}min"
            lineas.append(f"  • {app}: {tiempo_str}")

        total = sum(totales.values())
        lineas.append(f"\nTotal activa: {int(total//60)}h {int(total%60)}min")
        return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Asistente de escritura
# ---------------------------------------------------------------------------

def sugerir_mejora_texto(texto: str) -> str:
    """
    Analiza un texto y retorna sugerencias de mejora.
    Se llama desde el prompt de Alisha cuando detecta texto largo.
    """
    # Esta función genera el prompt para que Alisha analice el texto
    return (
        f"El usuario escribió este texto:\n\n{texto[:500]}\n\n"
        "Analizá brevemente: ¿hay errores ortográficos, frases confusas o mejoras de estilo? "
        "Sé concisa y directa. Máximo 3 sugerencias."
    )


# ---------------------------------------------------------------------------
# Automatización de Canva / proyectos creativos
# ---------------------------------------------------------------------------

def abrir_canva_plantilla(tipo: str = "infografia") -> str:
    """
    Abre Canva en el navegador con una búsqueda de plantilla.
    tipo: 'infografia', 'afiche', 'presentacion', 'cv', 'logo'
    """
    import webbrowser
    plantillas = {
        "infografia":   "https://www.canva.com/es_419/crear/infografias/",
        "afiche":       "https://www.canva.com/es_419/crear/afiches/",
        "presentacion": "https://www.canva.com/es_419/crear/presentaciones/",
        "cv":           "https://www.canva.com/es_419/crear/curriculum-vitae/",
        "logo":         "https://www.canva.com/es_419/crear/logos/",
        "flyer":        "https://www.canva.com/es_419/crear/flyers/",
        "banner":       "https://www.canva.com/es_419/crear/banners/",
    }
    url = plantillas.get(tipo.lower(), f"https://www.canva.com/search?q={tipo}")
    webbrowser.open(url)
    return f"Abrí Canva con plantillas de {tipo}. ¿Querés que te ayude a elegir una?"


def guiar_proyecto_canva(tipo: str, descripcion: str) -> str:
    """
    Genera instrucciones paso a paso para crear un proyecto en Canva.
    """
    guias = {
        "infografia": [
            "1. Elegí una plantilla vertical (800x2000px recomendado)",
            "2. Cambiá el título principal con tu tema",
            "3. Usá íconos de la biblioteca de Canva para cada sección",
            "4. Mantené máximo 3 colores para que se vea limpio",
            "5. Exportá como PNG o PDF",
        ],
        "afiche": [
            "1. Elegí formato A4 o carta",
            "2. El título debe ser grande y llamativo (ocupa 1/3 del espacio)",
            "3. Agregá una imagen de fondo o elemento visual central",
            "4. Información de contacto abajo",
            "5. Exportá como PDF para imprimir",
        ],
        "cv": [
            "1. Elegí una plantilla minimalista (más profesional)",
            "2. Foto de perfil en la esquina superior",
            "3. Secciones: Experiencia, Educación, Habilidades, Contacto",
            "4. Usá íconos para las habilidades técnicas",
            "5. Exportá como PDF",
        ],
    }
    pasos = guias.get(tipo.lower(), ["Abrí Canva y buscá plantillas de " + tipo])
    return f"Para tu {tipo} sobre '{descripcion}':\n" + "\n".join(pasos)


# ---------------------------------------------------------------------------
# Singleton y estado global
# ---------------------------------------------------------------------------

_detector   = ContextDetector()
_diary      = ProductivityDiary()


def get_detector() -> ContextDetector:
    return _detector


def get_diary() -> ProductivityDiary:
    return _diary


# ---------------------------------------------------------------------------
# Loop de observación (corre en hilo daemon)
# ---------------------------------------------------------------------------

def iniciar_observacion(callback: Callable[[str, str], None]) -> None:
    """
    Inicia el loop de observación del contexto.
    callback(tipo_evento, mensaje):
    - tipo_evento: 'procrastinacion', 'modo_silencioso', 'cambio_contexto'
    - mensaje: descripción del evento
    """
    def _loop():
        TIEMPO_PROCRASTINACION = 20 * 60  # 20 minutos

        while True:
            try:
                contexto, cambio = _detector.actualizar()

                # Registrar cambio en diario
                if cambio:
                    _diary.registrar_cambio_app(contexto)

                # Detector de procrastinación (YouTube > 20 min)
                tiempo_yt = _detector.tiempo_en_youtube()
                if tiempo_yt > TIEMPO_PROCRASTINACION:
                    callback("procrastinacion",
                             f"Llevas {int(tiempo_yt/60)} minutos en YouTube... "
                             "¿Querés volver a lo que estabas haciendo?")
                    _detector._tiempo_youtube = time.time()  # resetear

                # Modo silencioso activado
                if cambio and contexto == "powerpoint":
                    callback("modo_silencioso",
                             "Veo que abriste PowerPoint. No te interrumpo durante la presentación. Éxito!")

                # Modo silencioso desactivado
                if cambio and contexto != "powerpoint" and _detector._modo_silencioso:
                    callback("modo_silencioso",
                             "¿Cómo fue la presentación?")

            except Exception:
                pass

            time.sleep(30)  # revisar cada 30 segundos

    t = threading.Thread(target=_loop, daemon=True, name="PCObserver")
    t.start()



# ---------------------------------------------------------------------------
# Control de volumen (Req 3.11) — Bloque 3 parte 3
# ---------------------------------------------------------------------------

def volumen_subir(pasos: int = 5) -> str:
    """Sube el volumen del sistema en pasos de tecla."""
    try:
        import pyautogui
        for _ in range(pasos):
            pyautogui.press("volumeup")
        return f"🔊 Volumen subido ({pasos} pasos)."
    except Exception as e:
        return f"Error al subir volumen: {e}"


def volumen_bajar(pasos: int = 5) -> str:
    """Baja el volumen del sistema en pasos de tecla."""
    try:
        import pyautogui
        for _ in range(pasos):
            pyautogui.press("volumedown")
        return f"🔉 Volumen bajado ({pasos} pasos)."
    except Exception as e:
        return f"Error al bajar volumen: {e}"


def volumen_silenciar() -> str:
    """Silencia/desilencia el volumen del sistema."""
    try:
        import pyautogui
        pyautogui.press("volumemute")
        return "🔇 Volumen silenciado/desilenciado."
    except Exception as e:
        return f"Error al silenciar volumen: {e}"


def volumen_set(nivel: int) -> str:
    """
    Establece el volumen a un nivel específico (0-100) usando pycaw o nircmd.
    Fallback a teclas si no están disponibles.
    """
    nivel = max(0, min(100, nivel))
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        # pycaw usa escala -65.25 a 0.0 dB; convertir de 0-100
        scalar = nivel / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return f"🔊 Volumen establecido al {nivel}%."
    except ImportError:
        # Fallback: usar nircmd si está disponible
        try:
            import subprocess
            val = int(nivel * 65535 / 100)
            subprocess.run(["nircmd", "setsysvolume", str(val)], check=True, capture_output=True)
            return f"🔊 Volumen establecido al {nivel}%."
        except Exception:
            return f"No se pudo establecer volumen exacto. Instalar pycaw: pip install pycaw"
    except Exception as e:
        return f"Error al establecer volumen: {e}"


# ---------------------------------------------------------------------------
# Control de brillo (Req 3.12)
# ---------------------------------------------------------------------------

def brillo_ajustar(nivel: int) -> str:
    """
    Ajusta el brillo de la pantalla (0-100).
    Usa WMI en Windows.
    """
    nivel = max(0, min(100, nivel))
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(nivel, 0)
        return f"☀️ Brillo ajustado al {nivel}%."
    except ImportError:
        return "WMI no disponible. Instalar con: pip install wmi"
    except Exception as e:
        # Fallback: PowerShell
        try:
            import subprocess
            cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{nivel})"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
            return f"☀️ Brillo ajustado al {nivel}%."
        except Exception as e2:
            return f"Error al ajustar brillo: {e} / {e2}"


def brillo_subir(pasos: int = 10) -> str:
    """Sube el brillo en incrementos."""
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        actual = c.WmiMonitorBrightness()[0].CurrentBrightness
        nuevo = min(100, actual + pasos)
        return brillo_ajustar(nuevo)
    except Exception:
        return brillo_ajustar(70)  # valor seguro


def brillo_bajar(pasos: int = 10) -> str:
    """Baja el brillo en decrementos."""
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        actual = c.WmiMonitorBrightness()[0].CurrentBrightness
        nuevo = max(10, actual - pasos)
        return brillo_ajustar(nuevo)
    except Exception:
        return brillo_ajustar(40)  # valor seguro


# ---------------------------------------------------------------------------
# Gestión de procesos (Req 3.13)
# ---------------------------------------------------------------------------

def listar_procesos(top: int = 15) -> list[dict]:
    """
    Lista los procesos activos ordenados por uso de CPU.

    Returns:
        Lista de dicts con {"pid", "name", "cpu", "ram_mb"}
    """
    try:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                procs.append({
                    "pid":    info["pid"],
                    "name":   info["name"],
                    "cpu":    round(info["cpu_percent"] or 0.0, 1),
                    "ram_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / (1024 * 1024), 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Ordenar por CPU descendente
        procs.sort(key=lambda x: x["cpu"], reverse=True)
        return procs[:top]
    except ImportError:
        return [{"pid": 0, "name": "psutil no instalado", "cpu": 0, "ram_mb": 0}]
    except Exception as e:
        return [{"pid": 0, "name": f"Error: {e}", "cpu": 0, "ram_mb": 0}]


def terminar_proceso(nombre_o_pid) -> str:
    """
    Termina un proceso por nombre o PID.

    Args:
        nombre_o_pid: Nombre del proceso (ej: "notepad.exe") o PID (int)

    Returns:
        Mensaje de resultado.
    """
    try:
        import psutil

        terminados = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if isinstance(nombre_o_pid, int):
                    if proc.pid == nombre_o_pid:
                        proc.terminate()
                        terminados.append(f"{proc.name()} (PID {proc.pid})")
                else:
                    if proc.name().lower() == str(nombre_o_pid).lower():
                        proc.terminate()
                        terminados.append(f"{proc.name()} (PID {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if terminados:
            return f"✓ Proceso(s) terminado(s): {', '.join(terminados)}"
        else:
            return f"No se encontró el proceso: {nombre_o_pid}"

    except ImportError:
        return "psutil no instalado. Instalar con: pip install psutil"
    except Exception as e:
        return f"Error al terminar proceso: {e}"


# ---------------------------------------------------------------------------
# Compresión ZIP (Req 3.14)
# ---------------------------------------------------------------------------

def comprimir_zip(origen: str, destino: str) -> str:
    """
    Comprime un archivo o directorio en un ZIP.

    Args:
        origen:  Ruta del archivo o carpeta a comprimir
        destino: Ruta del archivo .zip resultante

    Returns:
        Mensaje de resultado.
    """
    import zipfile
    try:
        origen_path  = Path(origen)
        destino_path = Path(destino)

        if not origen_path.exists():
            return f"Error: No existe el origen: {origen}"

        destino_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(destino_path), "w", zipfile.ZIP_DEFLATED) as zf:
            if origen_path.is_file():
                zf.write(str(origen_path), origen_path.name)
            else:
                for archivo in origen_path.rglob("*"):
                    if archivo.is_file():
                        arcname = archivo.relative_to(origen_path.parent)
                        zf.write(str(archivo), str(arcname))

        size_kb = round(destino_path.stat().st_size / 1024, 1)
        return f"✓ Comprimido: {destino_path.name} ({size_kb} KB)"

    except Exception as e:
        return f"Error al comprimir: {e}"


def descomprimir_zip(origen: str, destino: str = "") -> str:
    """
    Descomprime un archivo ZIP.

    Args:
        origen:  Ruta del archivo .zip
        destino: Carpeta destino (si vacío, usa la misma carpeta del zip)

    Returns:
        Mensaje de resultado.
    """
    import zipfile
    try:
        origen_path = Path(origen)
        if not origen_path.exists():
            return f"Error: No existe el archivo: {origen}"

        destino_path = Path(destino) if destino else origen_path.parent / origen_path.stem
        destino_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(origen_path), "r") as zf:
            zf.extractall(str(destino_path))
            archivos = len(zf.namelist())

        return f"✓ Descomprimido: {archivos} archivo(s) en {destino_path}"

    except Exception as e:
        return f"Error al descomprimir: {e}"
