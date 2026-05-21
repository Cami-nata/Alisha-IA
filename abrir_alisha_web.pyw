"""
abrir_alisha_web.pyw — Lanzador silencioso de la interfaz web de Alisha.

Ejecutar con doble clic (pythonw, sin terminal).
- Si el servidor ya está corriendo, abre el navegador directamente.
- Si no, arranca web_app.py en background y espera a que esté listo.
"""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent
URL = "http://localhost:5000"
PYTHON = sys.executable
# Usar pythonw para no mostrar terminal
PYTHONW = PYTHON.replace("python.exe", "pythonw.exe")
if not Path(PYTHONW).exists():
    PYTHONW = PYTHON


def servidor_activo() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(URL, timeout=1)
        return True
    except Exception:
        return False


def main():
    os.chdir(BASE_DIR)

    if servidor_activo():
        webbrowser.open(URL)
        return

    # Arrancar web_app.py sin ventana
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [PYTHONW, str(BASE_DIR / "web_app.py")],
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Esperar hasta 20 segundos a que el servidor responda
    for _ in range(20):
        time.sleep(1)
        if servidor_activo():
            break

    webbrowser.open(URL)


if __name__ == "__main__":
    main()
