"""
alisha_tray.py — System Tray de Alisha.

Vive en la bandeja del sistema como Lively Wallpaper.
Sin terminal visible, sin barra de tareas.

Menú:
  - Mostrar/Ocultar Alisha (Live2D)
  - Abrir Chat Web
  - Configuración
  - Salir

Uso:
    python alisha_tray.py          (con consola para debug)
    pythonw alisha_tray.pyw        (sin consola — modo silencioso)
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── Ocultar consola inmediatamente (modo silencioso) ──────────────────────────
def _ocultar_consola():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass

_ocultar_consola()

# ── Dependencias ──────────────────────────────────────────────────────────────
try:
    import pystray
    from pystray import MenuItem as Item, Menu
    _PYSTRAY_OK = True
except ImportError:
    _PYSTRAY_OK = False
    print("[Tray] ERROR: pip install pystray")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
ICON_PATH   = BASE_DIR / "static" / "img" / "chibi" / "neutral.png"
from config import DATA_DIR
STATE_FILE  = DATA_DIR / "chibi_state.json"


# ══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE ÍCONO
# ══════════════════════════════════════════════════════════════════════════════

def crear_icono() -> "Image.Image":
    """
    Carga el ícono de Alisha o genera uno programático si no existe.
    Retorna una imagen PIL 64x64.
    """
    if _PIL_OK and ICON_PATH.exists():
        try:
            img = Image.open(ICON_PATH).convert("RGBA")
            img = img.resize((64, 64), Image.LANCZOS)
            # Hacer circular (más bonito en el tray)
            mask = Image.new("L", (64, 64), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 63, 63), fill=255)
            img.putalpha(mask)
            return img
        except Exception:
            pass

    # Fallback: ícono generado programáticamente
    if _PIL_OK:
        img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Círculo de fondo degradado (rosa/lila — colores de Alisha)
        draw.ellipse((2, 2, 61, 61), fill=(220, 130, 180, 255))
        draw.ellipse((6, 6, 57, 57), fill=(240, 160, 200, 255))
        # Letra "A" centrada
        try:
            draw.text((20, 16), "A", fill=(255, 255, 255, 255))
        except Exception:
            pass
        return img

    # Sin PIL: no se puede crear ícono
    raise RuntimeError("PIL no disponible para crear ícono")


# ══════════════════════════════════════════════════════════════════════════════
# GESTOR DE PROCESOS
# ══════════════════════════════════════════════════════════════════════════════

class AlishaProcessManager:
    """Gestiona los procesos de Alisha desde el tray."""

    def __init__(self):
        self._live2d_proc:  subprocess.Popen | None = None
        self._webapp_proc:  subprocess.Popen | None = None
        self._brain_thread: threading.Thread | None = None
        self._live2d_visible = True
        self._running = False

    def start_all(self) -> None:
        """Arranca todos los sistemas de Alisha."""
        self._running = True

        # Arrancar brain + visión + audio en hilo (no bloquea el tray)
        self._brain_thread = threading.Thread(
            target=self._start_brain, daemon=True
        )
        self._brain_thread.start()

        # Arrancar Live2D
        self._start_live2d()

        # Arrancar web app
        self._start_webapp()

    def stop_all(self) -> None:
        """Detiene todos los sistemas."""
        self._running = False
        for proc in [self._live2d_proc, self._webapp_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    def toggle_live2d(self) -> str:
        """Muestra u oculta el modelo Live2D. Retorna el nuevo estado."""
        if self._live2d_proc and self._live2d_proc.poll() is None:
            # Está corriendo → terminar
            try:
                self._live2d_proc.terminate()
                self._live2d_proc.wait(timeout=3)
            except Exception:
                pass
            self._live2d_proc = None
            self._live2d_visible = False
            return "oculto"
        else:
            # No está corriendo → arrancar
            self._start_live2d()
            self._live2d_visible = True
            return "visible"

    def open_web(self) -> None:
        """Abre el chat web en el navegador."""
        webbrowser.open("http://localhost:5000")

    def is_live2d_visible(self) -> bool:
        return (
            self._live2d_proc is not None
            and self._live2d_proc.poll() is None
        )

    def _start_live2d(self) -> None:
        """Arranca cabina_virtual.py con pythonw (sin consola)."""
        if self._live2d_proc and self._live2d_proc.poll() is None:
            try:
                self._live2d_proc.terminate()
                self._live2d_proc.wait(timeout=2)
            except Exception:
                pass

        # Usar pythonw.exe para que NO aparezca en la barra de tareas
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        exe = str(pythonw) if pythonw.exists() else sys.executable

        try:
            self._live2d_proc = subprocess.Popen(
                [exe, str(BASE_DIR / "cabina_virtual.py")],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
        except Exception as e:
            print(f"[Tray] Error Live2D: {e}")

    def _start_webapp(self) -> None:
        """Arranca web_app.py con pythonw (sin consola)."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", 5000)) == 0:
                    return
        except Exception:
            pass

        pythonw = Path(sys.executable).parent / "pythonw.exe"
        exe = str(pythonw) if pythonw.exists() else sys.executable

        # Usar log file para capturar errores silenciosos
        log_path = BASE_DIR / "web_app.log"
        try:
            with open(log_path, "w") as log_f:
                self._webapp_proc = subprocess.Popen(
                    [exe, str(BASE_DIR / "web_app.py")],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True,
                    stdout=log_f,
                    stderr=log_f,
                )
        except Exception as e:
            print(f"[Tray] Error WebApp: {e}")

    def _start_brain(self) -> None:
        """Arranca el brain, visión y audio en el proceso actual."""
        try:
            from brain import get_brain, get_idle_watcher
            from vision_engine import get_vision_engine
            from audio_visual_sync import get_audio_visual_sync
            from document_intelligence import get_document_intelligence

            brain  = get_brain()
            idle   = get_idle_watcher()
            vision = get_vision_engine()

            vision.set_active_goal("Proyecto Alisha")
            vision.start()
            idle.start()

            print("[Tray] ✓ Brain + Visión + Audio activos en background")

            # Watchdog: mantener vivo mientras el tray corre
            while self._running:
                time.sleep(5)

        except Exception as e:
            print(f"[Tray] Error brain: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# VENTANA DE CONFIGURACIÓN (simple)
# ══════════════════════════════════════════════════════════════════════════════

def abrir_configuracion() -> None:
    """Abre una ventana de configuración básica con tkinter."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox

        root = tk.Tk()
        root.title("Alisha — Configuración")
        root.geometry("400x300")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        # Estilo
        style = ttk.Style()
        style.configure("TLabel", background="#1a1a2e", foreground="#e0e0e0")
        style.configure("TButton", padding=6)

        tk.Label(root, text="⚙ Configuración de Alisha",
                 font=("Segoe UI", 14, "bold"),
                 bg="#1a1a2e", fg="#c084fc").pack(pady=15)

        # Meta activa
        frame_meta = tk.Frame(root, bg="#1a1a2e")
        frame_meta.pack(fill="x", padx=20, pady=5)
        tk.Label(frame_meta, text="Meta activa:",
                 bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 10)).pack(anchor="w")
        meta_var = tk.StringVar(value="Proyecto Alisha")
        meta_entry = tk.Entry(frame_meta, textvariable=meta_var,
                              width=40, bg="#2d2d44", fg="white",
                              insertbackground="white")
        meta_entry.pack(fill="x", pady=3)

        # Umbral de inactividad
        frame_idle = tk.Frame(root, bg="#1a1a2e")
        frame_idle.pack(fill="x", padx=20, pady=5)
        tk.Label(frame_idle, text="Minutos de inactividad para comentarios:",
                 bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 10)).pack(anchor="w")
        idle_var = tk.IntVar(value=3)
        tk.Spinbox(frame_idle, from_=1, to=30, textvariable=idle_var,
                   width=5, bg="#2d2d44", fg="white").pack(anchor="w", pady=3)

        def guardar():
            try:
                from vision_engine import get_vision_engine
                get_vision_engine().set_active_goal(meta_var.get())
                from brain import get_idle_watcher
                get_idle_watcher().IDLE_THRESHOLD = idle_var.get() * 60.0
                messagebox.showinfo("Guardado", "Configuración aplicada ✓")
                root.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(root, text="Guardar", command=guardar,
                  bg="#7c3aed", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=20, pady=6).pack(pady=15)

        root.mainloop()
    except Exception as e:
        print(f"[Tray] Error configuración: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM TRAY
# ══════════════════════════════════════════════════════════════════════════════

class AlishaTray:
    """Ícono en la bandeja del sistema."""

    def __init__(self):
        self._manager = AlishaProcessManager()
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        """Arranca el tray y todos los sistemas."""
        # Arrancar sistemas en background
        threading.Thread(target=self._manager.start_all, daemon=True).start()

        # Crear ícono
        try:
            img = crear_icono()
        except Exception as e:
            print(f"[Tray] No se pudo crear ícono: {e}")
            sys.exit(1)

        # Menú del tray
        menu = Menu(
            Item(
                "Mostrar/Ocultar Alisha",
                self._toggle_live2d,
                default=True,
            ),
            Item("Abrir Chat Web", self._open_web),
            Menu.SEPARATOR,
            Item("Configuración", self._open_config),
            Menu.SEPARATOR,
            Item("Salir", self._quit),
        )

        self._icon = pystray.Icon(
            name="Alisha",
            icon=img,
            title="Alisha — IA Activa",
            menu=menu,
        )

        print("[Tray] ✓ Alisha en la bandeja del sistema")
        self._icon.run()  # bloquea hasta que se llame a stop()

    # ── Callbacks del menú ────────────────────────────────────────────────────

    def _toggle_live2d(self, icon, item) -> None:
        estado = self._manager.toggle_live2d()
        icon.title = f"Alisha — {'Visible' if estado == 'visible' else 'Oculta'}"
        # Actualizar ícono según estado
        try:
            if estado == "oculto":
                img = crear_icono()
                # Oscurecer levemente para indicar que está oculta
                from PIL import ImageEnhance
                img = ImageEnhance.Brightness(img).enhance(0.6)
                icon.icon = img
            else:
                icon.icon = crear_icono()
        except Exception:
            pass

    def _open_web(self, icon, item) -> None:
        self._manager.open_web()

    def _open_config(self, icon, item) -> None:
        threading.Thread(target=abrir_configuracion, daemon=True).start()

    def _quit(self, icon, item) -> None:
        print("[Tray] Cerrando Alisha...")
        self._manager.stop_all()
        icon.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tray = AlishaTray()
    tray.run()
