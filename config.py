import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Rutas base del proyecto ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent          # raíz del proyecto
DATA_DIR = BASE_DIR / "data"              # carpeta centralizada de datos/estado
DATA_DIR.mkdir(exist_ok=True)             # se crea si no existe

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_NAME = "Elena"
CONTEXT_SUMMARY_THRESHOLD = 10
# Acciones que requieren confirmación explícita del usuario antes de ejecutarse.
# Las acciones conversacionales ("nada") nunca piden confirmación.
CONFIRMAR_ACCIONES = False

# Acciones que SÍ deben pedir confirmación aunque CONFIRMAR_ACCIONES sea False
# (acciones destructivas o de alto impacto)
ACCIONES_PELIGROSAS = {"power", "ejecutar_codigo", "hotkey"}
SAFE_MODE = True
IDENTIDAD_FILE  = str(DATA_DIR / "ia_identidad.json")
MEMORY_FILE     = str(DATA_DIR / "ia_memoria.json")
LOG_FILE        = str(DATA_DIR / "ia_acciones.log")
VOICE_LANG_DEFAULT = "es-ES"
VALID_ACTIONS = {
    "abrir_app",
    "abrir_web",
    "escribir_texto",
    "hotkey",
    "click",
    "doble_click",
    "screenshot",
    "crear_word",
    "tomar_nota",
    "recordatorio",
    "diagnosticar",
    "power",
    "ventana",
    "volumen",
    "musica",
    "buscar_archivo",
    "brillo",
    "ejecutar_codigo",
    "navegar_web",
    "buscar_web",
    "click_web",
    "escribir_web",
    "leer_web",
    "cerrar_navegador",
    "nada",
}

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = "ia_asistente"
MONGO_MAX_HISTORIAL = 500
LIVE2D_MODEL_PATH = os.environ.get(
    "LIVE2D_MODEL_PATH",
    r"C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\IceGirl_Live2d\IceGIrl Live2D\IceGirl.model3.json"
)

def _resolver_app(nombre: str) -> str:
    """
    Resuelve la ruta de una app buscando en múltiples ubicaciones estándar.
    Compatible con cualquier PC — no depende de rutas hardcodeadas.
    """
    import shutil
    # 1. Buscar en PATH del sistema
    en_path = shutil.which(nombre)
    if en_path:
        return en_path

    # 2. Rutas estándar de Windows (independientes del usuario)
    rutas_estandar = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "word": [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
        ],
        "notepad": [
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "notepad.exe"),
            r"C:\Windows\notepad.exe",
        ],
        "calc": [
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "calc.exe"),
        ],
    }
    nombre_lower = nombre.lower()
    for clave, rutas in rutas_estandar.items():
        if clave in nombre_lower:
            for ruta in rutas:
                if os.path.exists(ruta):
                    return ruta
    return nombre  # fallback: usar el nombre directamente

APP_RUTAS = {
    "chrome": _resolver_app("chrome"),
    "edge":   _resolver_app("edge"),
    "word":   _resolver_app("word"),
}
ALLOWED_APPS = set(APP_RUTAS.keys()) | {"explorador"}
POWER_COMMANDS = {
    "apagar": "shutdown /s /t 0",
    "reiniciar": "shutdown /r /t 0",
    "suspender": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
}
STARTUP_SHORTCUT = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "ia_asistente_start.bat"

# Configuración de comportamiento
OBSERVACION_SILENCIOSA = False  # Si True, Alisha observa sin comentar constantemente
COMENTARIOS_ESPONTANEOS = True  # Si True, permite comentarios espontáneos ocasionales e inteligentes
FRECUENCIA_OBSERVACION = 60  # Segundos entre observaciones de pantalla (60 = menos intrusivo)
