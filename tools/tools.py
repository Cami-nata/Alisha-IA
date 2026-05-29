"""
tools.py — Definición unificada de herramientas para Alisha (Function Calling).

Cada herramienta tiene:
- nombre: identificador único
- descripcion: qué hace (para el prompt del LLM)
- parametros: schema de parámetros
- ejecutar(): función que la ejecuta
- critica: si requiere confirmación visual antes de ejecutar

Integración con el sistema existente:
- Reutiliza actions.py, actions_system.py, agent_actions.py, browser_agent.py
- Respeta safety_guard.py para acciones críticas
- Emite señales Live2D durante ejecución (ojos moviéndose, respiración)
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

# pyautogui — escritura de texto y control de teclado seguro
try:
    import pyautogui as _pyautogui
    _pyautogui.FAILSAFE = True   # mover mouse a esquina superior izquierda = abort
    _pyautogui.PAUSE    = 0.05   # pausa mínima entre acciones (evita spam)
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

# ---------------------------------------------------------------------------
# Estado de ejecución de herramientas (para feedback Live2D)
# ---------------------------------------------------------------------------

_tool_running = threading.Event()   # True mientras una herramienta está corriendo
_tool_name    = ""                  # nombre de la herramienta activa


def _set_tool_running(nombre: str) -> None:
    global _tool_name
    _tool_name = nombre
    _tool_running.set()
    # Escribir en chibi_state.json para que el Live2D reaccione
    _emit_tool_state(nombre, running=True)


def _set_tool_done() -> None:
    global _tool_name
    _tool_name = ""
    _tool_running.clear()
    _emit_tool_state("", running=False)


def _emit_tool_state(nombre: str, running: bool) -> None:
    """Escribe en chibi_state.json el estado de ejecución de herramienta."""
    try:
        from assistant_state import STATE_FILE
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        data["tool_running"] = running
        data["tool_name"]    = nombre
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def is_tool_running() -> bool:
    return _tool_running.is_set()


def get_running_tool() -> str:
    return _tool_name


# ---------------------------------------------------------------------------
# Clase base de herramienta
# ---------------------------------------------------------------------------

class Tool:
    """Herramienta que Alisha puede usar de forma autónoma."""

    def __init__(
        self,
        nombre: str,
        descripcion: str,
        parametros: dict,
        critica: bool = False,
    ):
        self.nombre      = nombre
        self.descripcion = descripcion
        self.parametros  = parametros
        self.critica     = critica  # requiere confirmación visual

    def ejecutar(self, **kwargs) -> str:
        raise NotImplementedError

    def ejecutar_con_feedback(self, **kwargs) -> str:
        """Ejecuta la herramienta con feedback visual Live2D."""
        _set_tool_running(self.nombre)
        try:
            resultado = self.ejecutar(**kwargs)
            return resultado
        finally:
            _set_tool_done()

    def schema_para_prompt(self) -> str:
        """Retorna la descripción de la herramienta para el prompt del LLM."""
        params_str = ", ".join(
            f"{k}: {v}" for k, v in self.parametros.items()
        )
        critica_str = " [REQUIERE CONFIRMACIÓN]" if self.critica else ""
        return f"- {self.nombre}({params_str}): {self.descripcion}{critica_str}"


# ---------------------------------------------------------------------------
# file_manager — Leer, escribir y editar archivos
# ---------------------------------------------------------------------------

class FileReadTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="file_read",
            descripcion="Lee el contenido de un archivo (.py, .txt, .docx, .md, .json, .csv)",
            parametros={"ruta": "str — ruta del archivo"},
            critica=False,
        )

    def ejecutar(self, ruta: str, **_) -> str:
        try:
            p = Path(ruta)
            if not p.exists():
                return f"Archivo no encontrado: {ruta}"
            if p.suffix.lower() == ".docx":
                try:
                    from docx import Document
                    doc = Document(str(p))
                    return "\n".join(par.text for par in doc.paragraphs)[:5000]
                except Exception as e:
                    return f"Error leyendo .docx: {e}"
            return p.read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception as e:
            return f"Error: {e}"


class FileWriteTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="file_write",
            descripcion="Crea o sobreescribe un archivo con el contenido dado",
            parametros={
                "ruta":      "str — ruta del archivo a crear",
                "contenido": "str — contenido a escribir",
            },
            critica=True,
        )

    def ejecutar(self, ruta: str, contenido: str, **_) -> str:
        try:
            from safety_guard import get_guard
            guard = get_guard()
            accion = {"accion": "crear_archivo", "ruta": ruta}
            puede, razon = guard.verificar_accion(accion)
            if not puede:
                return f"Bloqueado por seguridad: {razon}"
            p = Path(ruta)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenido, encoding="utf-8")
            return f"Archivo guardado: {ruta} ({len(contenido)} caracteres)"
        except Exception as e:
            return f"Error: {e}"


class FileEditTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="file_edit",
            descripcion="Edita un archivo reemplazando texto específico",
            parametros={
                "ruta":       "str — ruta del archivo",
                "buscar":     "str — texto a buscar",
                "reemplazar": "str — texto de reemplazo",
            },
            critica=True,
        )

    def ejecutar(self, ruta: str, buscar: str, reemplazar: str, **_) -> str:
        try:
            from safety_guard import get_guard
            guard = get_guard()
            accion = {"accion": "editar_archivo", "ruta": ruta}
            puede, razon = guard.verificar_accion(accion)
            if not puede:
                return f"Bloqueado por seguridad: {razon}"
            p = Path(ruta)
            if not p.exists():
                return f"Archivo no encontrado: {ruta}"
            contenido = p.read_text(encoding="utf-8", errors="ignore")
            if buscar not in contenido:
                return f"Texto no encontrado en {ruta}: '{buscar[:50]}'"
            nuevo = contenido.replace(buscar, reemplazar, 1)
            p.write_text(nuevo, encoding="utf-8")
            return f"Archivo editado: {ruta}"
        except Exception as e:
            return f"Error: {e}"


class FileDeleteTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="file_delete",
            descripcion="Elimina un archivo (solo archivos del usuario, no del sistema)",
            parametros={"ruta": "str — ruta del archivo a eliminar"},
            critica=True,
        )

    def ejecutar(self, ruta: str, **_) -> str:
        try:
            from safety_guard import get_guard, RUTAS_PROHIBIDAS
            guard = get_guard()
            accion = {"accion": "eliminar_archivo", "ruta": ruta}
            puede, razon = guard.verificar_accion(accion)
            if not puede:
                return f"Bloqueado por seguridad: {razon}"
            # Verificar rutas prohibidas
            ruta_abs = str(Path(ruta).resolve())
            for prohibida in RUTAS_PROHIBIDAS:
                if ruta_abs.lower().startswith(prohibida.lower()):
                    return f"No puedo eliminar archivos en {prohibida}"
            p = Path(ruta)
            if not p.exists():
                return f"Archivo no encontrado: {ruta}"
            p.unlink()
            return f"Archivo eliminado: {ruta}"
        except Exception as e:
            return f"Error: {e}"


# ---------------------------------------------------------------------------
# web_search — Búsqueda web en tiempo real
# ---------------------------------------------------------------------------

class WebSearchTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="web_search",
            descripcion="Busca información en internet y retorna un resumen de los resultados",
            parametros={"query": "str — consulta de búsqueda"},
            critica=True,   # requiere confirmación — evita búsquedas autónomas no solicitadas
        )

    def ejecutar(self, query: str, **_) -> str:
        # Método 1: DuckDuckGo (sin API key, sin Playwright)
        resultado = self._buscar_duckduckgo(query)
        if resultado:
            return resultado
        # Método 2: Playwright como fallback
        return self._buscar_playwright(query)

    def _buscar_duckduckgo(self, query: str) -> str:
        """Búsqueda via DuckDuckGo Instant Answer API (sin key)."""
        try:
            import urllib.request
            import urllib.parse
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Alisha/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:  # 5s timeout
                data = json.loads(resp.read().decode("utf-8"))

            partes = []
            # Respuesta abstracta
            abstract = data.get("AbstractText", "").strip()
            if abstract:
                partes.append(f"Resumen: {abstract[:500]}")
            # Respuesta directa
            answer = data.get("Answer", "").strip()
            if answer:
                partes.append(f"Respuesta directa: {answer}")
            # Resultados relacionados
            related = data.get("RelatedTopics", [])[:3]
            for r in related:
                if isinstance(r, dict) and r.get("Text"):
                    partes.append(f"• {r['Text'][:200]}")

            if partes:
                return f"Búsqueda: '{query}'\n" + "\n".join(partes)
            return ""
        except Exception:
            return ""

    def _buscar_playwright(self, query: str) -> str:
        """Fallback: búsqueda via Playwright."""
        try:
            from browser_agent import BrowserAgent
            agent = BrowserAgent.get_instance()
            resultado = agent.buscar_en_google(query)
            time.sleep(2)
            contenido = agent.leer_pagina()
            return f"Búsqueda: '{query}'\n{contenido[:1000]}"
        except Exception as e:
            return f"No pude buscar '{query}': {e}"


class WebReadTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="web_read",
            descripcion="Lee el contenido de una página web específica",
            parametros={"url": "str — URL de la página a leer"},
            critica=True,   # requiere confirmación — evita navegación autónoma
        )

    def ejecutar(self, url: str, **_) -> str:
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            # Extraer texto limpio
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:2000]
        except Exception as e:
            # Fallback a Playwright
            try:
                from browser_agent import BrowserAgent
                agent = BrowserAgent.get_instance()
                agent.abrir_url(url)
                time.sleep(2)
                return agent.leer_pagina()
            except Exception:
                return f"No pude leer {url}: {e}"


# ---------------------------------------------------------------------------
# system_control — Abrir/cerrar apps, volumen, etc.
# ---------------------------------------------------------------------------

class AppOpenTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="app_open",
            descripcion="Abre una aplicación del sistema (chrome, vscode, word, spotify, etc.)",
            parametros={"app": "str — nombre de la aplicación"},
            critica=False,
        )

    def ejecutar(self, app: str, **_) -> str:
        try:
            from actions import abrir_app
            abrir_app(app)
            return f"Aplicación abierta: {app}"
        except Exception as e:
            return f"No pude abrir {app}: {e}"


class AppCloseTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="app_close",
            descripcion="Cierra una aplicación por nombre de proceso",
            parametros={"proceso": "str — nombre del proceso (ej: chrome.exe, notepad.exe)"},
            critica=True,
        )

    def ejecutar(self, proceso: str, **_) -> str:
        try:
            import subprocess
            from safety_guard import APPS_PROTEGIDAS
            if proceso.lower() in APPS_PROTEGIDAS:
                return f"No puedo cerrar {proceso} por seguridad."
            subprocess.run(["taskkill", "/f", "/im", proceso], capture_output=True)
            return f"Proceso cerrado: {proceso}"
        except Exception as e:
            return f"Error cerrando {proceso}: {e}"


class VolumeTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="volume_control",
            descripcion="Controla el volumen del sistema (subir, bajar, silenciar, establecer 0-100)",
            parametros={
                "accion": "str — subir|bajar|silenciar|restaurar|establecer",
                "valor":  "int (opcional) — 0-100 para establecer",
            },
            critica=False,
        )

    def ejecutar(self, accion: str, valor: int = None, **_) -> str:
        try:
            from actions_system import controlar_volumen
            return controlar_volumen(accion, valor)
        except Exception as e:
            return f"Error controlando volumen: {e}"


class SystemInfoTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="system_info",
            descripcion="Obtiene información del sistema: CPU, RAM, disco, procesos activos",
            parametros={},
            critica=False,
        )

    def ejecutar(self, **_) -> str:
        try:
            from actions import diagnosticar_pc
            return diagnosticar_pc()
        except Exception as e:
            return f"Error obteniendo info del sistema: {e}"


class RunCodeTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="run_code",
            descripcion="Ejecuta código Python de forma segura en un sandbox",
            parametros={"codigo": "str — código Python a ejecutar"},
            critica=True,
        )

    def ejecutar(self, codigo: str, **_) -> str:
        try:
            from actions_system import ejecutar_codigo_seguro
            return ejecutar_codigo_seguro(codigo)
        except Exception as e:
            return f"Error ejecutando código: {e}"


class ManageCVTool(Tool):
    """Herramienta específica para gestión del CV de Camila."""

    def __init__(self):
        super().__init__(
            nombre="manage_cv",
            descripcion=(
                "Gestiona el CV de Camila: leer, actualizar secciones, "
                "agregar experiencia, formatear para LinkedIn o PDF"
            ),
            parametros={
                "accion":    "str — leer|actualizar|agregar_experiencia|formatear|buscar_cv",
                "seccion":   "str (opcional) — sección a modificar (experiencia, habilidades, etc.)",
                "contenido": "str (opcional) — contenido nuevo a agregar",
            },
            critica=False,
        )

    def ejecutar(self, accion: str, seccion: str = "", contenido: str = "", **_) -> str:
        try:
            if accion == "buscar_cv":
                return self._buscar_cv()
            elif accion == "leer":
                return self._leer_cv()
            elif accion == "actualizar":
                return self._actualizar_cv(seccion, contenido)
            elif accion == "agregar_experiencia":
                return self._agregar_experiencia(contenido)
            elif accion == "formatear":
                return self._formatear_cv(seccion)
            else:
                return f"Acción de CV desconocida: {accion}"
        except Exception as e:
            return f"Che, algo salió mal con el CV: {e}"

    def _buscar_cv(self) -> str:
        """Busca archivos de CV en el sistema."""
        try:
            from actions_system import buscar_archivo
            rutas = buscar_archivo("cv", directorio=None)
            if not rutas:
                rutas = buscar_archivo("curriculum", directorio=None)
            if rutas:
                return "Encontré estos archivos de CV:\n" + "\n".join(rutas[:5])
            return "No encontré ningún archivo de CV. ¿Cómo se llama el archivo?"
        except Exception as e:
            return f"No pude buscar el CV: {e}"

    def _leer_cv(self) -> str:
        """Lee el CV más reciente encontrado."""
        try:
            from pathlib import Path
            # Buscar en lugares comunes
            lugares = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "Downloads",
            ]
            for lugar in lugares:
                for patron in ["*cv*", "*curriculum*", "*CV*"]:
                    archivos = list(lugar.glob(patron + ".docx")) + \
                               list(lugar.glob(patron + ".pdf")) + \
                               list(lugar.glob(patron + ".txt"))
                    if archivos:
                        archivo = max(archivos, key=lambda p: p.stat().st_mtime)
                        lector = FileReadTool()
                        return f"CV encontrado: {archivo}\n\n" + lector.ejecutar(ruta=str(archivo))
            return "No encontré el CV. Decime dónde está y lo leo."
        except Exception as e:
            return f"No pude leer el CV: {e}"

    def _actualizar_cv(self, seccion: str, contenido: str) -> str:
        if not seccion or not contenido:
            return "Necesito saber qué sección actualizar y con qué contenido."
        return f"Para actualizar la sección '{seccion}' del CV, necesito la ruta del archivo. ¿Me la pasás?"

    def _agregar_experiencia(self, contenido: str) -> str:
        if not contenido:
            return "¿Qué experiencia querés agregar? Describila y la formateo."
        # Formatear la experiencia
        return (
            f"Experiencia formateada para CV:\n\n"
            f"**[Cargo] | [Empresa] | [Fecha inicio] – [Fecha fin]**\n"
            f"• {contenido}\n\n"
            f"¿Querés que la agregue al archivo? Decime la ruta del CV."
        )

    def _formatear_cv(self, formato: str = "linkedin") -> str:
        if formato == "linkedin":
            return (
                "Para LinkedIn, el CV debe tener:\n"
                "• Resumen profesional (3-4 líneas)\n"
                "• Experiencia con logros cuantificables\n"
                "• Habilidades técnicas como keywords\n"
                "• Educación con fechas\n\n"
                "¿Querés que revise tu CV actual y te diga qué mejorar?"
            )
        return f"Formato '{formato}' no reconocido. Usá: linkedin, pdf, word"


# ---------------------------------------------------------------------------
# screenshot, clipboard, window_manager, brightness (FASE 11 — JCySharp)
# ---------------------------------------------------------------------------

class ScreenshotTool(Tool):
    """Captura de pantalla — guarda, copia al portapapeles o analiza con Gemini."""

    def __init__(self):
        super().__init__(
            nombre="screenshot",
            descripcion="Toma una captura de pantalla: guardar en archivo, copiar al portapapeles o analizar con IA",
            parametros={
                "accion": "str — guardar|portapapeles|analizar",
                "ruta":   "str (opcional) — ruta donde guardar (solo para 'guardar')",
            },
            critica=False,
        )

    def ejecutar(self, accion: str = "guardar", ruta: str = "", **_) -> str:
        try:
            import pyautogui as _pag
            from PIL import Image as _PILImg
            import io as _io
            from datetime import datetime as _dt

            # Capturar pantalla completa con pyautogui (sin mss)
            img = _pag.screenshot()

            if accion == "guardar":
                if not ruta:
                    from pathlib import Path
                    ruta = str(Path.home() / "Desktop" /
                               f"screenshot_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png")
                img.save(ruta)
                return f"Captura guardada en: {ruta}"

            elif accion == "portapapeles":
                try:
                    import win32clipboard
                    output = _io.BytesIO()
                    img.save(output, "BMP")
                    data = output.getvalue()[14:]
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    win32clipboard.CloseClipboard()
                    return "Captura copiada al portapapeles"
                except ImportError:
                    return "win32clipboard no disponible — guardá la captura con accion='guardar'"

            elif accion == "analizar":
                output = _io.BytesIO()
                img.save(output, "JPEG", quality=70)
                img_bytes = output.getvalue()
                try:
                    from gemini_vision import GeminiVision
                    gv = GeminiVision()
                    descripcion = gv._analyze(img_bytes)
                    return descripcion or "No pude analizar la imagen con Gemini."
                except Exception as e:
                    return f"Gemini no disponible para analizar: {e}"

            return f"Acción desconocida: {accion}. Usá: guardar, portapapeles, analizar"
        except Exception as e:
            return f"Error con captura: {e}"


class ClipboardTool(Tool):
    """Lee o escribe en el portapapeles del sistema."""

    def __init__(self):
        super().__init__(
            nombre="clipboard",
            descripcion="Lee o escribe texto en el portapapeles del sistema",
            parametros={
                "accion":    "str — leer|escribir|limpiar",
                "contenido": "str (opcional) — texto a escribir",
            },
            critica=False,
        )

    def ejecutar(self, accion: str = "leer", contenido: str = "", **_) -> str:
        try:
            import pyperclip
            if accion == "leer":
                texto = pyperclip.paste()
                if not texto:
                    return "El portapapeles está vacío."
                return f"Portapapeles: {texto[:500]}{'...' if len(texto) > 500 else ''}"
            elif accion == "escribir":
                if not contenido:
                    return "Necesito el contenido a escribir."
                pyperclip.copy(contenido)
                return f"Texto copiado al portapapeles ({len(contenido)} caracteres)"
            elif accion == "limpiar":
                pyperclip.copy("")
                return "Portapapeles limpiado"
            return f"Acción desconocida: {accion}. Usá: leer, escribir, limpiar"
        except Exception as e:
            return f"Error con portapapeles: {e}"


class WindowManagerTool(Tool):
    """Gestiona ventanas abiertas: listar, maximizar, minimizar, snap."""

    def __init__(self):
        super().__init__(
            nombre="window_manager",
            descripcion="Gestiona ventanas: listar abiertas, maximizar, minimizar, snap izquierda/derecha, cerrar",
            parametros={
                "accion": "str — listar|maximizar|minimizar|snap_izquierda|snap_derecha|cerrar",
                "titulo": "str (opcional) — título parcial de la ventana a gestionar",
            },
            critica=False,
        )

    def ejecutar(self, accion: str = "listar", titulo: str = "", **_) -> str:
        try:
            import win32gui
            import win32con

            if accion == "listar":
                ventanas: list[str] = []

                def _enum(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        t = win32gui.GetWindowText(hwnd)
                        if t and len(t) > 2:
                            ventanas.append(t)

                win32gui.EnumWindows(_enum, None)
                if not ventanas:
                    return "No encontré ventanas visibles."
                return "Ventanas abiertas:\n" + "\n".join(f"• {v}" for v in ventanas[:15])

            # Para las demás acciones necesitamos encontrar la ventana
            if not titulo:
                return f"Para '{accion}' necesito el título parcial de la ventana."

            hwnd_found = [None]

            def _find(hwnd, _):
                if hwnd_found[0]:
                    return
                t = win32gui.GetWindowText(hwnd)
                if titulo.lower() in t.lower() and win32gui.IsWindowVisible(hwnd):
                    hwnd_found[0] = hwnd

            win32gui.EnumWindows(_find, None)
            hwnd = hwnd_found[0]

            if not hwnd:
                return f"No encontré ninguna ventana con '{titulo}'"

            nombre_ventana = win32gui.GetWindowText(hwnd)

            if accion == "maximizar":
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return f"Ventana maximizada: {nombre_ventana}"
            elif accion == "minimizar":
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return f"Ventana minimizada: {nombre_ventana}"
            elif accion == "snap_izquierda":
                win32gui.SetForegroundWindow(hwnd)
                import pyautogui
                pyautogui.hotkey("win", "left")
                return f"Ventana anclada a la izquierda: {nombre_ventana}"
            elif accion == "snap_derecha":
                win32gui.SetForegroundWindow(hwnd)
                import pyautogui
                pyautogui.hotkey("win", "right")
                return f"Ventana anclada a la derecha: {nombre_ventana}"
            elif accion == "cerrar":
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return f"Señal de cierre enviada a: {nombre_ventana}"

            return f"Acción desconocida: {accion}"
        except ImportError:
            return "win32gui no disponible — instalá pywin32"
        except Exception as e:
            return f"Error gestionando ventana: {e}"


class BrightnessTool(Tool):
    """Controla el brillo de la pantalla (0-100)."""

    def __init__(self):
        super().__init__(
            nombre="brightness",
            descripcion="Controla el brillo de la pantalla del sistema (0-100)",
            parametros={"valor": "int — nivel de brillo de 0 a 100"},
            critica=False,
        )

    def ejecutar(self, valor: int = 70, **_) -> str:
        try:
            valor = max(0, min(100, int(valor)))
            import subprocess
            # PowerShell WMI — funciona en la mayoría de laptops con Windows
            cmd = (
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{valor})"
            )
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", cmd],
                capture_output=True, timeout=5, text=True
            )
            if result.returncode == 0:
                return f"Brillo ajustado a {valor}%"
            # Fallback: screen_brightness_control si está instalado
            try:
                import screen_brightness_control as sbc
                sbc.set_brightness(valor)
                return f"Brillo ajustado a {valor}% (via sbc)"
            except ImportError:
                pass
            return f"No pude ajustar el brillo (código {result.returncode}). En laptops puede requerir permisos de administrador."
        except Exception as e:
            return f"Error ajustando brillo: {e}"


# ---------------------------------------------------------------------------
# Registro global de herramientas
# ---------------------------------------------------------------------------

_TOOLS: dict[str, Tool] = {}


def _registrar_herramientas() -> None:
    global _TOOLS
    herramientas = [
        # file_manager
        FileReadTool(),
        FileWriteTool(),
        FileEditTool(),
        FileDeleteTool(),
        # web_search
        WebSearchTool(),
        WebReadTool(),
        # system_control
        AppOpenTool(),
        AppCloseTool(),
        VolumeTool(),
        SystemInfoTool(),
        RunCodeTool(),
        # CV management
        ManageCVTool(),
        # PC control avanzado (FASE 11)
        ScreenshotTool(),
        ClipboardTool(),
        WindowManagerTool(),
        BrightnessTool(),
    ]
    _TOOLS = {t.nombre: t for t in herramientas}


_registrar_herramientas()


def get_tool(nombre: str) -> Tool | None:
    return _TOOLS.get(nombre)


def get_all_tools() -> dict[str, Tool]:
    return dict(_TOOLS)


# ---------------------------------------------------------------------------
# Parsing de tool calls desde texto del LLM
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(r'TOOL_CALL:\s*(\w+)\s*\(([^)]*)\)', re.IGNORECASE)
_COORD_PARAMS = frozenset({"x", "y", "pos_x", "pos_y", "coord_x", "coord_y"})


def parsear_tool_call(texto: str) -> tuple[str, dict] | None:
    """
    Parsea un tool call en formato TOOL_CALL: nombre(k=v, ...) desde el texto del LLM.

    Retorna (nombre, params_dict) si hay match, o None si no hay ninguno.
    Los valores se parsean como pares k=v separados por comas; las comillas
    alrededor de los valores se eliminan automáticamente.
    """
    match = _TOOL_CALL_RE.search(texto)
    if not match:
        return None

    nombre = match.group(1)
    params_raw = match.group(2).strip()

    params: dict[str, str] = {}
    if params_raw:
        for par in params_raw.split(","):
            par = par.strip()
            if "=" in par:
                clave, _, valor = par.partition("=")
                clave = clave.strip()
                valor = valor.strip().strip("\"'")
                if clave:
                    params[clave] = valor

    return (nombre, params)


def _validar_params_sin_coordenadas(params: dict) -> tuple[bool, str]:
    """
    Valida que el diccionario de parámetros no contenga coordenadas de pantalla.

    Retorna (True, "") si no hay parámetros de coordenadas.
    Retorna (False, mensaje_error) si se detectan parámetros de coordenadas.
    """
    encontrados = [k for k in params if k in _COORD_PARAMS]
    if encontrados:
        return (
            False,
            f"Parámetros de coordenadas no permitidos: {', '.join(sorted(encontrados))}",
        )
    return (True, "")


def get_tools_schema() -> str:
    """Retorna el schema de todas las herramientas para inyectar en el prompt."""
    lineas = ["HERRAMIENTAS DISPONIBLES (usá tool_call cuando sea necesario):"]
    for tool in _TOOLS.values():
        lineas.append(tool.schema_para_prompt())
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Ejecutor de herramientas con seguridad y confirmación
# ---------------------------------------------------------------------------

def ejecutar_herramienta(
    nombre: str,
    params: dict,
    confirmar_callback: Callable[[str], bool] | None = None,
) -> str:
    """
    Ejecuta una herramienta por nombre con sus parámetros.
    Si es crítica, llama a confirmar_callback antes de ejecutar.
    Retorna el resultado como string.
    Fail-Silent: si algo falla, retorna mensaje en voseo rioplatense.
    """
    import random

    _FRASES_ERROR = [
        "Che, algo salió mal con eso. Seguimos igual.",
        "Mirá, no me salió. Pero no es el fin del mundo.",
        "Dale, eso no funcionó. ¿Probamos de otra forma?",
        "Uy, se rompió algo. Nada grave, seguimos.",
        "No me salió esa. ¿Querés que lo intente diferente?",
    ]

    tool = get_tool(nombre)
    if tool is None:
        return f"Che, no conozco la herramienta '{nombre}'. ¿Está bien escrito?"

    # ── Seguridad: bloquear coordenadas de píxeles ────────────────────────────
    # La IA no puede inventar x=, y= a ciegas — siempre usa nombres de app o rutas
    valido, razon_coords = _validar_params_sin_coordenadas(params)
    if not valido:
        return (
            f"Che, no puedo usar coordenadas de píxeles a ciegas. {razon_coords}. "
            f"Usá el nombre de la app o la ruta del archivo en su lugar."
        )

    # Confirmación para herramientas críticas
    if tool.critica:
        params_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in params.items())
        mensaje_confirmacion = (
            f"\n⚠️  Alisha quiere ejecutar: {nombre}({params_str})\n"
            f"   {tool.descripcion}\n"
            f"¿Confirmar? [y/N]: "
        )
        if confirmar_callback:
            aprobado = confirmar_callback(mensaje_confirmacion)
        else:
            aprobado = input(mensaje_confirmacion).strip().lower() == "y"

        if not aprobado:
            return f"Dale, no lo hago. Avisame si cambiás de idea."

    # Ejecutar con feedback Live2D
    resultado_holder = [None]
    error_holder     = [None]

    def _thread_run():
        try:
            resultado_holder[0] = tool.ejecutar_con_feedback(**params)
        except Exception as e:
            error_holder[0] = str(e)

    t = threading.Thread(target=_thread_run, daemon=True)
    t.start()
    t.join(timeout=30)

    if t.is_alive():
        _set_tool_done()
        return f"Che, {nombre} tardó demasiado. Lo dejé. ¿Querés que lo intente de nuevo?"

    if error_holder[0]:
        return random.choice(_FRASES_ERROR) + f" (Detalle: {error_holder[0][:100]})"

    return resultado_holder[0] or "Listo, pero no hubo resultado visible."

