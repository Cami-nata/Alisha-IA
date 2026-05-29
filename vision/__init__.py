"""
vision/ — Percepción visual del entorno de Alisha.

Módulo independiente: NO importa de core/, memory/, personality/ ni avatar/.
Solo puede importar de config/.
"""

from vision.vision_engine import VisionEngine, VisionSnapshot, VisionContext, detectar_rol, get_vision_engine, enrich_query_with_vision
from vision.screen_vision import capturar_ventana_rapida, obtener_ventana_activa_info, detectar_errores_en_pantalla

__all__ = [
    "VisionEngine",
    "VisionSnapshot",
    "VisionContext",
    "detectar_rol",
    "get_vision_engine",
    "enrich_query_with_vision",
    "capturar_ventana_rapida",
    "obtener_ventana_activa_info",
    "detectar_errores_en_pantalla",
]
