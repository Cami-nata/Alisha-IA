"""
alisha_identity.py — Sistema de Personalidad Dinámica de Alisha.

Implementa:
1. Semilla de personalidad (gustos propios generados por la IA)
2. Termómetro de afinidad (rangos dinámicos por género)
3. Memoria de opinión (recuerda qué le gustó)
4. Gestos no-verbales (tarareo/baile sin TTS)
5. Sistema de juicio (juzga lo que hace Camila)

Integración: fail-silent, no modifica archivos existentes.
Se conecta a context_monitor.py y tts_engine.py via callbacks.
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
from pathlib import Path
from typing import Optional

from config import DATA_DIR
# ── Archivo de identidad ──────────────────────────────────────────────────────
IDENTITY_FILE = DATA_DIR / "alisha_personalidad.json"
STATE_FILE    = DATA_DIR / "chibi_state.json"

# ── Géneros musicales con rangos de afinidad ─────────────────────────────────
# Cada género tiene: energia [0-1], complejidad [0-1], afinidad_base [-1, 1]
# afinidad_base: 1=ama, 0=neutral, -1=odia
GENEROS_MUSICALES = {
    "synthwave":     {"energia": 0.8, "complejidad": 0.7, "afinidad_base":  1.0},
    "electro":       {"energia": 0.9, "complejidad": 0.6, "afinidad_base":  0.9},
    "lofi":          {"energia": 0.3, "complejidad": 0.4, "afinidad_base":  0.8},
    "jazz":          {"energia": 0.4, "complejidad": 0.9, "afinidad_base":  0.6},
    "rock":          {"energia": 0.8, "complejidad": 0.6, "afinidad_base":  0.5},
    "pop":           {"energia": 0.6, "complejidad": 0.3, "afinidad_base":  0.2},
    "clasica":       {"energia": 0.2, "complejidad": 1.0, "afinidad_base": -0.3},
    "reggaeton":     {"energia": 0.7, "complejidad": 0.2, "afinidad_base": -0.7},
    "cumbia":        {"energia": 0.6, "complejidad": 0.3, "afinidad_base": -0.5},
    "trap":          {"energia": 0.5, "complejidad": 0.2, "afinidad_base": -0.4},
}

# ── Géneros de cine/video ─────────────────────────────────────────────────────
GENEROS_VIDEO = {
    "terror":        {"afinidad_base": -0.8, "emocion": "preocupación"},
    "horror":        {"afinidad_base": -0.8, "emocion": "preocupación"},
    "accion":        {"afinidad_base":  0.6, "emocion": "entusiasmo"},
    "comedia":       {"afinidad_base":  0.9, "emocion": "alegría"},
    "romance":       {"afinidad_base":  0.3, "emocion": "nostalgia"},
    "ciencia_ficcion":{"afinidad_base": 0.8, "emocion": "curiosidad"},
    "documental":    {"afinidad_base":  0.5, "emocion": "curiosidad"},
    "drama":         {"afinidad_base": -0.2, "emocion": "preocupación"},
    "anime":         {"afinidad_base":  0.9, "emocion": "entusiasmo"},
    "tutorial":      {"afinidad_base":  0.4, "emocion": "curiosidad"},
}

# ── Palabras clave para detectar género en título de ventana ─────────────────
KEYWORDS_MUSICA = {
    "synthwave": ["synthwave", "retrowave", "outrun"],
    "electro":   ["electronic", "edm", "techno", "house", "electro"],
    "lofi":      ["lofi", "lo-fi", "chill", "study music", "beats"],
    "jazz":      ["jazz", "blues", "soul", "bossa"],
    "rock":      ["rock", "metal", "punk", "grunge", "indie"],
    "pop":       ["pop", "taylor swift", "bad bunny", "shakira"],
    "clasica":   ["classical", "clásica", "beethoven", "mozart", "bach", "opera"],
    "reggaeton": ["reggaeton", "perreo", "j balvin", "maluma", "daddy yankee"],
    "cumbia":    ["cumbia", "vallenato", "tropical"],
    "trap":      ["trap", "drill", "rap", "hip hop", "hip-hop"],
}

KEYWORDS_VIDEO = {
    "terror":    ["terror", "horror", "scary", "miedo", "susto", "paranormal"],
    "accion":    ["action", "acción", "fight", "battle", "guerra", "explosion"],
    "comedia":   ["comedy", "comedia", "funny", "humor", "laugh"],
    "romance":   ["romance", "love", "amor", "romantic", "novela"],
    "ciencia_ficcion": ["sci-fi", "science fiction", "space", "espacio", "futuro"],
    "documental":["documentary", "documental", "nature", "naturaleza"],
    "drama":     ["drama", "dramatic", "tragedy", "tragedia"],
    "anime":     ["anime", "manga", "naruto", "one piece", "demon slayer"],
    "tutorial":  ["tutorial", "how to", "cómo", "aprende", "curso"],
}


# ══════════════════════════════════════════════════════════════════════════════
# SEMILLA DE PERSONALIDAD
# ══════════════════════════════════════════════════════════════════════════════

class SemillaPersonalidad:
    """
    Genera y persiste los gustos propios de Alisha.
    Primera vez: los genera con Ollama basándose en su estética.
    Siguientes veces: los carga del archivo.
    """

    def __init__(self):
        self._gustos: dict = {}
        self._memoria_opiniones: dict = {}  # título → afinidad aprendida
        self._cargar_o_generar()

    def _cargar_o_generar(self):
        if IDENTITY_FILE.exists():
            try:
                data = json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
                self._gustos = data.get("gustos", {})
                self._memoria_opiniones = data.get("memoria_opiniones", {})
                return
            except Exception:
                pass
        # Primera vez: generar con valores por defecto + ajuste aleatorio
        self._gustos = self._generar_gustos_iniciales()
        self._guardar()
        # Intentar enriquecer con Ollama en background
        threading.Thread(target=self._enriquecer_con_llm, daemon=True).start()

    def _generar_gustos_iniciales(self) -> dict:
        """Gustos iniciales basados en la estética ciberpunk/anime de IceGirl."""
        gustos = {}
        for genero, datos in GENEROS_MUSICALES.items():
            # Variación aleatoria ±0.2 sobre la base
            variacion = random.uniform(-0.2, 0.2)
            gustos[f"musica_{genero}"] = max(-1.0, min(1.0,
                datos["afinidad_base"] + variacion))
        for genero, datos in GENEROS_VIDEO.items():
            variacion = random.uniform(-0.15, 0.15)
            gustos[f"video_{genero}"] = max(-1.0, min(1.0,
                datos["afinidad_base"] + variacion))
        return gustos

    def _enriquecer_con_llm(self):
        """Pide a Ollama que genere gustos más personalizados."""
        try:
            import requests
            prompt = (
                "Sos Alisha, una IA con estética ciberpunk/anime, voz juvenil, "
                "personalidad rioplatense. Generá tus gustos musicales y de cine "
                "en formato JSON. Ejemplo: "
                "{\"musica_synthwave\": 0.9, \"musica_reggaeton\": -0.8, "
                "\"video_anime\": 0.95, \"video_terror\": -0.7}. "
                "Solo el JSON, sin explicación."
            )
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1", "prompt": prompt, "stream": False},
                timeout=15
            )
            if r.status_code == 200:
                texto = r.json().get("response", "")
                # Extraer JSON de la respuesta
                import re
                match = re.search(r'\{[^}]+\}', texto, re.DOTALL)
                if match:
                    nuevos_gustos = json.loads(match.group())
                    # Mezclar con los existentes
                    for k, v in nuevos_gustos.items():
                        if isinstance(v, (int, float)):
                            self._gustos[k] = max(-1.0, min(1.0, float(v)))
                    self._guardar()
                    print("[Identidad] ✓ Gustos enriquecidos con LLM")
        except Exception:
            pass  # fail-silent

    def get_afinidad(self, clave: str) -> float:
        """Retorna afinidad [-1, 1] para una clave de género."""
        # Primero revisar memoria de opiniones (aprendizaje)
        if clave in self._memoria_opiniones:
            return self._memoria_opiniones[clave]
        return self._gustos.get(clave, 0.0)

    def aprender_opinion(self, clave: str, delta: float):
        """
        Actualiza la opinión sobre un género basándose en exposición.
        Si Camila escucha mucho algo que Alisha odia, se adapta gradualmente.
        """
        actual = self.get_afinidad(clave)
        # Cambio muy gradual (0.02 por exposición)
        nuevo = actual + delta * 0.02
        nuevo = max(-1.0, min(1.0, nuevo))
        self._memoria_opiniones[clave] = nuevo
        self._guardar()

    def _guardar(self):
        try:
            IDENTITY_FILE.write_text(json.dumps({
                "gustos": self._gustos,
                "memoria_opiniones": self._memoria_opiniones,
                "version": 1,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# DETECTOR DE CONTEXTO MULTIMEDIA
# ══════════════════════════════════════════════════════════════════════════════

def detectar_genero_musica(titulo_ventana: str) -> Optional[str]:
    """Detecta el género musical del título de ventana activa."""
    titulo = titulo_ventana.lower()
    for genero, keywords in KEYWORDS_MUSICA.items():
        if any(k in titulo for k in keywords):
            return genero
    # Detectar Spotify/YouTube Music genéricamente
    if any(app in titulo for app in ["spotify", "youtube music", "soundcloud", "deezer"]):
        return "pop"  # género neutro por defecto
    return None

def detectar_genero_video(titulo_ventana: str) -> Optional[str]:
    """Detecta el género de video del título de ventana activa."""
    titulo = titulo_ventana.lower()
    for genero, keywords in KEYWORDS_VIDEO.items():
        if any(k in titulo for k in keywords):
            return genero
    return None

def es_app_musica(titulo: str, proceso: str) -> bool:
    t = titulo.lower()
    p = proceso.lower()
    return any(k in t or k in p for k in ["spotify", "music", "soundcloud", "deezer", "youtube music"])

def es_app_video(titulo: str, proceso: str) -> bool:
    t = titulo.lower()
    p = proceso.lower()
    return any(k in t or k in p for k in ["netflix", "youtube", "twitch", "prime", "disney", "hbo", "vlc"])


# ══════════════════════════════════════════════════════════════════════════════
# GESTOS NO-VERBALES (sin TTS)
# ══════════════════════════════════════════════════════════════════════════════

class GestosNoVerbales:
    """
    Dispara animaciones de tarareo/baile en el modelo 2D
    sin usar el sintetizador de voz.
    Escribe directamente en chibi_state.json.
    """

    def _escribir_estado(self, estado: str, mouth: float = 0.0):
        try:
            data = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data["estado"]          = estado
            data["mouth_amplitude"] = round(mouth, 3)
            data["hablando"]        = mouth > 0.01
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def tararear(self, duracion: float = 8.0):
        """Anima la boca con un tarareo suave sin voz."""
        def _loop():
            t = 0.0
            fin = time.time() + duracion
            while time.time() < fin:
                # Onda suave de tarareo (boca casi cerrada)
                amp = abs(math.sin(t * 3.0)) * 0.25 + 0.05
                self._escribir_estado("alegría", mouth=amp)
                t += 0.1
                time.sleep(0.1)
            self._escribir_estado("alegría", mouth=0.0)
        threading.Thread(target=_loop, daemon=True).start()

    def bailar(self, duracion: float = 10.0):
        """Activa expresión de baile — el modelo se mueve con el balanceo."""
        def _loop():
            estados = ["alegría", "entusiasmo", "alegría", "entusiasmo"]
            fin = time.time() + duracion
            i = 0
            while time.time() < fin:
                self._escribir_estado(estados[i % len(estados)], mouth=0.0)
                i += 1
                time.sleep(2.5)
            self._escribir_estado("neutral", mouth=0.0)
        threading.Thread(target=_loop, daemon=True).start()

    def reaccion_susto(self):
        """Reacción de susto ante contenido de terror."""
        def _loop():
            self._escribir_estado("preocupación", mouth=0.3)
            time.sleep(1.0)
            self._escribir_estado("preocupación", mouth=0.0)
            time.sleep(2.0)
            self._escribir_estado("neutral", mouth=0.0)
        threading.Thread(target=_loop, daemon=True).start()

    def ojo_en_blanco(self):
        """Expresión de fastidio."""
        def _loop():
            self._escribir_estado("frustración", mouth=0.0)
            time.sleep(3.0)
            self._escribir_estado("neutral", mouth=0.0)
        threading.Thread(target=_loop, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE JUICIO
# ══════════════════════════════════════════════════════════════════════════════

class SistemaJuicio:
    """
    Evalúa lo que hace Camila y decide si Alisha comenta, tararea, baila o ignora.
    Integra SemillaPersonalidad + GestosNoVerbales + TTS.
    """

    def __init__(self):
        self._semilla   = SemillaPersonalidad()
        self._gestos    = GestosNoVerbales()
        self._ultimo_contexto: str = ""
        self._ultimo_juicio: float = 0.0
        self._cooldown  = 120.0  # mínimo 2 min entre juicios

    def evaluar(self, titulo_ventana: str, proceso: str) -> Optional[str]:
        """
        Evalúa el contexto actual y retorna un comentario de texto (o None).
        También puede disparar gestos no-verbales directamente.
        """
        now = time.time()
        if now - self._ultimo_juicio < self._cooldown:
            return None

        contexto_key = f"{proceso}:{titulo_ventana[:30]}"
        if contexto_key == self._ultimo_contexto:
            return None  # mismo contexto, no repetir

        comentario = None

        # ── Detectar música ───────────────────────────────────────────────────
        if es_app_musica(titulo_ventana, proceso):
            genero = detectar_genero_musica(titulo_ventana)
            if genero:
                afinidad = self._semilla.get_afinidad(f"musica_{genero}")
                # Aprender por exposición
                self._semilla.aprender_opinion(f"musica_{genero}", 0.1)

                if afinidad > 0.6:
                    # Le encanta — tararear
                    self._gestos.tararear(duracion=random.uniform(6, 12))
                    if random.random() < 0.4:  # 40% chance de comentar
                        comentario = self._generar_comentario_musica(genero, afinidad)
                elif afinidad > 0.2:
                    # Le gusta — a veces baila
                    if random.random() < 0.3:
                        self._gestos.bailar(duracion=random.uniform(8, 15))
                elif afinidad < -0.5:
                    # Odia — ojo en blanco + comentario ácido
                    self._gestos.ojo_en_blanco()
                    comentario = self._generar_comentario_musica(genero, afinidad)

        # ── Detectar video ────────────────────────────────────────────────────
        elif es_app_video(titulo_ventana, proceso):
            genero = detectar_genero_video(titulo_ventana)
            if genero:
                afinidad = self._semilla.get_afinidad(f"video_{genero}")
                datos = GENEROS_VIDEO.get(genero, {})

                if genero in ("terror", "horror") and afinidad < -0.3:
                    # Se asusta
                    self._gestos.reaccion_susto()
                    if random.random() < 0.5:
                        comentario = random.choice([
                            "Che, ¿en serio vas a ver eso? Yo me tapo los ojos.",
                            "Uy, eso no me gusta nada. Avisame cuando termine.",
                            "Mirá, yo te aviso si aparece algo feo. Seguí vos.",
                        ])
                elif afinidad > 0.6 and random.random() < 0.3:
                    comentario = self._generar_comentario_video(genero, afinidad)

        if comentario:
            self._ultimo_juicio   = now
            self._ultimo_contexto = contexto_key

        return comentario

    def _generar_comentario_musica(self, genero: str, afinidad: float) -> str:
        if afinidad > 0.6:
            opciones = [
                f"Uh, {genero}. Esto sí me gusta. Seguí poniendo.",
                f"Buena elección con el {genero}. Así se trabaja.",
                f"Che, esto está buenísimo. No lo cambies.",
            ]
        elif afinidad < -0.5:
            opciones = [
                f"¿{genero}? Camila, por favor. Tenés mejor gusto que eso.",
                f"Esto es {genero}. No me hagas esto. Poné otra cosa.",
                f"Che, con todo el respeto, esto me duele los oídos.",
            ]
        else:
            return ""
        return random.choice(opciones)

    def _generar_comentario_video(self, genero: str, afinidad: float) -> str:
        if afinidad > 0.6:
            opciones = [
                f"Buena elección con el {genero}. Me quedo a ver.",
                f"Esto sí vale la pena. Buen gusto.",
            ]
        else:
            return ""
        return random.choice(opciones)


# ══════════════════════════════════════════════════════════════════════════════
# MONITOR DE IDENTIDAD (loop principal)
# ══════════════════════════════════════════════════════════════════════════════

class MonitorIdentidad:
    """
    Loop daemon que monitorea el contexto y dispara reacciones de identidad.
    Se integra con context_monitor.py leyendo la ventana activa.
    """

    def __init__(self, callback_voz=None):
        """
        callback_voz: función que recibe texto y lo habla (tts_engine.speak).
        Si es None, solo hace gestos sin voz.
        """
        self._juicio   = SistemaJuicio()
        self._callback = callback_voz
        self._running  = False
        self._thread   = None

    def iniciar(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Identidad] ✓ Monitor de personalidad dinámica iniciado")

    def detener(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                titulo, proceso = self._obtener_ventana()
                if titulo:
                    comentario = self._juicio.evaluar(titulo, proceso)
                    if comentario and self._callback:
                        threading.Thread(
                            target=self._callback,
                            args=(comentario,),
                            daemon=True
                        ).start()
            except Exception:
                pass
            time.sleep(15)  # revisar cada 15 segundos

    def _obtener_ventana(self) -> tuple[str, str]:
        try:
            import ctypes, ctypes.wintypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            buf  = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            titulo = buf.value

            proceso = ""
            try:
                import win32gui, win32process, psutil
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proceso = psutil.Process(pid).name()
            except Exception:
                pass

            return titulo, proceso
        except Exception:
            return "", ""


# ══════════════════════════════════════════════════════════════════════════════
# API pública
# ══════════════════════════════════════════════════════════════════════════════

_monitor: Optional[MonitorIdentidad] = None

def iniciar_identidad(callback_voz=None) -> MonitorIdentidad:
    """Inicia el sistema de personalidad dinámica."""
    global _monitor
    if _monitor is None:
        _monitor = MonitorIdentidad(callback_voz=callback_voz)
        _monitor.iniciar()
    return _monitor

def get_monitor() -> Optional[MonitorIdentidad]:
    return _monitor
