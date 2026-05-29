"""
tools/ — Herramientas de control del PC.

Módulo independiente: NO importa de core/, memory/, personality/ ni avatar/.
Solo puede importar de config/.
"""

from tools.pc_controller import abort_all_actions, iniciar_hotkey_bloqueo, esta_bloqueado, set_bloqueado
from tools.safety_guard import SafetyGuard, get_guard
from tools.natural_mouse import NaturalMouse

__all__ = [
    "abort_all_actions",
    "iniciar_hotkey_bloqueo",
    "esta_bloqueado",
    "set_bloqueado",
    "SafetyGuard",
    "get_guard",
    "NaturalMouse",
]
