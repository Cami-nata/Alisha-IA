"""
personality/ — Identidad, personalidad y comportamiento de Alisha.

Exporta las clases y funciones públicas del paquete.
NO importa de core/ (ver reglas de dependencia en design.md).
"""

from personality.alisha_identity import SemillaPersonalidad, GestosNoVerbales
from personality.skepticism_engine import SkepticismEngine
from personality.alisha_curiosidad import CuriosidadEngine, iniciar_curiosidad

__all__ = [
    "SemillaPersonalidad",
    "GestosNoVerbales",
    "SkepticismEngine",
    "CuriosidadEngine",
    "iniciar_curiosidad",
]
