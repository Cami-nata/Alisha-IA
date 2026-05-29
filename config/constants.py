"""Constantes inmutables del sistema — no cambian en tiempo de ejecución."""
from pathlib import Path

from config.settings import DATA_DIR

# Archivo de estado compartido entre core/ y avatar/
STATE_FILE = DATA_DIR / "chibi_state.json"

# Intervalos del AgentLoop
CYCLE_INTERVAL_S = 5.0
HEARTBEAT_INTERVAL_S = 30.0
FILE_CHANGE_WINDOW_S = 30.0
MOUSE_IDLE_WAIT_S = 3.0
IDLE_TRANSITION_S = 2.0

# Cooldowns
RAM_MENTION_COOLDOWN = 300.0
SOLUTION_EXECUTION_COOLDOWN = 60.0

# Categorías de aplicaciones → rol
APP_CATEGORIES = {
    "senior_dev": (
        {"visual studio code", "vscode", "code", "kiro", "pycharm", "terminal", "powershell"},
        "senior_dev",
    ),
    "directora_creativa": (
        {"figma", "photoshop", "illustrator", "canva", "adobe"},
        "directora_creativa",
    ),
    "investigadora": (
        {"chrome", "edge", "firefox", "brave", "opera"},
        "investigadora",
    ),
    "asistente_ejecutiva": (
        {"word", "excel", "powerpoint", "libreoffice", "docs", "sheets"},
        "asistente_ejecutiva",
    ),
}
