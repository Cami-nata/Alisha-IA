"""
iniciar_alisha.pyw — Lanzador sin consola de Alisha.
Doble clic para iniciar. Redirige a Alisha_IA.pyw (el launcher correcto).
"""
import sys
import os
from pathlib import Path

# Cambiar al directorio del script para que todos los paths relativos funcionen
os.chdir(Path(__file__).parent)

# Redirigir stdout/stderr a log (pythonw no tiene consola)
_log = open(Path(__file__).parent / "alisha_debug.log", "a", encoding="utf-8", buffering=1)
sys.stdout = _log
sys.stderr = _log

# Ejecutar el sistema completo
from Alisha_IA import main
main()
