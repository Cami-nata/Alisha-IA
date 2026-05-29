"""
config.py — shim de compatibilidad.
Redirige todos los imports al nuevo paquete config/.
"""
from config.settings import *  # noqa: F401, F403
from config.constants import *  # noqa: F401, F403
