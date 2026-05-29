"""
memory/ — Persistencia de conversaciones, recuerdos y memoria semántica.

Re-exporta las funciones del módulo memory.py de raíz para compatibilidad
con todos los módulos que hacen `from memory import guardar_identidad`, etc.
"""
from memory.memory_db import MemoryDB
from memory.agent_memory import get_memory

__all__ = ["MemoryDB", "get_memory"]

try:
    from memory.alisha_memoria_semantica import get_indice
    __all__.append("get_indice")
except ImportError:
    pass

# ── Re-exportar funciones del memory.py de raíz (compatibilidad) ─────────────
# Estos imports permiten que `from memory import guardar_identidad` funcione
# aunque el código esté en el paquete memory/
import sys as _sys
import os as _os

# Agregar raíz al path si no está (para importar memory.py de raíz directamente)
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path:
    _sys.path.insert(0, _root)

try:
    # Importar el módulo memory.py de raíz con nombre alternativo para evitar
    # conflicto con este paquete
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_memory_root", _os.path.join(_root, "memory.py"))
    _mem_root = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mem_root)

    # Re-exportar todas las funciones públicas
    cargar_identidad        = _mem_root.cargar_identidad
    guardar_identidad       = _mem_root.guardar_identidad
    cargar_memoria          = _mem_root.cargar_memoria
    guardar_memoria         = _mem_root.guardar_memoria
    guardar_memoria_personal = _mem_root.guardar_memoria_personal
    agregar_memoria         = _mem_root.agregar_memoria
    guardar_perfil          = _mem_root.guardar_perfil
    guardar_estado          = _mem_root.guardar_estado
    obtener_estado_vigente  = _mem_root.obtener_estado_vigente
    guardar_recordatorio    = _mem_root.guardar_recordatorio
    limpiar_historial       = _mem_root.limpiar_historial
    reiniciar_memoria       = _mem_root.reiniciar_memoria
    configurar_autostart    = _mem_root.configurar_autostart
    obtener_contexto_memoria = _mem_root.obtener_contexto_memoria

    __all__ += [
        "cargar_identidad", "guardar_identidad",
        "cargar_memoria", "guardar_memoria",
        "guardar_memoria_personal", "agregar_memoria",
        "guardar_perfil", "guardar_estado", "obtener_estado_vigente",
        "guardar_recordatorio", "limpiar_historial", "reiniciar_memoria",
        "configurar_autostart", "obtener_contexto_memoria",
    ]
except Exception as _e:
    import warnings
    warnings.warn(f"[memory] No se pudo cargar memory.py de raíz: {_e}")
