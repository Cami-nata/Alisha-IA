"""config package — configuración centralizada de Alisha IA."""
from config.env_loader import load_env

# Cargar .env antes de importar settings (que lee las vars)
load_env()

# Re-exportar todo para que `from config import X` funcione igual que antes
from config.settings import *   # noqa: F401, F403
from config.constants import *  # noqa: F401, F403
