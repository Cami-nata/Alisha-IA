"""
Alisha_IA.py — Script maestro unificado.

Inicia TODO en un solo proceso:
  - Servidor web (Flask + SocketIO) con Watchdog de auto-restart
  - Modelo Live2D (desktop_widget.py)
  - Ícono en bandeja del sistema

Uso:
    python Alisha_IA.py           # normal
    python Alisha_IA.py --install # instalar en inicio de Windows
    python Alisha_IA.py --remove  # quitar del inicio de Windows
"""
import argparse
import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

BASE_DIR  = Path(__file__).parent
NOMBRE    = "Alisha IA"
CRASH_LOG = BASE_DIR / "crash_log.txt"
DEBUG_LOG = BASE_DIR / "alisha_debug.log"
PORT      = 5000

# Suprimir ventana de pygame/SDL antes de cualquier import de audio
import os as _os_sdl
_os_sdl.environ.setdefault("SDL_VIDEODRIVER", "dummy")
_os_sdl.environ.setdefault("SDL_AUDIODRIVER", "directsound")

# ── Redirección de logs a archivo (modo invisible) ────────────────────────────
def _redirigir_logs():
    try:
        if sys.stdout is None or not hasattr(sys.stdout, 'write'):
            _log_f = open(DEBUG_LOG, "a", encoding="utf-8", buffering=1)
            sys.stdout = _log_f
            sys.stderr = _log_f
    except Exception:
        pass

_redirigir_logs()

# ── Crash logger ──────────────────────────────────────────────────────────────
def _log_crash(origen: str, exc: Exception) -> None:
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb = traceback.format_exc()
        linea = f"\n{'='*60}\n[{ts}] CRASH en {origen}\n{tb}\n"
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(linea)
        print(f"[CrashLog] ✓ Error guardado en crash_log.txt")
    except Exception:
        pass

# ── Ocultar consola ───────────────────────────────────────────────────────────
def _ocultar_consola():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass
    try:
        APP_ID = "AlishaIA.Live2D.Assistant.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

# ── Autostart de Windows ──────────────────────────────────────────────────────
_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "AlishaIA"

def _ruta_startup() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "AlishaIA.bat"

def instalar_autostart():
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    exe = str(pythonw) if pythonw.exists() else sys.executable
    script = str(BASE_DIR / "Alisha_IA.py")
    valor = f'"{exe}" "{script}"'
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, valor)
        print(f"✓ Alisha en el registro de Windows (HKCU\\...\\Run\\{_REG_NAME})")
    except Exception as e:
        print(f"⚠ Registro falló ({e}), usando carpeta Startup como fallback")
        bat = _ruta_startup()
        bat.write_text(f'@echo off\nstart "" /B "{exe}" "{script}"\n', encoding="utf-8")
        print(f"✓ Alisha en Startup: {bat}")

def remover_autostart():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _REG_NAME)
        print("✓ Alisha removida del registro de Windows.")
    except Exception:
        pass
    bat = _ruta_startup()
    if bat.exists():
        bat.unlink()
        print("✓ Alisha removida de la carpeta Startup.")

# ── Iniciar modelo Live2D en proceso separado ─────────────────────────────────

def _esperar_servidor(url: str = f"http://localhost:{PORT}", timeout_s: float = 15.0) -> bool:
    """Espera hasta que el servidor Flask esté disponible. Retorna True si OK."""
    import urllib.request as _urllib_req
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            _urllib_req.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    print(f"[Chat] Servidor no disponible tras {timeout_s:.0f}s")
    return False


def abrir_chat_nativo(url: str = f"http://localhost:{PORT}") -> None:
    """
    Abre la interfaz de chat en ventana nativa pywebview.
    Corre en hilo daemon para no bloquear el loop GLFW.
    Fallback a webbrowser si pywebview no está disponible.
    """
    def _run():
        if not _esperar_servidor(url):
            return
        try:
            import pywebview
            pywebview.create_window(
                title="Alisha IA",
                url=url,
                frameless=False,
            )
            pywebview.start()
        except ImportError:
            import webbrowser
            print("[Chat] pywebview no disponible — abriendo en navegador")
            webbrowser.open(url)
        except Exception as e:
            print(f"[Chat] Error abriendo ventana nativa: {e}")
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True, name="NativeWindow")
    t.start()


def _iniciar_live2d():
    """
    Lanza cabina_virtual.py (live2d-py + GLFW) — sistema principal que funciona.
    Si falla, intenta desktop_widget.py como fallback.
    """
    log_path = BASE_DIR / "alisha_debug.log"
    python_exe = Path(sys.executable).parent / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    STARTF_USESHOWWINDOW = 0x00000001
    SW_HIDE = 0
    si = subprocess.STARTUPINFO()
    si.dwFlags = STARTF_USESHOWWINDOW
    si.wShowWindow = SW_HIDE

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Sistema principal: cabina_virtual.py (live2d-py + GLFW — probado y funciona)
    cabina = BASE_DIR / "cabina_virtual.py"
    if cabina.exists():
        try:
            lf = open(log_path, "a", encoding="utf-8", errors="replace")
            subprocess.Popen(
                [str(python_exe), str(cabina)],
                cwd=str(BASE_DIR),
                startupinfo=si,
                stdout=lf,
                stderr=lf,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print("[Alisha] ✓ Modelo Live2D iniciado (cabina_virtual)")
            return
        except Exception as e:
            _log_crash("_iniciar_live2d/cabina_virtual", e)

    # Fallback: desktop_widget.py (PyQt6 + WebEngine)
    desktop = BASE_DIR / "desktop_widget.py"
    if desktop.exists():
        try:
            lf = open(log_path, "a", encoding="utf-8", errors="replace")
            subprocess.Popen(
                [str(python_exe), str(desktop)],
                cwd=str(BASE_DIR),
                startupinfo=si,
                stdout=lf,
                stderr=lf,
                env=env,
            )
            print("[Alisha] ✓ Modelo Live2D iniciado (desktop_widget fallback)")
        except Exception as e:
            _log_crash("_iniciar_live2d/desktop_widget", e)

# ── Servidor web con Watchdog ─────────────────────────────────────────────────
_servidor_activo = threading.Event()

def _arrancar_servidor_una_vez() -> bool:
    try:
        from web_app import app, socketio, _inicializar
        _inicializar()

        try:
            from alisha_analitica import start_alisha_analitica
            from memory import cargar_memoria
            mem = cargar_memoria()
            user = mem.get("perfil", {}).get("nombre", "Camila")
            start_alisha_analitica(user)
        except Exception:
            pass

        print(f"[Alisha] ✓ Servidor web en localhost:{PORT}")
        _servidor_activo.set()
        socketio.run(
            app,
            host="127.0.0.1",
            port=PORT,
            debug=False,
            allow_unsafe_werkzeug=True,
            use_reloader=False,
        )
        return True
    except Exception as e:
        _log_crash("_arrancar_servidor_una_vez", e)
        return False

def _iniciar_web_con_watchdog():
    intentos = 0
    MAX_INTENTOS = 10
    ESPERA = 3.0

    while intentos < MAX_INTENTOS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", PORT)) == 0:
                print(f"[Watchdog] Puerto {PORT} ya en uso — servidor ya corriendo")
                _servidor_activo.set()
                return

        intentos += 1
        print(f"[Watchdog] Arrancando servidor (intento {intentos}/{MAX_INTENTOS})...")
        _servidor_activo.clear()

        try:
            _arrancar_servidor_una_vez()
        except Exception as e:
            _log_crash(f"Watchdog intento {intentos}", e)

        print(f"[Watchdog] ⚠ Servidor caído — reiniciando en {ESPERA}s...")
        time.sleep(ESPERA)

    print("[Watchdog] ❌ Servidor no pudo arrancar después de 10 intentos.")

# ── Ícono en bandeja del sistema ──────────────────────────────────────────────
def _iniciar_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
        import webbrowser

        ico_path = BASE_DIR / "alisha.ico"
        if ico_path.exists():
            img = Image.open(ico_path).convert("RGBA").resize((64, 64))
        else:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([2, 2, 62, 62], fill=(0, 180, 210, 255))
            draw.ellipse([8, 8, 56, 56], fill=(0, 229, 255, 255))
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 36)
                draw.text((18, 12), "A", font=font, fill=(255, 255, 255, 255))
            except Exception:
                draw.ellipse([22, 22, 42, 42], fill=(255, 255, 255, 200))

        def on_abrir_chat(icon, item):
            abrir_chat_nativo(f"http://localhost:{PORT}")

        def on_abrir_config(icon, item):
            webbrowser.open(f"http://localhost:{PORT}/config")

        def on_mostrar_modelo(icon, item):
            _iniciar_live2d()

        def on_ver_log(icon, item):
            try:
                os.startfile(str(CRASH_LOG))
            except Exception:
                pass

        def on_cerrar(icon, item):
            icon.stop()
            try:
                import web_app as _wa
                if _wa._agent_loop is not None:
                    _wa._agent_loop.stop()
            except Exception:
                pass
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("💬 Abrir chat",        on_abrir_chat),
            pystray.MenuItem("🎭 Mostrar modelo 2D", on_mostrar_modelo),
            pystray.MenuItem("⚙️ Configuración",     on_abrir_config),
            pystray.MenuItem("📋 Ver crash log",     on_ver_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Cerrar Alisha",     on_cerrar),
        )
        icon = pystray.Icon(NOMBRE, img, NOMBRE, menu)
        icon.default_action = on_abrir_chat
        icon.run()
    except Exception as e:
        _log_crash("_iniciar_tray", e)
        while True:
            time.sleep(60)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Alisha IA — Sistema unificado")
    parser.add_argument("--install", action="store_true", help="Instalar en inicio de Windows")
    parser.add_argument("--remove",  action="store_true", help="Quitar del inicio de Windows")
    args = parser.parse_args()

    if args.install:
        instalar_autostart()
        return
    if args.remove:
        remover_autostart()
        return

    # ── Single Instance Lock — evitar que se abra doble ──────────────────────
    import tempfile, atexit
    lock_path = Path(tempfile.gettempdir()) / "alisha.lock"

    # Verificar si ya hay una instancia corriendo
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            import psutil
            if psutil.pid_exists(pid):
                print(f"[Alisha] Ya hay una instancia corriendo (PID {pid}). Cerrando.")
                return
        except Exception:
            pass  # lock viejo o corrupto — continuar

    # Crear lock con nuestro PID
    lock_path.write_text(str(os.getpid()))
    atexit.register(lambda: lock_path.unlink(missing_ok=True))

    _ocultar_consola()
    print(f"🎭 {NOMBRE} — Iniciando sistema unificado...")

    _agent_loop_instance = None

    def _al_despertar():
        nonlocal _agent_loop_instance
        print("[Alisha] ✨ Despertando — cargando módulos pesados...")
        try:
            from agent_loop import AgentLoop
            _agent_loop_instance = AgentLoop()
            _agent_loop_instance.start()
            print("[Alisha] ✓ AgentLoop iniciado (post-despertar)")
        except Exception as e:
            _log_crash("AgentLoop post-despertar", e)
        try:
            import web_app as _wa
            _wa._agent_loop = _agent_loop_instance
        except Exception:
            pass

    # 1. Servidor web con Watchdog (hilo no daemon)
    t_web = threading.Thread(target=_iniciar_web_con_watchdog, daemon=False, name="WebWatchdog")
    t_web.start()

    # Esperar a que el servidor esté listo (máx 15s)
    if not _servidor_activo.wait(timeout=15):
        print("[Alisha] ⚠ Servidor tardó más de lo esperado — continuando igual")

    # 2. Modelo Live2D en proceso separado
    _iniciar_live2d()

    # 3. Sistema de sueño
    _sistema_sueno = None
    try:
        from alisha_sleep import get_sistema_sueno
        _sistema_sueno = get_sistema_sueno(callback=_al_despertar)
        _sistema_sueno.iniciar_modo_dormida()
        print("[Alisha] 😴 Modo dormida activado — esperando actividad del usuario")
    except Exception as e:
        _log_crash("SistemaSueno", e)
        _al_despertar()

    # 4. Exponer sistema de sueño en web_app
    try:
        import web_app as _web_app
        _web_app._sistema_sueno = _sistema_sueno
    except Exception:
        pass

    # 5. Ícono en bandeja (bloquea hasta cerrar)
    _iniciar_tray()


if __name__ == "__main__":
    main()
