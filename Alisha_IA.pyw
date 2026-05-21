"""
Alisha_IA.pyw — Versión sin consola de Alisha_IA.py
Usar este archivo para abrir Alisha sin ventana negra.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Redirigir logs al archivo antes de importar nada
from pathlib import Path
_log = open(Path(__file__).parent / "alisha_debug.log", "a", encoding="utf-8", buffering=1)
sys.stdout = _log
sys.stderr = _log

# Ejecutar el main de Alisha_IA
from Alisha_IA import main
main()
