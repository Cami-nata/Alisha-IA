"""Carga variables de entorno desde .env usando python-dotenv."""
import os
from pathlib import Path

# Keys críticas que deben estar presentes en el .env
_CRITICAL_KEYS = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "MISTRAL_API_KEY",
]

# Keys opcionales (se cargan pero no generan advertencia si faltan)
_OPTIONAL_KEYS = [
    "ELEVENLABS_API_KEY",
    "MONGO_URI",
]


def load_env() -> None:
    """Carga el archivo .env desde la raíz del proyecto.

    - Fail-silent si python-dotenv no está instalado.
    - Verifica que las keys críticas existan y loguea advertencia si falta alguna.
    - GEMINI_API_KEY también se expone como GOOGLE_API_KEY si no está ya definida.
    - Nunca imprime los valores de las keys, solo sus nombres.
    """
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        pass

    # Alias: GEMINI_API_KEY → GOOGLE_API_KEY (si GOOGLE_API_KEY no está definida)
    gemini_val = os.environ.get("GEMINI_API_KEY")
    if gemini_val and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = gemini_val

    # Verificar keys críticas
    for key in _CRITICAL_KEYS:
        if not os.environ.get(key):
            print(f"[Config] ADVERTENCIA: {key} no encontrada en .env")
