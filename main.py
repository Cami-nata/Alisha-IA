"""
main.py — Único punto de entrada de Alisha IA.

Inicia TODO en un solo proceso:
  - Servidor web (Flask + SocketIO) con Watchdog de auto-restart
  - Modelo Live2D (cabina_virtual.py) en proceso separado
  - Ícono en bandeja del sistema

Uso:
    python main.py           # normal
    python main.py --install # instalar en inicio de Windows
    python main.py --remove  # quitar del inicio de Windows
"""
import argparse
import atexit
import ctypes
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

# Cargar configuración primero
from config.env_loader import load_env
load_env()

from config.settings import BASE_DIR, DATA_DIR

NOMBRE    = "Alisha IA"
CRASH_LOG = DATA_DIR / "crash_log.txt"
DEBUG_LOG = DATA_DIR / "alisha_debug.log"
PORT      = 5000

# Suprimir ventana de pygame/SDL
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "directsound")


# ── Crash logger ──────────────────────────────────────────────────────────────
def _log_crash(origen: str, exc: Exception) -> None:
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb = traceback.format_exc()
        linea = f"\n{'='*60}\n[{ts}] CRASH en {origen}\n{tb}\n"
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass


# ── Ocultar consola ───────────────────────────────────────────────────────────
def _ocultar_consola():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
        APP_ID = "AlishaIA.Live2D.Assistant.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


# ── Autostart de Windows ──────────────────────────────────────────────────────
_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "AlishaIA"


def instalar_autostart():
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    exe = str(pythonw) if pythonw.exists() else sys.executable
    script = str(BASE_DIR / "main.py")
    valor = f'"{exe}" "{script}"'
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, valor)
        print(f"✓ Alisha en el registro de Windows")
    except Exception as e:
        appdata = os.environ.get("APPDATA", "")
        bat = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "AlishaIA.bat"
        bat.write_text(f'@echo off\nstart "" /B "{exe}" "{script}"\n', encoding="utf-8")
        print(f"✓ Alisha en Startup: {bat}")


def remover_autostart():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _REG_NAME)
        print("✓ Alisha removida del registro.")
    except Exception:
        pass


# ── Servidor web con Watchdog ─────────────────────────────────────────────────
_servidor_activo = threading.Event()


def _arrancar_servidor_una_vez() -> bool:
    try:
        from web.web_app import app, socketio, _inicializar
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
        socketio.run(app, host="127.0.0.1", port=PORT,
                     debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
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
                print(f"[Watchdog] Puerto {PORT} ya en uso")
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


# ── Iniciar Live2D ────────────────────────────────────────────────────────────
def _iniciar_live2d():
    log_path = DATA_DIR / "alisha_debug.log"
    python_exe = Path(sys.executable).parent / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
    si = subprocess.STARTUPINFO()
    si.dwFlags = 0x00000001
    si.wShowWindow = 0
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cabina = BASE_DIR / "avatar" / "cabina_virtual.py"
    if not cabina.exists():
        cabina = BASE_DIR / "cabina_virtual.py"
    if cabina.exists():
        try:
            lf = open(log_path, "a", encoding="utf-8", errors="replace")
            subprocess.Popen([str(python_exe), str(cabina)], cwd=str(BASE_DIR),
                             startupinfo=si, stdout=lf, stderr=lf, env=env,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            print("[Alisha] ✓ Modelo Live2D iniciado")
        except Exception as e:
            _log_crash("_iniciar_live2d", e)


# ── Tray icon ─────────────────────────────────────────────────────────────────
def _iniciar_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
        import webbrowser
        ico_path = BASE_DIR / "alisha.ico"
        if ico_path.exists():
            img = Image.open(ico_path).convert("RGBA").resize((64, 64))
        else:
            img = Image.new("RGBA", (64, 64), (0, 180, 210, 255))

        def on_abrir(icon, item):
            webbrowser.open(f"http://localhost:{PORT}")

        def on_cerrar(icon, item):
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("💬 Abrir chat", on_abrir),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Cerrar Alisha", on_cerrar),
        )
        icon = pystray.Icon(NOMBRE, img, NOMBRE, menu)
        icon.default_action = on_abrir
        icon.run()
    except Exception as e:
        _log_crash("_iniciar_tray", e)
        while True:
            time.sleep(60)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Alisha IA")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--remove",  action="store_true")
    args = parser.parse_args()

    if args.install:
        instalar_autostart()
        return
    if args.remove:
        remover_autostart()
        return

    # Single instance lock
    lock_path = Path(tempfile.gettempdir()) / "alisha.lock"
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            import psutil
            if psutil.pid_exists(pid):
                print(f"[Alisha] Ya hay una instancia corriendo (PID {pid}).")
                return
        except Exception:
            pass
    lock_path.write_text(str(os.getpid()))
    atexit.register(lambda: lock_path.unlink(missing_ok=True))

    _ocultar_consola()
    print(f"🎭 {NOMBRE} — Iniciando...")

    _agent_loop_instance = None

    def _al_despertar():
        nonlocal _agent_loop_instance
        try:
            from core.agent_loop import AgentLoop
            _agent_loop_instance = AgentLoop()
            _agent_loop_instance.start()
            print("[Alisha] ✓ AgentLoop iniciado")
        except Exception as e:
            _log_crash("AgentLoop post-despertar", e)
        try:
            import web.web_app as _wa
            _wa._agent_loop = _agent_loop_instance
        except Exception:
            pass

    # 1. Servidor web
    t_web = threading.Thread(target=_iniciar_web_con_watchdog, daemon=False, name="WebWatchdog")
    t_web.start()
    if not _servidor_activo.wait(timeout=15):
        print("[Alisha] ⚠ Servidor tardó más de lo esperado")

    # 2. Live2D
    _iniciar_live2d()

    # 3. Sistema de sueño
    _sistema_sueno = None
    try:
        from alisha_sleep import get_sistema_sueno
        _sistema_sueno = get_sistema_sueno(callback=_al_despertar)
        _sistema_sueno.iniciar_modo_dormida()
        print("[Alisha] 😴 Modo dormida activado")
    except Exception as e:
        _log_crash("SistemaSueno", e)
        _al_despertar()

    try:
        import web.web_app as _web_app
        _web_app._sistema_sueno = _sistema_sueno
    except Exception:
        pass

    # 4. Canales externos (Telegram, etc.)
    _iniciar_canales()

    # 5. Tray (bloquea hasta cerrar)
    _iniciar_tray()


# ── Canales externos ──────────────────────────────────────────────────────────
def _iniciar_canales():
    """Iniciar canales externos (Telegram, etc.) en thread separado."""
    import os as _os

    telegram_enabled = _os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    if not telegram_enabled:
        return

    def _run_canales():
        import asyncio as _asyncio
        try:
            from channels.channel_router import ChannelRouter
            from channels.telegram_channel import TelegramChannel, set_router

            router = ChannelRouter()
            telegram = TelegramChannel()
            router.register_channel(telegram)
            set_router(router)

            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            loop.run_until_complete(router.start_all())
            loop.run_forever()
        except Exception as e:
            _log_crash("_iniciar_canales", e)
            print(f"[Canales] ⚠ Error iniciando canales: {e}")

    t = threading.Thread(target=_run_canales, daemon=True, name="ChannelManager")
    t.start()
    print("[Alisha] ✓ Canales externos iniciando...")


if __name__ == "__main__":
    main()
