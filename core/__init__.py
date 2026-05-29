"""
core/ — Cerebro central de Alisha IA.

Importa de: services/, memory/, personality/, config/
NO es importado por: personality/, services/, memory/, tools/, vision/, avatar/
"""

from core.brain import HybridIntelligenceCore, get_brain, get_idle_watcher
from core.emotion_engine import EmotionEngine
from core.agent_loop import AgentLoop, EventBus

__all__ = [
    "HybridIntelligenceCore",
    "get_brain",
    "get_idle_watcher",
    "EmotionEngine",
    "AgentLoop",
    "EventBus",
]
