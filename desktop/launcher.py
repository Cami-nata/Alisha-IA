"""
desktop/launcher.py — Launcher de Alisha IA como app de escritorio.

Usa pywebview para abrir la UI JARVIS como ventana nativa sin barras de navegador.
El backend Flask sigue corriendo en localhost:5000.

Uso:
    python desktop/launcher.py          # abre la app
    python desktop/launcher.py --wait   # espera a que el backend esté listo
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import time
import threading
from pathlib import Path

# Agregar raíz al path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

PORT = int(os.getenv("PORT", "5000"))
URL  = f"http://localhost:{PORT}"


def _esperar_backend(timeout: int = 20) -> bool:
    """Espera hasta que el backend Flask esté disponible."""
    print(f"[Launcher] Esperando backend en {URL}...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("localhost", PORT), timeout=1):
                print(f"[Launcher] ✓ Backend disponible")
                return True
        except OSError:
            time.sleep(0.5)
    print(f"[Launcher] ⚠ Backend no respondió en {timeout}s")
    return False


def _iniciar_backend_si_no_corre():
    """Inicia el backend Python si no está corriendo."""
    try:
        with socket.create_connection(("localhost", PORT), timeout=1):
            print(f"[Launcher] Backend ya está corriendo en :{PORT}")
            return
    except OSError:
        pass

    print("[Launcher] Iniciando backend...")
    import subprocess
    python = Path(sys.executable)
    main   = BASE_DIR / "main.py"

    subprocess.Popen(
        [str(python), str(main)],
        cwd=str(BASE_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def abrir_ventana():
    """Abre la UI JARVIS como ventana nativa con pywebview."""
    try:
        import webview
    except ImportError:
        print("[Launcher] ✗ pywebview no instalado. Ejecutá: pip install pywebview")
        # Fallback: abrir en el navegador
        import webbrowser
        webbrowser.open(URL)
        return

    # Configuración de la ventana
    window = webview.create_window(
        title="Alisha IA",
        url=URL,
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        easy_drag=False,
        background_color="#0a0e1a",
        # Sin barra de navegador — solo la UI
    )

    # Exponer API Python al JS (para acciones nativas)
    class AlishaAPI:
        def get_version(self):
            return "2.0-JARVIS"

        def minimize(self):
            window.minimize()

        def toggle_fullscreen(self):
            window.toggle_fullscreen()

    window.expose(AlishaAPI())

    print(f"[Launcher] ✓ Abriendo ventana JARVIS → {URL}")
    webview.start(debug=False)


def main():
    parser = argparse.ArgumentParser(description="Alisha IA — Desktop Launcher")
    parser.add_argument("--wait", action="store_true",
                        help="Solo esperar al backend, no abrir ventana")
    parser.add_argument("--no-start", action="store_true",
                        help="No iniciar el backend automáticamente")
    args = parser.parse_args()

    # Iniciar backend si no está corriendo
    if not args.no_start:
        _iniciar_backend_si_no_corre()

    # Esperar a que el backend esté listo
    if not _esperar_backend(timeout=30):
        print("[Launcher] ✗ No se pudo conectar al backend. Verificá que main.py esté corriendo.")
        sys.exit(1)

    if args.wait:
        print(f"[Launcher] Backend listo en {URL}")
        return

    # Abrir ventana
    abrir_ventana()


if __name__ == "__main__":
    main()
