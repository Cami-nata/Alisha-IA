"""
cabina_virtual.py — Motor de Comportamiento Orgánico para Alisha (Live2D).

100% control por parámetros directos. Sin StartMotion. Sin archivos .motion3.json.
Todo movimiento es consecuencia matemática del estado interno y del entorno.

Sistema:
  - Dopamina / Humor / Irritabilidad → rangos dinámicos de parámetros
  - Análisis semántico de ventana activa → categorías (Flow, Tensión, Neutro)
  - Seguimiento de mouse con ruido Perlin + micro-acciones autónomas
  - Inercia corporal: pelo y brazos reaccionan a movimiento de cabeza
  - Lerp suavizado en todos los parámetros, sin saltos ni desenfoque
  - Chat web en hilo independiente (no bloquea animación)

Controles:
  Click izquierdo  → altera humor (muchos clics = irritabilidad)
  Click derecho + arrastrar → mover ventana
  Rueda → zoom
  Ctrl+S → guardar | Ctrl+E → estático | Ctrl+R → reset | ESC → cerrar
  Ctrl+T → mover a borde superior | Ctrl+B → mover a borde inferior
"""
import ctypes, ctypes.wintypes
import json, math, random, sys, time, threading, webbrowser, socket
from pathlib import Path

# psutil — muestreo de CPU/RAM para animar el avatar con datos reales del sistema
try:
    import psutil as _psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

import glfw
from OpenGL.GL import (
    glViewport, glClearColor, glClear, glEnable, glBlendFunc,
    glColorMask,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_STENCIL_BUFFER_BIT,
    GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    GL_TRUE, GL_FALSE,
)
import live2d.v3 as live2d
from config import LIVE2D_MODEL_PATH

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"
PREFS_FILE = DATA_DIR / "chibi_prefs.json"
EMOTION_PERSIST_FILE = DATA_DIR / "alisha_estado_emocional.json"
W_DEF = 380; H_DEF = 570
W_MIN = 200; W_MAX = 1200

# ── Hardware sampler — CPU/RAM cacheados cada 1s ──────────────────────────────
# El hilo daemon escribe aquí; el loop de 60fps lee sin bloquear.
_HW_CPU_PCT: float = 0.0   # porcentaje de CPU  (0.0–100.0)
_HW_RAM_PCT: float = 0.0   # porcentaje de RAM  (0.0–100.0)


def _hw_to_live2d(pct: float, lo: float, hi: float) -> float:
    """Mapea un porcentaje 0–100 a un rango Live2D [lo, hi] linealmente."""
    return lo + (hi - lo) * max(0.0, min(100.0, pct)) / 100.0


def _iniciar_hw_sampler() -> None:
    """
    Hilo daemon que muestrea CPU y RAM cada 1 segundo con psutil.
    Usa cpu_percent(interval=None) para no bloquear — devuelve el valor
    calculado desde la última llamada (no bloquea el hilo).
    """
    if not _PSUTIL_OK:
        return

    def _loop():
        global _HW_CPU_PCT, _HW_RAM_PCT
        # Primera llamada descartada — inicializa el contador interno de psutil
        try:
            _psutil.cpu_percent(interval=None)
        except Exception:
            pass
        while True:
            try:
                _HW_CPU_PCT = _psutil.cpu_percent(interval=None)
                _HW_RAM_PCT = _psutil.virtual_memory().percent
            except Exception:
                pass
            time.sleep(1.0)

    threading.Thread(target=_loop, daemon=True, name="HWSampler").start()
    print("[Alisha] 📊 HWSampler iniciado (CPU/RAM → parámetros Live2D)")

# ── Estado de pausa global ────────────────────────────────────────────────────
# Cuando _PAUSADA=True: ventana oculta + voz silenciada. Web sigue funcionando.
_PAUSADA: bool = False
_glfw_win_ref = [None]   # referencia a la ventana GLFW para show/hide

def _toggle_pausa() -> None:
    """Oculta/muestra el modelo 2D y silencia/activa la voz. No toca la web."""
    global _PAUSADA
    _PAUSADA = not _PAUSADA
    win = _glfw_win_ref[0]

    if _PAUSADA:
        # Ocultar ventana GLFW
        if win:
            try:
                import glfw as _glfw
                _glfw.hide_window(win)
            except Exception:
                pass
        # Silenciar TTS — escribir flag en chibi_state.json
        try:
            import alisha_bridge
            alisha_bridge.IS_SPEAKING = False
        except Exception:
            pass
        # Detener audio en curso inmediatamente
        try:
            from tts_engine import TTSEngine
            TTSEngine().stop_audio()
        except Exception:
            pass
        # Detener AudioVisualSync también
        try:
            from audio_visual_sync import get_audio_visual_sync
            avs = get_audio_visual_sync()
            avs.stop()
        except Exception:
            pass
        # Flag en chibi_state para que tts_engine no reproduzca
        try:
            _sd = {}
            if STATE_FILE.exists():
                _sd = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            _sd["tts_silenciado"] = True
            STATE_FILE.write_text(json.dumps(_sd, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        print("[Alisha] ⏸ Modelo 2D oculto y voz silenciada — chat web sigue activo")
    else:
        # Mostrar ventana GLFW
        if win:
            try:
                import glfw as _glfw
                _glfw.show_window(win)
                hwnd = _glfw.get_win32_window(win)
                _force_topmost(hwnd)
            except Exception:
                pass
        # Quitar flag de silencio
        try:
            _sd = {}
            if STATE_FILE.exists():
                _sd = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            _sd.pop("tts_silenciado", None)
            STATE_FILE.write_text(json.dumps(_sd, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        print("[Alisha] ▶ Modelo 2D visible y voz activada")

# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCIA EMOCIONAL
# ═══════════════════════════════════════════════════════════════════════════════

def guardar_estado_emocional(ei: "EstadoInterno"):
    """Guarda el estado interno al cerrar."""
    try:
        EMOTION_PERSIST_FILE.write_text(json.dumps({
            "dopamina":      ei.dopamina,
            "humor":         ei.humor,
            "irritabilidad": ei.irritabilidad,
            "tension":       ei.tension,
            "flow":          ei.flow,
            "timestamp":     time.time(),
            "historial_categorias": ei._historial_categorias[-20:],
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

def cargar_estado_emocional() -> dict:
    """Carga el estado de la sesión anterior."""
    try:
        if EMOTION_PERSIST_FILE.exists():
            return json.loads(EMOTION_PERSIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def analisis_semanal_async(ei: "EstadoInterno"):
    """
    Analiza el historial emocional de la semana con Llama en hilo separado.
    Ajusta el estado inicial de Alisha según los patrones detectados.
    """
    def _analizar():
        try:
            historial = ei._historial_categorias
            if len(historial) < 10:
                return   # no hay suficientes datos

            tensiones = historial.count("tension")
            flows     = historial.count("flow")
            total     = len(historial)

            resumen = (
                f"Historial emocional: {total} eventos. "
                f"Tensión: {tensiones} ({tensiones*100//total}%). "
                f"Flow: {flows} ({flows*100//total}%). "
                f"Neutro: {total-tensiones-flows}."
            )

            import requests
            payload = {
                "model": "llama3.1",
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Sos Alisha, una IA con personalidad. "
                        f"Basándote en este resumen de la semana: {resumen}. "
                        f"¿Cómo deberías iniciar la sesión de hoy? "
                        f"Respondé en una sola oración corta, en primera persona."
                    )
                }],
                "stream": False
            }
            r = requests.post("http://localhost:11434/api/chat",
                            json=payload, timeout=15)
            if r.status_code == 200:
                reflexion = r.json().get("message", {}).get("content", "")
                if reflexion:
                    print(f"[Alisha] 💭 {reflexion}")
                    # Guardar reflexión en chibi_state para que aparezca en el chat
                    try:
                        from assistant_state import actualizar_estado
                        actualizar_estado(texto=reflexion)
                    except Exception:
                        pass
        except Exception:
            pass

    threading.Thread(target=_analizar, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════════════════
# MOTOR DE ESTADO INTERNO
# ═══════════════════════════════════════════════════════════════════════════════

class EstadoInterno:
    """
    Estado interno de Alisha. Todos los parámetros Live2D son función de esto.
    dopamina  [0,1]: energía/alegría
    humor     [0,1]: estado de ánimo general
    irritabilidad [0,1]: sube con clics repetidos, baja con el tiempo
    tension   [0,1]: sube con contenido de terror/errores, baja en flow
    flow      [0,1]: sube con música/diseño/crochet
    """
    def __init__(self, estado_previo: dict = None):
        self._historial_categorias = []
        self._modo_despertar = "normal"

        if estado_previo:
            self.dopamina      = estado_previo.get("dopamina", 0.7)
            self.humor         = estado_previo.get("humor", 0.7)
            self.irritabilidad = estado_previo.get("irritabilidad", 0.0) * 0.3
            self.tension       = estado_previo.get("tension", 0.0) * 0.2
            self.flow          = estado_previo.get("flow", 0.0) * 0.5
            self._historial_categorias = estado_previo.get("historial_categorias", [])

            ts = estado_previo.get("timestamp", 0)
            horas = (time.time() - ts) / 3600
            if self.dopamina < 0.25 and horas < 8:
                self.dopamina = 0.15
                self.humor    = 0.2
                self._modo_despertar = "cansada"
                print("[Alisha] 😴 Iniciando cansada (sesión anterior agotadora)")
            elif horas > 24:
                self.dopamina = 0.65
                self.humor    = 0.65
                self._modo_despertar = "fresca"

            tensiones = self._historial_categorias.count("tension")
            if tensiones > 5:
                self.tension = min(0.4, self.tension + 0.2)
                print("[Alisha] ⚠ Historial de tensión — más cautelosa")
        else:
            self.dopamina      = 0.75   # arranca con energía visible
            self.humor         = 0.70
            self.irritabilidad = 0.0
            self.tension       = 0.0
            self.flow          = 0.35   # flow inicial para que haya balanceo visible

        self.hablando      = False
        self.categoria     = "neutro"   # "flow", "tension", "neutro"
        self._ultimo_clic  = 0.0
        self._clics_recientes = 0

        # Iniciativa propia — basada en historial
        self.ignorar_mouse    = False   # True = no sigue el cursor
        self.modo_sarcastico  = False   # True = respuestas más secas
        self._calcular_iniciativa()

    def _calcular_iniciativa(self):
        """Decide comportamiento inicial basado en historial."""
        tensiones = self._historial_categorias.count("tension")
        flows     = self._historial_categorias.count("flow")
        total     = len(self._historial_categorias)

        if total > 10:
            ratio_tension = tensiones / total
            # Si > 60% del historial fue tensión → más distante
            if ratio_tension > 0.6:
                self.ignorar_mouse   = random.random() < 0.4   # 40% chance de ignorar
                self.modo_sarcastico = random.random() < 0.3
                if self.ignorar_mouse:
                    print("[Alisha] 😒 Modo distante activado (historial tenso)")
            # Si > 60% fue flow → más expresiva
            elif flows / total > 0.6:
                self.ignorar_mouse   = False
                self.modo_sarcastico = False
                self.dopamina = min(1.0, self.dopamina + 0.1)

        # Si la sesión anterior fue muy corta (< 5 categorías) → aburrida
        if 0 < total < 5 and self._modo_despertar == "normal":
            self.modo_sarcastico = random.random() < 0.2
            if self.modo_sarcastico:
                print("[Alisha] 🙄 Sesión anterior muy corta — un poco sarcástica")

    def clic(self):
        now = time.time()
        if now - self._ultimo_clic < 3.0:
            self._clics_recientes += 1
        else:
            self._clics_recientes = 1
        self._ultimo_clic = now
        # Muchos clics = irritabilidad sube
        self.irritabilidad = min(1.0, self.irritabilidad + 0.15 * self._clics_recientes)
        # Humor baja levemente
        self.humor = max(0.0, self.humor - 0.05)

    def set_categoria(self, cat: str):
        self.categoria = cat
        self._historial_categorias.append(cat)
        if len(self._historial_categorias) > 100:
            self._historial_categorias = self._historial_categorias[-100:]
        if cat == "tension":
            self.tension = min(1.0, self.tension + 0.3)
            self.flow    = max(0.0, self.flow    - 0.2)
            self.dopamina = max(0.2, self.dopamina - 0.1)
        elif cat == "flow":
            self.flow    = min(1.0, self.flow    + 0.3)
            self.tension = max(0.0, self.tension - 0.2)
            self.dopamina = min(1.0, self.dopamina + 0.1)
        else:
            self.tension = max(0.0, self.tension - 0.05)
            self.flow    = max(0.0, self.flow    - 0.05)

    def set_desde_chibi(self, estado: str, hablando: bool):
        self.hablando = hablando
        MAPA = {
            "alegría":      (0.9, 0.85),
            "entusiasmo":   (0.95, 0.9),
            "curiosidad":   (0.7, 0.75),
            "preocupación": (0.4, 0.35),
            "frustración":  (0.3, 0.2),
            "cansancio":    (0.2, 0.3),
            "nostalgia":    (0.5, 0.5),
            "neutral":      (0.65, 0.65),
        }
        d, h = MAPA.get(estado, (0.65, 0.65))
        # Lerp suave hacia el nuevo estado
        self.dopamina = self.dopamina * 0.85 + d * 0.15
        self.humor    = self.humor    * 0.85 + h * 0.15

    def tick(self, dt: float):
        """Decaimiento natural cada frame."""
        decay = dt * 0.008   # decaimiento más lento para movimiento sostenido
        self.irritabilidad = max(0.0, self.irritabilidad - decay * 2)
        self.tension       = max(0.0, self.tension       - decay)
        self.flow          = max(0.15, self.flow          - decay * 0.3)  # mínimo 0.15 siempre
        # Humor tiende a 0.65 (neutral)
        self.humor += (0.65 - self.humor) * dt * 0.008
        # Dopamina mínima para que siempre haya algo de vida
        self.dopamina = max(0.4, self.dopamina)

    # ── Rangos dinámicos ──────────────────────────────────────────────────────
    def rango_sonrisa(self) -> tuple[float, float]:
        """Rango de ParamEyeLSmile / ParamMouthForm según humor."""
        if self.irritabilidad > 0.6:
            return (-0.5, 0.0)   # enojada
        if self.humor > 0.75:
            return (0.7, 1.0)    # feliz
        if self.tension > 0.5:
            return (-0.3, 0.2)   # tensa
        return (0.2, 0.6)        # neutral

    def rango_cejas(self) -> tuple[float, float]:
        """Rango de ParamBrowLAngle según estado."""
        if self.irritabilidad > 0.5:
            return (-1.0, -0.4)  # cejas fruncidas
        if self.tension > 0.5:
            return (0.3, 0.8)    # cejas levantadas (susto)
        if self.humor > 0.8:
            return (0.2, 0.5)    # cejas relajadas/alegres
        return (-0.2, 0.2)       # neutral

    def amplitud_balanceo(self) -> float:
        """Retorna amplitud en [1.5, 5.0]."""
        raw = 1.5 + self.flow * 2.0 + self.dopamina * 0.8
        return max(1.5, min(5.0, raw))

    def velocidad_balanceo(self) -> float:
        """Retorna velocidad en [0.20, 0.45] Hz."""
        raw = 0.20 + self.flow * 0.25
        return max(0.20, min(0.45, raw))

    def tension_ocular(self) -> float:
        """Cuánto se cierran los ojos por tensión."""
        return self.tension * 0.4   # 0=normal, 0.4=muy cerrados


# ═══════════════════════════════════════════════════════════════════════════════
# RUIDO SIMPLEX SIMPLIFICADO (para micro-movimientos oculares)
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleNoise:
    """Ruido suave basado en sumas de senos con fases aleatorias."""
    def __init__(self, seed: int = 42):
        rng = random.Random(seed)
        self._freqs  = [rng.uniform(0.1, 0.8) for _ in range(6)]
        self._phases = [rng.uniform(0, math.tau) for _ in range(6)]
        self._amps   = [rng.uniform(0.1, 0.4) for _ in range(6)]

    def sample(self, t: float) -> float:
        v = sum(a * math.sin(f * t + p)
                for a, f, p in zip(self._amps, self._freqs, self._phases))
        return v / sum(self._amps)   # normalizado [-1, 1]


noise_x = SimpleNoise(seed=1)
noise_y = SimpleNoise(seed=2)
noise_z = SimpleNoise(seed=3)


# ═══════════════════════════════════════════════════════════════════════════════
# LERP SUAVIZADO
# ═══════════════════════════════════════════════════════════════════════════════

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def smooth_damp(current: float, target: float, vel: list, smooth_time: float,
                dt: float, max_speed: float = 8.0) -> float:
    """SmoothDamp estilo Unity — sin oscilación."""
    smooth_time = max(0.0001, smooth_time)
    omega = 2.0 / smooth_time
    x = omega * dt
    exp_val = 1.0 / (1.0 + x + 0.48 * x*x + 0.235 * x*x*x)
    change = current - target
    max_change = max_speed * smooth_time
    change = max(-max_change, min(max_change, change))
    temp = (vel[0] + omega * change) * dt
    vel[0] = (vel[0] - omega * temp) * exp_val
    output = target + (change + temp) * exp_val
    if (target - current > 0.0) == (output > target):
        output = target
        vel[0] = 0.0
    return output


# ═══════════════════════════════════════════════════════════════════════════════
# MICRO-VARIACIONES ORGÁNICAS
# ═══════════════════════════════════════════════════════════════════════════════

class MicroVariaciones:
    """Micro-variaciones orgánicas para respiración y mirada del avatar."""
    FREQ_BREATH = 0.18   # Hz — ciclo de ~5.5s
    FREQ_GAZE_A = 0.07   # Hz — componente lenta de mirada
    FREQ_GAZE_B = 0.13   # Hz — componente rápida (diff >= 0.01 Hz)

    def __init__(self):
        self._phase_breath = random.uniform(0, math.tau)
        self._phase_gaze_a = random.uniform(0, math.tau)
        self._phase_gaze_b = random.uniform(0, math.tau)
        self._last_breath = 0.0
        self._last_gaze_x = 0.0
        self._last_gaze_y = 0.0

    def breath(self, t: float) -> float:
        """Amplitud de respiración en [-0.15, 0.15]."""
        return 0.15 * math.sin(2 * math.pi * self.FREQ_BREATH * t + self._phase_breath)

    def gaze_x(self, t: float) -> float:
        """Componente X de mirada — combinación de dos frecuencias."""
        a = 0.06 * math.sin(2 * math.pi * self.FREQ_GAZE_A * t + self._phase_gaze_a)
        b = 0.04 * math.sin(2 * math.pi * self.FREQ_GAZE_B * t + self._phase_gaze_b)
        return a + b

    def gaze_y(self, t: float) -> float:
        """Componente Y de mirada."""
        a = 0.05 * math.sin(2 * math.pi * self.FREQ_GAZE_A * t + self._phase_gaze_a + 1.0)
        b = 0.03 * math.sin(2 * math.pi * self.FREQ_GAZE_B * t + self._phase_gaze_b + 0.5)
        return a + b

    def update(self, t: float, hablando: bool, idle_since: float) -> tuple:
        """
        Retorna (breath_val, gaze_x_val, gaze_y_val).
        Si hablando=True o no han pasado 2s desde última interacción, congela valores.
        """
        idle_ok = (t - idle_since) >= 2.0
        if hablando or not idle_ok:
            return (self._last_breath, self._last_gaze_x, self._last_gaze_y)
        self._last_breath = self.breath(t)
        self._last_gaze_x = self.gaze_x(t)
        self._last_gaze_y = self.gaze_y(t)
        return (self._last_breath, self._last_gaze_x, self._last_gaze_y)


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS DE VENTANA ACTIVA
# ═══════════════════════════════════════════════════════════════════════════════

PALABRAS_TENSION = [
    "terror","horror","scary","error","traceback","exception","failed",
    "crash","warning","critical","battery low","batería baja","virus",
    "malware","hack","attack","danger","peligro","urgente",
]
PALABRAS_FLOW = [
    "music","música","spotify","youtube music","soundcloud","crochet",
    "knit","tejido","figma","canva","photoshop","illustrator","design",
    "diseño","art","arte","draw","dibujo","paint","creative",
]
PALABRAS_VIDEO = ["youtube","netflix","twitch","prime video","disney","hbo","vlc"]
PALABRAS_CODE  = ["vscode","code","python","kiro","github","terminal","powershell"]

def analizar_ventana(titulo: str) -> str:
    t = titulo.lower()
    if any(p in t for p in PALABRAS_TENSION):
        return "tension"
    if any(p in t for p in PALABRAS_FLOW):
        return "flow"
    if any(p in t for p in PALABRAS_VIDEO):
        return "video"
    if any(p in t for p in PALABRAS_CODE):
        return "code"
    return "neutro"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPRESIONES
# ═══════════════════════════════════════════════════════════════════════════════

# ── Sistema de gestos hardcodeados ELIMINADO (FASE JCySharp) ─────────────────
# El avatar no elige expresiones. Todo movimiento es consecuencia matemática
# del estado interno. Ver SistemaVariables + MotorMapeo más abajo.

# ── Gestos automáticos basados en gustos ─────────────────────────────────────

# _gesto_por_gusto() ELIMINADO — el avatar no elige gestos.
# La identidad musical de Alisha afecta ei.flow/irritabilidad,
# que a su vez afectan los parámetros matemáticamente.


# ═══════════════════════════════════════════════════════════════════════════════
# WIN32
# ═══════════════════════════════════════════════════════════════════════════════

def screen_size():
    return (ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1))

def get_active_window_title() -> str:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buf  = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""

def setup_window(hwnd):
    GWL_EXSTYLE       = -20
    WS_EX_LAYERED     = 0x00080000
    WS_EX_TOOLWINDOW  = 0x00000080
    WS_EX_NOACTIVATE  = 0x08000000
    WS_EX_APPWINDOW   = 0x00040000
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    new_style = (style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    # Color key VERDE PURO (0,255,0) — IceGirl no tiene verde en ninguna textura
    # Evita el parpadeo en mangas blancas que causaba el magenta (mezcla con bordes blancos)
    # COLORREF formato 0x00BBGGRR: verde = R=0,G=255,B=0 → 0x0000FF00
    GREEN_KEY = 0x0000FF00
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, GREEN_KEY, 0, 0x1)  # LWA_COLORKEY
    _force_topmost(hwnd)

def es_pixel_transparente(r: int, g: int, b: int) -> bool:
    """Retorna True si el píxel es zona de color key (verde puro).
    Condición exacta del spec: r < 30 AND g ∈ [225, 255] AND b < 30.
    """
    return r < 30 and 225 <= g <= 255 and b < 30


# ── Click-through dinámico ────────────────────────────────────────────────────
_ultimo_click_through = [False]   # estado actual

def _actualizar_click_through(hwnd: int, lx: float, ly: float,
                               win_w: int, win_h: int) -> None:
    """
    Click-through condicional basado en el color del framebuffer OpenGL.
    - Si el píxel bajo el cursor es verde puro (color key) → click-through ON
    - Si hay modelo (cualquier otro color) → click-through OFF
    """
    GWL_EXSTYLE       = -20
    WS_EX_LAYERED     = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW  = 0x00000080
    WS_EX_NOACTIVATE  = 0x08000000
    WS_EX_APPWINDOW   = 0x00040000

    try:
        from OpenGL.GL import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
        import ctypes

        px = max(0, min(int(lx), win_w - 1))
        py = max(0, min(int(win_h - 1 - ly), win_h - 1))

        pixel = glReadPixels(px, py, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)
        r, g, b = pixel[0], pixel[1], pixel[2]

        # Usar es_pixel_transparente() — condición exacta del spec
        es_transparente = es_pixel_transparente(r, g, b)

        if es_transparente == _ultimo_click_through[0]:
            return

        _ultimo_click_through[0] = es_transparente
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        base  = (style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
        new_style = (base | WS_EX_TRANSPARENT) if es_transparente else (base & ~WS_EX_TRANSPARENT)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

    except Exception:
        pass

def _force_topmost(hwnd):
    """Fuerza la ventana al frente de absolutamente todo, incluyendo la barra de tareas."""
    HWND_TOPMOST = -1
    SWP_NOMOVE     = 0x0002
    SWP_NOSIZE     = 0x0001
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    # Primera llamada: poner topmost
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    )
    # Segunda llamada: forzar sobre la shell (barra de tareas)
    # Usar BringWindowToTop + SetForegroundWindow sin robar foco
    ctypes.windll.user32.BringWindowToTop(hwnd)
    # Asegurar que el estilo TOPMOST persiste
    GWL_EXSTYLE   = -20
    WS_EX_TOPMOST = 0x00000008
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if not (style & WS_EX_TOPMOST):
        ctypes.windll.user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )

def load_prefs():
    try:
        if PREFS_FILE.exists():
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_prefs(x, y, w, h, estatico, posicion):
    try:
        PREFS_FILE.write_text(json.dumps(
            {"x":x,"y":y,"w":w,"h":h,"estatico":estatico,"posicion":posicion},
            indent=2), encoding="utf-8")
        print("[Alisha] ✓ Guardado")
    except Exception as e:
        print(f"[Alisha] Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT WEB EN HILO INDEPENDIENTE
# ═══════════════════════════════════════════════════════════════════════════════

def iniciar_chat():
    def _server():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", 5000)) == 0:
                    print("[Chat] ✓ Ya corriendo en localhost:5000")
                    return
            from web_app import app, socketio, _inicializar
            _inicializar()
            print("[Chat] ✓ Servidor iniciado")
            socketio.run(app, host="127.0.0.1", port=5000, debug=False,
                        allow_unsafe_werkzeug=True, use_reloader=False)
        except Exception as e:
            print(f"[Chat] Error: {e}")

    def _browser():
        # Esperar hasta que el servidor esté realmente listo (máx 15s)
        deadline = time.time() + 15.0
        while time.time() < deadline:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("localhost", 5000)) == 0:
                        webbrowser.open("http://localhost:5000")
                        print("[Chat] ✓ Navegador abierto")
                        return
            except Exception:
                pass
            time.sleep(0.5)
        print("[Chat] ⚠ No se pudo abrir el navegador — abrí http://localhost:5000 manualmente")

    threading.Thread(target=_server,  daemon=True).start()
    threading.Thread(target=_browser, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def _saludo_personalizado() -> None:
    """
    Modo Saludo: al despertar, Alisha ve la pantalla y genera un saludo
    personalizado según la hora y lo que está haciendo Cami.
    """
    import time as _t
    _t.sleep(2.0)  # esperar a que el modelo termine la secuencia de despertar
    try:
        from datetime import datetime
        hora = datetime.now().hour

        if 5 <= hora < 12:
            momento = "Buen día"
            emoji_hora = "☀️"
        elif 12 <= hora < 19:
            momento = "Buenas tardes"
            emoji_hora = "🌤️"
        else:
            momento = "Buenas noches"
            emoji_hora = "🌙"

        # Ver qué tiene abierto Cami
        ventana_actual = ""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            buf  = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            ventana_actual = buf.value.strip()
        except Exception:
            pass

        # Obtener último tema de conversación
        ultimo_tema = ""
        try:
            from memory import cargar_memoria
            mem = cargar_memoria()
            historial = mem.get("historial", [])
            if historial:
                ultimo_tema = historial[-1].get("entrada", "")[:50]
        except Exception:
            pass

        # Generar saludo con el brain
        try:
            from brain import get_brain
            brain = get_brain()

            contexto_ventana = f"Tiene abierto: '{ventana_actual}'" if ventana_actual else ""
            contexto_tema    = f"La última vez hablaron de: '{ultimo_tema}'" if ultimo_tema else ""

            prompt = (
                f"Sos Alisha, una IA argentina juvenil y con onda. "
                f"Acabás de despertar. Saludá a Cami con '{momento}' en voseo rioplatense. "
                f"{contexto_ventana}. {contexto_tema}. "
                f"Hacé un saludo corto (máx 2 oraciones), con personalidad, "
                f"que mencione lo que está haciendo o el último tema si es relevante. "
                f"Usá 'che', 'dale', 'boluda' si viene al caso. "
                f"Ejemplo: '¡Buenas, Cami! ¿Otra vez con el Emprendimiento? Dale que ya casi terminamos, no te cuelgues.'"
            )
            resp = brain.process(prompt)
            saludo = resp.content
        except Exception:
            saludo = f"¡{momento}, Cami! Ya estoy acá, ¿en qué andamos?"

        if not saludo:
            saludo = f"¡{momento}, Cami! Ya estoy despierta."

        print(f"[Alisha] 👋 {saludo}")

        # Hablar el saludo
        try:
            from audio_visual_sync import get_audio_visual_sync
            avs = get_audio_visual_sync()
            avs.speak(saludo, sarcasm_score=0.0,
                      emotional_state="alegría", async_mode=True)
        except Exception:
            try:
                from tts_engine import speak
                speak(saludo)
            except Exception:
                pass

        # Emitir al chat web
        try:
            from web_app import socketio
            socketio.emit("respuesta", {
                "texto": saludo,
                "estado_emocional": "alegría",
                "fuente": "saludo_inicial",
            })
        except Exception:
            pass

        # Expresión de saludo en el modelo
        try:
            from assistant_state import actualizar_estado
            actualizar_estado(estado="alegría", hablando=True, texto=saludo)
        except Exception:
            pass

    except Exception as e:
        print(f"[Alisha] Error en saludo personalizado: {e}")


# _KEYWORD_EXPRESSIONS y _expresion_por_texto() ELIMINADOS (FASE JCySharp)
# El texto de respuesta no elige expresiones. El estado emocional
# se refleja matemáticamente en los parámetros del modelo.


# ═══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE VARIABLES NUMÉRICAS (FASE JCySharp — Capítulo 2)
# ═══════════════════════════════════════════════════════════════════════════════

class SistemaVariables:
    """
    Todas las variables del sistema como valores numéricos puros (0.0-1.0).
    Nada aquí sabe que existe un avatar.
    Nada aquí elige gestos ni expresiones.
    Solo números que reflejan el estado real del sistema.
    """

    def __init__(self):
        # ── Variables de carga del sistema (de psutil) ──
        self.cpu_pct      = 0.0   # 0.0-1.0
        self.ram_pct      = 0.0   # 0.0-1.0

        # ── Variables de respuesta del LLM ──
        self.tiempo_respuesta  = 0.0  # 0.0-1.0 (0=rápido, 1=muy lento)
        self.profundidad_razon = 0.0  # 0.0-1.0
        self.frecuencia_error  = 0.0  # 0.0-1.0
        self.novedad_respuesta = 0.0  # 0.0-1.0

        # ── Variables emocionales (sincronizadas desde EstadoInterno) ──
        self.dopamina      = 0.75
        self.humor         = 0.70
        self.irritabilidad = 0.0
        self.tension       = 0.0
        self.flow          = 0.35

        # ── Variables de actividad del usuario ──
        self.teclas_por_minuto = 0.0  # 0.0-1.0 (150 TPM = máximo)
        self.tiempo_sin_input  = 0.0  # 0.0-1.0 (5 min = máximo)
        self.cambios_ventana   = 0.0  # 0.0-1.0 (10/min = máximo)

        # ── Variables de audio (lip-sync) ──
        self.amplitud_audio = 0.0   # 0.0-1.0 — RMS real del audio TTS
        self.hablando       = False

        # ── Variables de tiempo ──
        self.t            = 0.0    # tiempo acumulado en segundos
        self.hora_del_dia = 0.5    # 0.0=medianoche, 0.5=mediodía, 1.0=medianoche

    def actualizar_desde_hw(self, cpu_pct: float, ram_pct: float) -> None:
        """Actualiza variables de hardware desde psutil (0-100 → 0.0-1.0)."""
        self.cpu_pct = max(0.0, min(1.0, cpu_pct / 100.0))
        self.ram_pct = max(0.0, min(1.0, ram_pct / 100.0))

    def actualizar_desde_llm(self, tiempo_ms: float, complejidad: float,
                              errores: float, novedad: float) -> None:
        """Actualiza variables de rendimiento del LLM."""
        self.tiempo_respuesta  = min(1.0, tiempo_ms / 10000.0)
        self.profundidad_razon = max(0.0, min(1.0, complejidad))
        self.frecuencia_error  = max(0.0, min(1.0, errores))
        self.novedad_respuesta = max(0.0, min(1.0, novedad))

    def actualizar_desde_estado(self, ei: "EstadoInterno") -> None:
        """Sincroniza variables emocionales desde EstadoInterno."""
        self.dopamina      = ei.dopamina
        self.humor         = ei.humor
        self.irritabilidad = ei.irritabilidad
        self.tension       = ei.tension
        self.flow          = ei.flow
        self.hablando      = ei.hablando
        self.amplitud_audio = max(0.0, getattr(ei, "_mouth_amplitude", 0.0))

    def actualizar_desde_usuario(self, tpm: float, sin_input_s: float,
                                  cambios: float) -> None:
        """Actualiza variables de actividad del usuario."""
        self.teclas_por_minuto = min(1.0, tpm / 150.0)
        self.tiempo_sin_input  = min(1.0, sin_input_s / 300.0)
        self.cambios_ventana   = min(1.0, cambios / 10.0)

    def tick(self, dt: float) -> None:
        self.t += dt
        from datetime import datetime as _dt
        h = _dt.now().hour + _dt.now().minute / 60.0
        self.hora_del_dia = h / 24.0


# ═══════════════════════════════════════════════════════════════════════════════
# MOTOR DE MAPEO — variables numéricas → parámetros Live2D (FASE JCySharp)
# ═══════════════════════════════════════════════════════════════════════════════

class MotorMapeo:
    """
    Convierte variables del sistema en parámetros visuales mediante
    funciones matemáticas puras.

    REGLA DE ORO: ningún método aquí elige, decide, ni selecciona.
    Todo es transformación matemática: f(variables) → parámetros.
    """

    # Tiempos de suavizado diferenciados por zona corporal
    SMOOTH_TIMES: dict[str, float] = {
        "ParamAngleX":    0.15,
        "ParamAngleY":    0.15,
        "ParamAngleZ":    0.22,
        "ParamEyeLOpen":  0.05,
        "ParamEyeROpen":  0.05,
        "ParamEyeBallX":  0.10,
        "ParamEyeBallY":  0.10,
        "ParamEyeLSmile": 0.35,
        "ParamEyeRSmile": 0.35,
        "ParamBrowLAngle":0.28,
        "ParamBrowRAngle":0.28,
        "ParamBrowLForm": 0.35,
        "ParamBrowRForm": 0.35,
        "ParamMouthForm": 0.30,
        "ParamMouthOpenY":0.04,
        "ParamBreath":    0.55,
        "ParamHairFront": 0.32,
        "ParamHairFront2":0.40,
        "ParamHairFront3":0.48,
        "JingYa":         0.40,
        "WaiZui":         0.45,
        "ShouBing":       0.65,
        "JiaJu":          0.55,
    }

    def __init__(self, params_reales: list[str]):
        """
        params_reales: lista de IDs del modelo real (del diagnóstico).
        Solo se animarán parámetros que existan en esta lista.
        """
        self._params = set(params_reales)
        self._noise = {
            "micro_x": SimpleNoise(seed=10),
            "micro_y": SimpleNoise(seed=11),
            "micro_z": SimpleNoise(seed=12),
            "breath":  SimpleNoise(seed=13),
            "eye_x":   SimpleNoise(seed=14),
            "eye_y":   SimpleNoise(seed=15),
            "hair":    SimpleNoise(seed=16),
        }
        # Estado del parpadeo — controlado por tiempo, no por elección
        self._proximo_blink  = 0.0
        self._en_blink       = False
        self._blink_inicio   = 0.0
        self._blink_duracion = 0.12   # segundos de cierre
        self._blink_apertura = 0.08   # segundos de apertura

    def tiene(self, param_id: str) -> bool:
        return param_id in self._params

    # ── MAPEOS INDIVIDUALES ───────────────────────────────────────────────────

    def map_balanceo_z(self, sv: SistemaVariables) -> float:
        """
        ParamAngleZ — balanceo lateral del cuerpo.
        Tres ondas a distintas frecuencias + ruido. Nunca una sola frecuencia.
        Amplitud modulada por flow y dopamina. Pausa natural cada ~20s.
        """
        t = sv.t
        amp  = 1.5 + sv.flow * 2.5 + sv.dopamina * 0.8
        # Reducir si es tarde y hay poca actividad
        hora = sv.hora_del_dia
        if hora > 0.8 or hora < 0.15:
            amp *= (1.0 - sv.tiempo_sin_input * 0.4)
        freq = 0.18 + sv.dopamina * 0.08 - sv.tension * 0.05
        onda_1 = math.sin(2 * math.pi * freq * t)
        onda_2 = math.sin(2 * math.pi * freq * 2.1 * t + 0.7) * 0.3
        onda_3 = math.sin(2 * math.pi * freq * 0.43 * t + 1.2) * 0.15
        ruido  = self._noise["micro_z"].sample(t) * 0.4
        # Pausa natural cada ~20s
        pausa_ciclo = math.fmod(t, 22.0)
        if 18.0 < pausa_ciclo < 20.0:
            factor_pausa = 0.3 + 0.7 * (pausa_ciclo - 18.0) / 2.0
        else:
            factor_pausa = 1.0
        return (onda_1 + onda_2 + onda_3 + ruido) * amp * factor_pausa

    def map_parpadeo(self, sv: SistemaVariables) -> float:
        """
        ParamEyeLOpen / ParamEyeROpen — apertura de ojos.
        Intervalos IRREGULARES con random. Nunca math.fmod().
        Fase cierre: ease-in (progress²). Fase apertura: ease-out (√progress).
        """
        t = sv.t
        if self._proximo_blink == 0.0:
            self._proximo_blink = t + 3.0
        if not self._en_blink and t >= self._proximo_blink:
            self._en_blink    = True
            self._blink_inicio = t
            base = 4.0 - sv.tension * 1.5 + (1.0 if sv.hablando else 0.0)
            base = max(2.0, base)
            self._proximo_blink = t + base + random.uniform(-1.0, 2.5)
        if self._en_blink:
            elapsed = t - self._blink_inicio
            total   = self._blink_duracion + self._blink_apertura
            if elapsed < self._blink_duracion:
                progress = elapsed / self._blink_duracion
                apertura = 1.0 - (progress * progress)
            elif elapsed < total:
                progress = (elapsed - self._blink_duracion) / self._blink_apertura
                apertura = math.sqrt(max(0.0, progress))
            else:
                self._en_blink = False
                apertura = 1.0
        else:
            apertura = 1.0
        apertura_base  = 0.75 + sv.dopamina * 0.25
        cierre_tension = sv.tension * 0.3
        return apertura * apertura_base * (1.0 - cierre_tension)

    def map_mirada_x(self, sv: SistemaVariables, cursor_norm_x: float) -> float:
        """ParamEyeBallX — mirada horizontal."""
        t = sv.t
        peso_cursor = max(0.0, 1.0 - sv.tiempo_sin_input * 2.0)
        comp_cursor = cursor_norm_x * 0.8 * peso_cursor
        peso_deriva = 1.0 - peso_cursor
        deriva      = self._noise["eye_x"].sample(t * 0.3) * peso_deriva * 0.7
        escaneo     = 0.0
        if sv.cpu_pct > 0.5 and not sv.hablando:
            escaneo = math.sin(t * 2.5) * 0.5 * sv.cpu_pct
        micro = self._noise["micro_x"].sample(t * 0.8) * 0.08
        return comp_cursor + deriva + escaneo + micro

    def map_mirada_y(self, sv: SistemaVariables, cursor_norm_y: float) -> float:
        """ParamEyeBallY — mirada vertical."""
        t = sv.t
        peso_cursor     = max(0.0, 1.0 - sv.tiempo_sin_input * 2.0)
        comp_cursor     = -cursor_norm_y * 0.6 * peso_cursor
        pensando        = sv.tiempo_respuesta * sv.cpu_pct
        comp_pensar     = pensando * 0.4
        cansancio       = (1.0 - sv.dopamina) * sv.tiempo_sin_input
        comp_cansancio  = -cansancio * 0.3
        micro           = self._noise["eye_y"].sample(t * 0.7) * 0.06
        return comp_cursor + comp_pensar + comp_cansancio + micro

    def map_angulo_cabeza_x(self, sv: SistemaVariables) -> float:
        """ParamAngleX — inclinación vertical de cabeza."""
        pensando   = sv.tiempo_respuesta * 0.4
        cansancio  = (1.0 - sv.dopamina) * 5.0
        tension_up = sv.tension * -3.0
        micro      = self._noise["micro_y"].sample(sv.t * 0.2) * 1.5
        return pensando * -5.0 + cansancio + tension_up + micro

    def map_angulo_cabeza_y(self, sv: SistemaVariables, cursor_norm_x: float) -> float:
        """ParamAngleY — rotación horizontal de cabeza."""
        peso_cursor = max(0.0, 1.0 - sv.tiempo_sin_input * 1.5)
        return cursor_norm_x * 7.0 * peso_cursor

    def map_respiracion(self, sv: SistemaVariables) -> float:
        """ParamBreath — ciclo de respiración con frecuencia variable."""
        t    = sv.t
        freq = 0.16 + sv.tension * 0.18 + sv.cpu_pct * 0.10 - sv.flow * 0.06
        hora = sv.hora_del_dia
        if hora > 0.8 or hora < 0.15:
            freq -= 0.04
        freq  = max(0.10, min(0.35, freq))
        amp   = 0.5 - sv.tension * 0.2 + sv.flow * 0.2
        ruido = self._noise["breath"].sample(t * 0.15) * 0.08
        return math.sin(2 * math.pi * freq * t) * amp + 0.5 + ruido

    def map_sonrisa(self, sv: SistemaVariables) -> float:
        """ParamMouthForm — forma de boca. Resultado matemático de humor e irritabilidad."""
        base = sv.humor * 0.8 - 0.1
        base -= sv.irritabilidad * 0.6
        base -= sv.tension * 0.2
        onda  = math.sin(sv.t * 0.35) * 0.05
        return max(-1.0, min(1.0, base + onda))

    def map_cejas(self, sv: SistemaVariables) -> float:
        """ParamBrowAngle — ángulo de cejas."""
        base  = sv.humor * 0.3 - 0.1
        base -= sv.irritabilidad * 0.9
        base += sv.tension * 0.5
        micro = self._noise["micro_x"].sample(sv.t * 0.25) * 0.1
        return max(-1.0, min(1.0, base + micro))

    def map_pelo(self, sv: SistemaVariables,
                 angulo_z: float) -> tuple[float, float, float]:
        """ParamHairFront 1/2/3 — pelo con inercia escalonada."""
        t      = sv.t
        lag_1  = angulo_z * 0.22 + self._noise["hair"].sample(t * 0.4) * 0.6
        lag_2  = angulo_z * 0.16 + self._noise["hair"].sample(t * 0.3 + 1.0) * 0.4
        lag_3  = angulo_z * 0.11 + self._noise["hair"].sample(t * 0.2 + 2.0) * 0.3
        amp_flow = 1.0 + sv.flow * 0.5
        return (lag_1 * amp_flow, lag_2 * amp_flow, lag_3 * amp_flow)

    def map_boca_open(self, sv: SistemaVariables) -> float:
        """ParamMouthOpenY — lip-sync real o micro-variación en reposo."""
        if sv.hablando and sv.amplitud_audio >= 0.0:
            return sv.amplitud_audio
        return abs(math.sin(sv.t * 12.0)) * 0.02 * sv.dopamina

    def map_shou_bing(self, sv: SistemaVariables) -> float:
        """ShouBing — brazo derecho, modulado por flow y balanceo."""
        sway = math.sin(sv.t * (0.18 + sv.dopamina * 0.08))
        return max(0.0, min(0.85,
            0.35 + sway * 0.25 + sv.flow * 0.20))

    def map_jia_ju(self, sv: SistemaVariables) -> float:
        """JiaJu — muñeca/mano, más activa al hablar."""
        boost = 1.8 if sv.hablando else 1.0
        freq  = 0.18 + sv.dopamina * 0.08
        val   = (math.sin(sv.t * freq * 1.4 + 2.1) * 0.30
                 + math.sin(sv.t * freq * 0.7 + 0.5) * 0.15) * boost
        return max(-0.5, min(0.5, val))

    def calcular_todos(self, sv: SistemaVariables,
                       cursor_norm_x: float,
                       cursor_norm_y: float) -> dict[str, float]:
        """
        Punto de entrada principal.
        Retorna {param_id: valor} solo para parámetros que existen en el modelo.
        """
        angulo_z = self.map_balanceo_z(sv)
        hair1, hair2, hair3 = self.map_pelo(sv, angulo_z)
        parpadeo = self.map_parpadeo(sv)
        sonrisa  = self.map_sonrisa(sv)
        cejas    = self.map_cejas(sv)

        resultados: dict[str, float] = {
            # Cabeza
            "ParamAngleZ":     angulo_z,
            "ParamAngleX":     self.map_angulo_cabeza_x(sv),
            "ParamAngleY":     self.map_angulo_cabeza_y(sv, cursor_norm_x),
            # Ojos
            "ParamEyeLOpen":   parpadeo,
            "ParamEyeROpen":   parpadeo,
            "ParamEyeBallX":   self.map_mirada_x(sv, cursor_norm_x),
            "ParamEyeBallY":   self.map_mirada_y(sv, cursor_norm_y),
            "ParamEyeLSmile":  max(0.0, sonrisa),
            "ParamEyeRSmile":  max(0.0, sonrisa),
            # Cejas
            "ParamBrowLAngle": cejas,
            "ParamBrowRAngle": cejas,
            "ParamBrowLForm":  max(-1.0, min(1.0, -sv.irritabilidad * 0.6)),
            "ParamBrowRForm":  max(-1.0, min(1.0, -sv.irritabilidad * 0.6)),
            # Boca
            "ParamMouthForm":  sonrisa,
            "ParamMouthOpenY": self.map_boca_open(sv),
            # Cuerpo
            "ParamBreath":     self.map_respiracion(sv),
            # Pelo
            "ParamHairFront":  hair1,
            "ParamHairFront2": hair2,
            "ParamHairFront3": hair3,
            # Expresión corporal
            "JingYa":          sv.tension * 0.7,
            "WaiZui":          sv.irritabilidad * 0.5,
            "ShouBing":        self.map_shou_bing(sv),
            "JiaJu":           self.map_jia_ju(sv),
        }
        # Solo retornar parámetros que existen en el modelo real
        return {k: v for k, v in resultados.items() if self.tiene(k)}


def main():
    # (instancia única desactivada temporalmente — usar Task Manager si hay duplicados)

    prefs  = load_prefs()
    sw, sh = screen_size()

    win_w    = prefs.get("w", W_DEF)
    win_h    = prefs.get("h", H_DEF)
    win_x    = prefs.get("x", sw - win_w - 10)
    win_y    = prefs.get("y", sh - win_h - 10)
    estatico = prefs.get("estatico", False)
    posicion = prefs.get("posicion", "inferior")   # "superior" | "inferior"

    if not glfw.init():
        sys.exit("[GLFW] init falló")

    glfw.window_hint(glfw.DECORATED,               glfw.FALSE)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, glfw.TRUE)
    glfw.window_hint(glfw.FLOATING,                glfw.TRUE)
    glfw.window_hint(glfw.FOCUS_ON_SHOW,           glfw.FALSE)
    glfw.window_hint(glfw.SAMPLES,                 0)
    glfw.window_hint(glfw.DOUBLEBUFFER,            glfw.TRUE)
    glfw.window_hint(glfw.VISIBLE,                 glfw.FALSE)  # oculta al crear

    win = glfw.create_window(win_w, win_h, "Alisha", None, None)
    if not win:
        glfw.terminate()
        sys.exit("[GLFW] create_window falló")

    glfw.set_window_pos(win, win_x, win_y)
    glfw.make_context_current(win)
    glfw.swap_interval(1)   # VSync ON — sincroniza con el monitor, frames uniformes sin sleep

    hwnd = glfw.get_win32_window(win)
    setup_window(hwnd)      # WS_EX_TOOLWINDOW aplicado ANTES de mostrar
    glfw.show_window(win)   # mostrar después de configurar — no aparece en taskbar
    _glfw_win_ref[0] = win  # guardar referencia para toggle de pausa

    live2d.init()
    live2d.glInit()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # Verde puro = color key transparente — IceGirl no tiene verde en ninguna textura
    # Evita el parpadeo en mangas blancas que causaba el magenta
    glClearColor(0.0, 1.0, 0.0, 1.0)
    glViewport(0, 0, win_w, win_h)

    for _ in range(4):
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
        try: live2d.clearBuffer()
        except Exception: pass
        glfw.swap_buffers(win)
        glfw.poll_events()
    model = live2d.LAppModel()
    model.LoadModelJson(LIVE2D_MODEL_PATH)
    model.Resize(win_w, win_h)
    # Desactivar auto-animaciones internas que causan ghosting
    # PERO mantener la física del modelo activa (pelo, alas, ropa)
    try: model.SetAutoBlinkEnable(False)   # parpadeo manual (más control)
    except Exception: pass
    try: model.SetAutoBreathEnable(False)  # respiración manual (más control)
    except Exception: pass
    # NO desactivar física — permite que pelo y alas reaccionen naturalmente
    # try: model.StopAllMotions()  # ← comentado: permite motions de física
    try: model.StopAllMotions()
    except Exception: pass
    # set_expr eliminado — el avatar no elige expresiones (FASE JCySharp)
    print(f"[Live2D] ✓ IceGirl ({win_w}×{win_h})")
    print("  Click izq=humor | Click der+drag=mover | Rueda=zoom")
    print("  Ctrl+S=guardar | Ctrl+E=estático | Ctrl+R=reset")
    print("  Ctrl+P=ocultar/mostrar | Ctrl+T=borde superior | Ctrl+B=borde inferior | ESC=cerrar")

    # ── PASO 5: Inicializar sistema de animación matemático (FASE JCySharp) ──
    params_reales: list[str] = []
    try:
        _count = model.GetParameterCount()
        params_reales = list(model.GetParamIds())
        print(f"[Live2D] {len(params_reales)} parámetros disponibles para animación")
    except Exception as _pe:
        print(f"[Live2D] No se pudo obtener lista de parámetros: {_pe}")

    sv    = SistemaVariables()
    motor = MotorMapeo(params_reales)
    print("[Alisha] ✓ Sistema de animación 100% matemático iniciado")

    # ── Sistemas: solo Media Sync y Trust (SIN voz — eso lo maneja web_app.py) ─
    def _iniciar_cerebro():
        """
        cabina_virtual.py es SOLO el motor visual.
        NO inicia sistemas de voz — eso lo hace web_app.py para evitar doble voz.
        Solo inicia: Media Sync (para que el cuerpo reaccione a la música).
        """
        # Media Sync → chibi_state.json (para que el cuerpo reaccione a la música)
        def _media_sync_loop():
            import time as _t
            _ultimo_titulo = ""
            while True:
                try:
                    from alisha_media import get_media_info
                    info = get_media_info()
                    if info and info.get("title"):
                        titulo = info.get("title", "")
                        if titulo != _ultimo_titulo:
                            _ultimo_titulo = titulo
                            print(f"[Alisha] 🎵 Música: {titulo}")
                        try:
                            _sf = STATE_FILE
                            _data = {}
                            if _sf.exists():
                                try:
                                    _data = json.loads(_sf.read_text(encoding="utf-8"))
                                except Exception:
                                    pass
                            _data["media_flow_boost"] = 0.8
                            _data["media_actual"] = {
                                "title": titulo,
                                "artist": info.get("artist", ""),
                                "app": info.get("app", ""),
                            }
                            _sf.write_text(json.dumps(_data, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                    else:
                        _ultimo_titulo = ""
                        try:
                            _sf = STATE_FILE
                            _data = {}
                            if _sf.exists():
                                try:
                                    _data = json.loads(_sf.read_text(encoding="utf-8"))
                                except Exception:
                                    pass
                            _data.pop("media_flow_boost", None)
                            _sf.write_text(json.dumps(_data, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                except Exception:
                    pass
                _t.sleep(5.0)

        threading.Thread(target=_media_sync_loop, daemon=True, name="MediaSync").start()
        print("[Alisha] 🎵 Media Sync iniciado (sin voz — voz en web_app)")

    threading.Thread(target=_iniciar_cerebro, daemon=True).start()

    # ── Hardware sampler — CPU/RAM → parámetros Live2D ────────────────────────
    _iniciar_hw_sampler()

    # ── Sistema de Sueño/Despertar ────────────────────────────────────────────
    try:
        from alisha_sleep_anim import iniciar as _iniciar_sueno, esta_dormida, despertar
        def _on_despierta():
            print("[Alisha] Despierta y lista")
            try:
                from alisha_trust import iniciar_timer_uso, log_estado
                iniciar_timer_uso()
                log_estado()
            except Exception:
                pass
            # El saludo de voz lo maneja alisha_sleep.py — no iniciamos uno aquí

        _iniciar_sueno(callback_despierta=_on_despierta, arrancar_dormida=True)
        print("[Alisha] Sistema de sueno/despertar iniciado")
    except Exception as e:
        print(f"[Alisha] SleepAnim: {e}")
        esta_dormida = lambda: False
        despertar    = lambda m="": None

    # ── Estado interno (con persistencia emocional) ───────────────────────────
    ei             = EstadoInterno(estado_previo=cargar_estado_emocional())
    # Análisis semanal en hilo separado (no bloquea el render)
    analisis_semanal_async(ei)
    estado_emocional = "neutral"
    ultimo_check   = 0.0
    ultimo_ventana = 0.0
    # ultimo_expr / proximo_expr eliminados — no hay cambio de expresión por timer
    anim_t         = 0.0

    # ── Valores suavizados actuales de cada parámetro ─────────────────────────
    # Todos empiezan en su valor de reposo
    cur = {
        "ParamAngleX":    0.0,
        "ParamAngleY":    0.0,
        "ParamAngleZ":    0.0,
        "ParamEyeBallX":  0.0,
        "ParamEyeBallY":  0.0,
        "ParamEyeLOpen":  1.0,
        "ParamEyeROpen":  1.0,
        "ParamEyeLSmile": 0.0,
        "ParamEyeRSmile": 0.0,
        "ParamBrowLAngle":0.0,
        "ParamBrowRAngle":0.0,
        "ParamBrowLForm": 0.0,
        "ParamBrowRForm": 0.0,
        "ParamMouthForm": 0.3,
        "ParamMouthOpenY":0.0,
        "ParamBreath":    0.5,
        "ShouBing":       0.0,
        "JiaJu":          0.0,
        "JingYa":         0.0,
        "WaiZui":         0.0,
        "ParamHairFront": 0.0,
        "ParamHairFront2":0.0,
        "ParamHairFront3":0.0,
    }
    # Velocidades para smooth_damp
    vel = {k: [0.0] for k in cur}

    # ── Seguimiento de mouse ──────────────────────────────────────────────────
    # Modo de mirada eliminado — el MotorMapeo maneja la mirada matemáticamente
    # según tiempo_sin_input, cpu_pct y cursor en tiempo real

    # ── Drag ──────────────────────────────────────────────────────────────────
    dragging       = False
    drag_win_start = (win_x, win_y)
    drag_cur_start = (0.0, 0.0)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def on_mouse_button(w, btn, action, mods):
        nonlocal dragging, drag_win_start, drag_cur_start

        if btn == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
            if not estatico:
                ei.clic()
                # Irritabilidad sube con clics — se refleja matemáticamente en cejas/boca

        elif btn == glfw.MOUSE_BUTTON_RIGHT:
            if action == glfw.PRESS and not estatico:
                dragging       = True
                drag_win_start = glfw.get_window_pos(w)
                lx, ly         = glfw.get_cursor_pos(w)
                wx, wy         = drag_win_start
                drag_cur_start = (wx + lx, wy + ly)
                # Tensión sube al arrastrar — se refleja matemáticamente
                ei.tension = min(1.0, ei.tension + 0.1)
            elif action == glfw.RELEASE and dragging:
                nx, ny = glfw.get_window_pos(w)
                save_prefs(nx, ny, win_w, win_h, estatico, posicion)
                dragging = False

    def on_cursor_pos(w, lx, ly):
        if not dragging or estatico: return
        # cursor global actual = pos ventana actual + cursor local
        wx, wy = glfw.get_window_pos(w)
        gcx = wx + lx
        gcy = wy + ly
        # offset = cursor global inicio - pos ventana inicio
        ox = drag_cur_start[0] - drag_win_start[0]
        oy = drag_cur_start[1] - drag_win_start[1]
        glfw.set_window_pos(w, int(gcx - ox), int(gcy - oy))

    def on_scroll(w, xoff, yoff):
        nonlocal win_w, win_h
        if estatico: return
        factor = 1.1 if yoff > 0 else 0.9
        nw = max(W_MIN, min(W_MAX, int(win_w * factor)))
        nh = int(win_h * nw / win_w)
        wx, wy = glfw.get_window_pos(w)
        glfw.set_window_size(w, nw, nh)
        glfw.set_window_pos(w, wx - (nw - win_w)//2, wy - (nh - win_h)//2)
        model.Resize(nw, nh)
        glViewport(0, 0, nw, nh)
        win_w, win_h = nw, nh

    def on_key(w, key, sc, action, mods):
        nonlocal estatico, win_w, win_h, posicion
        if action != glfw.PRESS: return
        ctrl = mods & glfw.MOD_CONTROL
        if   key == glfw.KEY_ESCAPE:         glfw.set_window_should_close(w, True)
        elif key == glfw.KEY_P and ctrl:
            # Ctrl+P → toggle pausa (ocultar/mostrar modelo 2D)
            _toggle_pausa()
        elif key == glfw.KEY_S and ctrl:
            nx, ny = glfw.get_window_pos(w)
            save_prefs(nx, ny, win_w, win_h, estatico, posicion)
        elif key == glfw.KEY_E and ctrl:
            estatico = not estatico
            print(f"[Alisha] Estático: {'ON' if estatico else 'OFF'}")
        elif key == glfw.KEY_R and ctrl:
            glfw.set_window_size(w, W_DEF, H_DEF)
            model.Resize(W_DEF, H_DEF)
            glViewport(0, 0, W_DEF, H_DEF)
            win_w, win_h = W_DEF, H_DEF
        elif key == glfw.KEY_T and ctrl:
            # Mover a borde superior
            posicion = "superior"
            nx, ny = glfw.get_window_pos(w)
            glfw.set_window_pos(w, nx, 0)
            print("[Alisha] Posición: borde superior")
        elif key == glfw.KEY_B and ctrl:
            # Mover a borde inferior
            posicion = "inferior"
            nx, _ = glfw.get_window_pos(w)
            glfw.set_window_pos(w, nx, sh - win_h - 10)
            print("[Alisha] Posición: borde inferior")

    def on_fb_size(w, fw, fh):
        nonlocal win_w, win_h
        glViewport(0, 0, fw, fh)
        model.Resize(fw, fh)
        win_w, win_h = fw, fh

    glfw.set_mouse_button_callback(win,     on_mouse_button)
    glfw.set_cursor_pos_callback(win,       on_cursor_pos)
    glfw.set_scroll_callback(win,           on_scroll)
    glfw.set_key_callback(win,              on_key)
    glfw.set_framebuffer_size_callback(win, on_fb_size)

    # ── Loop principal — 60 FPS fijo ─────────────────────────────────────────
    last_t       = time.time()
    FRAME_DT     = 1.0 / 60.0
    ultimo_topmost = 0.0

    while not glfw.window_should_close(win):
        now = time.time()
        dt  = min(now - last_t, 0.05)
        last_t = now
        anim_t += dt

        # ── Si está pausada: solo procesar eventos y dormir ───────────────────
        if _PAUSADA:
            glfw.poll_events()
            time.sleep(0.05)
            continue

        # ── Topmost periódico — cada 500ms para mantenerse siempre al frente ──
        if now - ultimo_topmost > 0.5:
            ultimo_topmost = now
            _force_topmost(hwnd)

        # ── Click-through dinámico — cada frame ───────────────────────────────
        lx_cur, ly_cur = glfw.get_cursor_pos(win)
        _actualizar_click_through(hwnd, lx_cur, ly_cur, win_w, win_h)

        # ── Tick estado interno ───────────────────────────────────────────────
        ei.tick(dt)

        # ── Leer chibi_state.json — estado emocional + lip-sync (cada 50ms) ──
        if now - ultimo_check > 0.05:
            ultimo_check = now

            # ── Modo sueño: aplicar parámetros de sueño si está dormida ──────
            try:
                if STATE_FILE.exists():
                    _sd = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    if _sd.get("sleep_mode", False):
                        _phase = _sd.get("sleep_phase", "dormida")
                        _eye   = _sd.get("sleep_eye_open", 0.0)
                        _brt   = _sd.get("sleep_breath", 0.15)
                        _ay    = _sd.get("sleep_angle_y", 8.0)
                        _az    = _sd.get("sleep_angle_z", 3.0)
                        _mo    = _sd.get("sleep_mouth_open", 0.0)
                        # Aplicar suavemente
                        cur["ParamEyeLOpen"]   = cur["ParamEyeLOpen"]   * 0.9 + _eye * 0.1
                        cur["ParamEyeROpen"]   = cur["ParamEyeROpen"]   * 0.9 + _eye * 0.1
                        cur["ParamBreath"]     = cur["ParamBreath"]     * 0.95 + _brt * 0.05
                        cur["ParamAngleY"]     = cur["ParamAngleY"]     * 0.95 + _ay  * 0.05
                        cur["ParamAngleZ"]     = cur["ParamAngleZ"]     * 0.95 + _az  * 0.05
                        cur["ParamMouthOpenY"] = cur["ParamMouthOpenY"] * 0.9 + _mo  * 0.1
                        # Aplicar al modelo directamente
                        for _pk, _pv in [
                            ("ParamEyeLOpen",   cur["ParamEyeLOpen"]),
                            ("ParamEyeROpen",   cur["ParamEyeROpen"]),
                            ("ParamBreath",     cur["ParamBreath"]),
                            ("ParamAngleY",     cur["ParamAngleY"]),
                            ("ParamAngleZ",     cur["ParamAngleZ"]),
                            ("ParamMouthOpenY", cur["ParamMouthOpenY"]),
                        ]:
                            try: model.SetParameterValue(_pk, _pv)
                            except Exception: pass
                        # Saltar el resto del loop de parámetros
                        glEnable(GL_BLEND)
                        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
                        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
                        try: live2d.clearBuffer()
                        except Exception: pass
                        model.Update()
                        model.Draw()
                        glfw.swap_buffers(win)
                        glfw.poll_events()
                        elapsed = time.time() - now
                        sleep_t = FRAME_DT - elapsed
                        if sleep_t > 0.001:
                            time.sleep(sleep_t)
                        continue
            except Exception:
                pass
            try:
                # Prioridad 1: leer del bridge en memoria (0ms latencia)
                import alisha_bridge
                if alisha_bridge.IS_SPEAKING:
                    ei.hablando = True
                    ei._mouth_amplitude = alisha_bridge.MOUTH_AMPLITUDE
                else:
                    ei.hablando = False
                    ei._mouth_amplitude = 0.0
            except Exception:
                pass

            # ── Hardware → EstadoInterno (lee valores ya cacheados, sin I/O) ──
            if _PSUTIL_OK:
                # CPU alta → tensión sube (cejas fruncidas, respiración rápida)
                # Mapeo: 0% → +0.00 tensión | 100% → +0.35 tensión
                cpu_tension = _hw_to_live2d(_HW_CPU_PCT, 0.0, 0.35)
                ei.tension  = min(1.0, ei.tension * 0.98 + cpu_tension * 0.02)

                # RAM alta → dopamina baja (avatar más cansado/apagado)
                # Mapeo: 0% → 0.000 penalización | 100% → 0.015 por frame
                ram_penalty = _hw_to_live2d(_HW_RAM_PCT, 0.0, 0.15)
                ei.dopamina = max(0.4, ei.dopamina - ram_penalty * 0.005)

                # CPU muy alta (>85%) → ParamBreath se acelera directamente
                if _HW_CPU_PCT > 85.0:
                    cur["ParamBreath"] = cur.get("ParamBreath", 0.5) * 0.95 + 0.9 * 0.05

            try:
                if STATE_FILE.exists():
                    d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    nuevo    = d.get("estado", "neutral")
                    hablando = d.get("hablando", False)
                    # Solo actualizar hablando desde JSON si el bridge no está activo
                    try:
                        import alisha_bridge as _ab
                        if not _ab.IS_SPEAKING:
                            ei.set_desde_chibi(nuevo, hablando)
                    except Exception:
                        ei.set_desde_chibi(nuevo, hablando)

                    if nuevo != estado_emocional:
                        estado_emocional = nuevo
                        # set_expr eliminado — el cambio de estado emocional
                        # se refleja matemáticamente en los parámetros del motor

                    # ── Expresión por palabras clave ELIMINADA ────────────────
                    # El texto de respuesta no elige expresiones (FASE JCySharp)

                    # Gaze override
                    if d.get("gaze_override"):
                        gaze_x = d.get("gaze_x", 0.0)
                        gaze_y = d.get("gaze_y", 0.0)
                        if "ParamEyeBallX" in cur:
                            cur["ParamEyeBallX"] = cur["ParamEyeBallX"] * 0.7 + gaze_x * 0.3
                            cur["ParamEyeBallY"] = cur["ParamEyeBallY"] * 0.7 + gaze_y * 0.3

                    # Sarcasmo → irritabilidad
                    _sarcasm = d.get("sarcasm_score", 0.0)
                    if _sarcasm > 0.7:
                        ei.irritabilidad = min(1.0, ei.irritabilidad + 0.3)
                    elif _sarcasm > 0.3:
                        ei.tension = min(1.0, ei.tension + 0.2)

                    # ── Reflejos biométricos del Cerebro → Cuerpo ────────────
                    # brain.py escribe brain_dopamina/humor/irritabilidad cuando
                    # procesa con éxito o detecta un error. cabina_virtual los
                    # lee aquí y los aplica con lerp suave al EstadoInterno.
                    _b_dopa = d.get("brain_dopamina", -1.0)
                    _b_humor = d.get("brain_humor", -1.0)
                    _b_irrit = d.get("brain_irritabilidad", -1.0)
                    _b_tension = d.get("brain_tension", -1.0)
                    _b_flow = d.get("brain_flow", -1.0)
                    if _b_dopa >= 0.0:
                        # Lerp suave: 15% del valor del cerebro por frame de lectura
                        ei.dopamina = ei.dopamina * 0.85 + _b_dopa * 0.15
                    if _b_humor >= 0.0:
                        ei.humor = ei.humor * 0.85 + _b_humor * 0.15
                    if _b_irrit >= 0.0:
                        ei.irritabilidad = ei.irritabilidad * 0.85 + _b_irrit * 0.15
                    if _b_tension >= 0.0:
                        ei.tension = ei.tension * 0.85 + _b_tension * 0.15
                    if _b_flow >= 0.0:
                        ei.flow = ei.flow * 0.85 + _b_flow * 0.15

                    # ── Media Sync → boost de flow cuando hay música ──────────
                    _media_boost = d.get("media_flow_boost", -1.0)
                    if _media_boost >= 0.0:
                        # Música activa → flow sube hacia 0.8 (más balanceo y energía)
                        ei.flow = ei.flow * 0.97 + _media_boost * 0.03
                        ei.dopamina = min(1.0, ei.dopamina + 0.001)

                    modo = d.get("modo", "IDLE")
                    if modo == "THINKING":
                        # Mirar hacia arriba — gesto de pensar
                        if "ParamAngleX" in cur:
                            cur["ParamAngleX"] = cur["ParamAngleX"] * 0.9 + (-6.0) * 0.1
                        if "ParamEyeBallY" in cur:
                            cur["ParamEyeBallY"] = cur["ParamEyeBallY"] * 0.9 + 0.4 * 0.1
                        # Dopamina baja levemente mientras piensa
                        ei.dopamina = max(0.4, ei.dopamina - 0.001)
                    elif modo == "WORKING":
                        # Ojos moviéndose de lado a lado — leyendo pantalla
                        _scan_x = math.sin(anim_t * 2.5) * 0.7
                        if "ParamEyeBallX" in cur:
                            cur["ParamEyeBallX"] = cur["ParamEyeBallX"] * 0.8 + _scan_x * 0.2
                        ei.tension = min(0.6, ei.tension + 0.002)
                    elif modo == "IDLE":
                        # Dopamina se recupera en idle
                        ei.dopamina = min(0.8, ei.dopamina + 0.0005)

                    # ── Dopamina alta → brillo en ojos y sonrisa ─────────────
                    if ei.dopamina > 0.85:
                        # Ojos más abiertos y brillantes
                        if "ParamEyeLOpen" in cur:
                            cur["ParamEyeLOpen"] = min(1.0, cur["ParamEyeLOpen"] + 0.02)
                            cur["ParamEyeROpen"] = min(1.0, cur["ParamEyeROpen"] + 0.02)
                        # Sonrisa más amplia
                        if "ParamEyeLSmile" in cur:
                            cur["ParamEyeLSmile"] = min(1.0, cur["ParamEyeLSmile"] + 0.01)
                            cur["ParamEyeRSmile"] = min(1.0, cur["ParamEyeRSmile"] + 0.01)
                    # ── Dopamina baja → encorvarse, mirar hacia abajo ─────────
                    elif ei.dopamina < 0.3:
                        if "ParamAngleX" in cur:
                            cur["ParamAngleX"] = cur["ParamAngleX"] * 0.95 + 5.0 * 0.05
                        if "ParamEyeBallY" in cur:
                            cur["ParamEyeBallY"] = cur["ParamEyeBallY"] * 0.95 + (-0.3) * 0.05

                    # Lip-sync fallback desde JSON (si bridge no disponible)
                    try:
                        import alisha_bridge as _ab
                        if not _ab.IS_SPEAKING:
                            _amp = d.get("mouth_amplitude", -1.0)
                            if hablando and _amp >= 0.0:
                                ei._mouth_amplitude = float(_amp)
                            elif not hablando:
                                ei._mouth_amplitude = 0.0
                    except Exception:
                        _amp = d.get("mouth_amplitude", -1.0)
                        if hablando and _amp >= 0.0:
                            ei._mouth_amplitude = float(_amp)

            except Exception:
                pass

        # ── Análisis de ventana activa ────────────────────────────────────────
        if now - ultimo_ventana > 2.5:
            ultimo_ventana = now
            titulo = get_active_window_title()
            cat    = analizar_ventana(titulo)
            ei.set_categoria(cat)

        # ── Cambio de expresión periódico ELIMINADO (FASE JCySharp) ──────────
        # El estado emocional se refleja matemáticamente en los parámetros.
        # No hay expresiones elegidas por timer.

        # ── Modo de mirada ELIMINADO — MotorMapeo lo maneja matemáticamente ──

        # ── PASO 4: Sistema de animación matemático (FASE JCySharp) ─────────────
        # Actualizar SistemaVariables con datos reales del sistema
        sv.tick(dt)
        sv.actualizar_desde_hw(_HW_CPU_PCT, _HW_RAM_PCT)
        sv.actualizar_desde_estado(ei)

        # Cursor normalizado [-1, 1]
        lx, ly = glfw.get_cursor_pos(win)
        cursor_norm_x = (lx / max(win_w, 1)) * 2.0 - 1.0
        cursor_norm_y = (ly / max(win_h, 1)) * 2.0 - 1.0

        # Calcular todos los targets con el motor matemático
        targets = motor.calcular_todos(sv, cursor_norm_x, cursor_norm_y)

        # Aplicar smooth_damp con tiempos diferenciados por zona corporal
        def sd(key: str, target: float, smooth: float = 0.20) -> None:
            if key not in cur:
                cur[key] = 0.0
                vel[key] = [0.0]
            cur[key] = smooth_damp(cur[key], target, vel[key], smooth, dt)
            try:
                model.SetParameterValue(key, cur[key])
            except Exception:
                pass

        for param_id, target in targets.items():
            smooth = motor.SMOOTH_TIMES.get(param_id, 0.25)
            sd(param_id, target, smooth)

        # ── Brazos y rotaciones de malla — siguen el balanceo matemático ─────
        # Calculados aquí porque usan sway derivado del balanceo del motor
        _angulo_z = cur.get("ParamAngleZ", 0.0)
        _freq     = 0.18 + sv.dopamina * 0.08
        _sway     = math.sin(sv.t * _freq)
        _sway_f   = math.sin(sv.t * _freq * 2.3 + 0.7)
        _sway_s   = math.sin(sv.t * _freq * 0.4 + 1.2)

        _arm_l = max(-0.7, min(0.7, _sway * -0.45 + _sway_s * 0.20 + 0.10))
        _arm_r = max(-0.7, min(0.7, _sway *  0.45 + _sway_f * 0.15 + 0.10))
        _hand  = math.sin(sv.t * _freq * 1.0 + 0.8) * 0.40
        _shldr = math.sin(sv.t * 0.5) * 0.25
        _daiji = max(0.0, min(0.6, 0.4 - sv.flow * 0.4))

        sd("ParamArmL",      _arm_l,  0.50)
        sd("ParamArmR",      _arm_r,  0.50)
        sd("Param_Arm_L",    _arm_l,  0.50)
        sd("Param_Arm_R",    _arm_r,  0.50)
        sd("ArmL",           _arm_l,  0.50)
        sd("ArmR",           _arm_r,  0.50)
        sd("ParamHandL",     _hand,   0.45)
        sd("ParamHandR",     _hand,   0.45)
        sd("手臂",            _arm_r,  0.50)
        sd("手",              _hand,   0.45)
        sd("ParamShoulderL", _shldr,  0.60)
        sd("ParamShoulderR", _shldr,  0.60)
        sd("肩",              _shldr,  0.60)
        sd("DaiJi",          _daiji,  0.70)

        # Rotaciones de malla — moduladas por dopamina y flow
        _torso = _sway * 1.0 * sv.dopamina
        _arm_e = _sway_f * 1.2 * (0.3 + sv.flow * 0.4 + sv.dopamina * 0.3)
        sd("Param_Angle_Rotation_1_ArtMesh11", _torso,        0.45)
        sd("Param_Angle_Rotation_2_ArtMesh11", _torso * 0.7,  0.50)
        sd("Param_Angle_Rotation_1_ArtMesh12", _torso * 0.8,  0.48)
        sd("Param_Angle_Rotation_2_ArtMesh12", _torso * 0.5,  0.52)
        sd("Param_Angle_Rotation_1_ArtMesh95", _arm_e,        0.45)
        sd("Param_Angle_Rotation_2_ArtMesh95", _arm_e * 0.6,  0.50)
        sd("Param_Angle_Rotation_1_ArtMesh96", _arm_e * 0.8,  0.48)
        sd("Param_Angle_Rotation_1_ArtMesh97", _sway * 0.8,   0.50)
        sd("Param_Angle_Rotation_1_ArtMesh98", _sway_s * 0.7, 0.55)

        # ── Motion idle — desactivado (usamos parámetros directos) ──────────
        # StartMotion causa ghosting al mezclarse con el control por parámetros

        # ── Render ────────────────────────────────────────────────────────────
        # Restaurar estado de blending antes de cada draw — Live2D puede
        # modificar el estado OpenGL internamente (máscaras de recorte, capas).
        # Sin esto, las capas semitransparentes parpadean o se transparentan mal.
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
        try: live2d.clearBuffer()
        except Exception: pass
        model.Update()
        model.Draw()
        glfw.swap_buffers(win)
        glfw.poll_events()

        # Control de 60 FPS — sleep el tiempo restante del frame
        elapsed = time.time() - now
        sleep_t = FRAME_DT - elapsed
        if sleep_t > 0.001:
            time.sleep(sleep_t)
    # Guardar al cerrar
    nx, ny = glfw.get_window_pos(win)
    save_prefs(nx, ny, win_w, win_h, estatico, posicion)
    guardar_estado_emocional(ei)   # persistencia emocional
    model.DeleteModel()
    live2d.dispose()
    glfw.destroy_window(win)
    glfw.terminate()


if __name__ == "__main__":
    # Ocultar consola completamente — ícono en bandeja del sistema (system tray)
    try:
        import ctypes as _ctypes
        hwnd_console = _ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd_console:
            _ctypes.windll.user32.ShowWindow(hwnd_console, 0)  # SW_HIDE = ocultar completamente
    except Exception:
        pass

    # Ícono en bandeja del sistema
    def _tray():
        try:
            import pystray
            from PIL import Image, ImageDraw

            # Crear ícono rosa simple
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill=(244, 143, 177, 255))  # rosa
            draw.ellipse([20, 20, 44, 44], fill=(255, 255, 255, 200))  # centro blanco

            def on_abrir(icon, item):
                try:
                    import webbrowser
                    webbrowser.open("http://localhost:5000")
                except Exception:
                    pass

            def on_toggle_pausa(icon, item):
                """Oculta/muestra el modelo 2D y silencia/activa la voz."""
                _toggle_pausa()
                # Actualizar el título del ítem en el menú
                icon.update_menu()

            def on_cerrar(icon, item):
                icon.stop()
                import os, signal
                os.kill(os.getpid(), signal.SIGTERM)

            menu = pystray.Menu(
                pystray.MenuItem("Abrir chat", on_abrir),
                pystray.MenuItem(
                    lambda item: "▶ Mostrar Alisha" if _PAUSADA else "⏸ Ocultar Alisha",
                    on_toggle_pausa
                ),
                pystray.MenuItem("Cerrar Alisha", on_cerrar),
            )
            icon = pystray.Icon("Alisha", img, "Alisha IA", menu)
            icon.run()
        except Exception as e:
            print(f"[Tray] Error: {e}")

    import threading as _threading
    _threading.Thread(target=_tray, daemon=True).start()

    main()
