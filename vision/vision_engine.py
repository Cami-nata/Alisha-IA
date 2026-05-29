"""
vision_engine.py — VisionEngine de Alisha (Propiedad 7).

Le da "ojos" a Alisha. Construido sobre screen_vision.py existente.

Características:
  - Scan pasivo cada 10-15s (no satura CPU de la ASUS F15)
  - OCR rápido con PIL + pytesseract (escala de grises, resize)
  - Detección de apps de distracción vs meta activa → Sarcasm Score 0.8
  - "Mirada de reojo": mueve ParamEyeBallX/Y hacia el centro con desaprobación
  - Integración con SmartRouter: "¿qué opinás de lo que estoy haciendo?"
    toma captura en ese instante y responde basándose en lo que ve
  - Context buffer: guarda lo que "ve" para respuestas orgánicas
    (sin decir "veo que tenés X abierto")

Integración:
  - Escribe en chibi_state.json para mover los ojos del Live2D
  - Se conecta con brain.py (SmartRouter + SarcasmScoreEngine)
  - Usa screen_vision.py para captura y OCR base
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

# ── Importar módulos existentes ────────────────────────────────────────────────
from vision.screen_vision import (
    capturar_ventana_rapida,
    obtener_ventana_activa_info,
    detectar_errores_en_pantalla,
    _WIN32_OK,
    _MSS_OK,
    _OCR_OK,
)

from config.settings import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# ── Dependencias opcionales ────────────────────────────────────────────────────
try:
    from PIL import Image as _PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import pytesseract as _tesseract
    # Configurar ruta del binario de Tesseract — búsqueda dinámica
    import shutil as _shutil_tess
    import os as _os_tess
    _tess_en_path = _shutil_tess.which("tesseract")
    if _tess_en_path:
        _tesseract.pytesseract.tesseract_cmd = _tess_en_path
    else:
        _TESS_PATHS = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            _os_tess.path.join(_os_tess.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
            _os_tess.path.join(_os_tess.environ.get("APPDATA", ""), r"Tesseract-OCR\tesseract.exe"),
        ]
        for _tp in _TESS_PATHS:
            if _os_tess.path.exists(_tp):
                _tesseract.pytesseract.tesseract_cmd = _tp
                break
    _TESS_OK = True
except ImportError:
    _TESS_OK = False

try:
    import psutil as _psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORÍAS DE APPS
# ══════════════════════════════════════════════════════════════════════════════

# Apps de distracción (activan "mirada de reojo")
_APPS_DISTRACCION = {
    "instagram", "youtube", "tiktok", "twitter", "x.com", "twitch",
    "netflix", "disney", "hbo", "prime video", "spotify",
    "steam", "epic games", "discord", "facebook", "reddit",
    "whatsapp web", "telegram web",
}

# Apps de trabajo/estudio (Alisha aprueba)
_APPS_TRABAJO = {
    "visual studio code", "vscode", "code", "kiro",
    "pycharm", "intellij", "sublime text", "notepad++",
    "word", "excel", "powerpoint", "libreoffice",
    "figma", "photoshop", "illustrator", "canva",
    "github", "gitlab", "terminal", "powershell", "cmd",
    "jupyter", "anaconda", "spyder",
}

# Palabras clave de error en pantalla (para detección rápida sin OCR completo)
_ERROR_VISUAL_KW = {
    "traceback", "error:", "exception", "syntaxerror", "failed",
    "fatal", "critical", "undefined", "cannot", "not found",
    "404", "500", "crash", "segfault",
}

# Palabras clave de contenido técnico
_TECH_KW = {
    "def ", "class ", "import ", "function", "const ", "var ",
    "return", "if (", "for (", "while (", "async", "await",
    "SELECT", "INSERT", "UPDATE", "FROM", "WHERE",
}

# ── Detección de rol según app activa ────────────────────────────────────────
_ROL_MAP = {
    "senior_dev": {
        "apps": {"visual studio code", "vscode", "code", "kiro", "pycharm",
                 "intellij", "sublime text", "notepad++", "github", "terminal",
                 "powershell", "cmd", "jupyter"},
        "descripcion": "Senior Developer",
        "estilo": "técnico y directo, como pair programmer",
    },
    "directora_creativa": {
        "apps": {"figma", "photoshop", "illustrator", "canva", "adobe",
                 "inkscape", "gimp", "premiere", "after effects"},
        "descripcion": "Directora Creativa",
        "estilo": "visual y estético, con opiniones sobre diseño",
    },
    "analista_datos": {
        "apps": {"excel", "sheets", "tableau", "power bi", "spyder",
                 "anaconda", "jupyter", "pandas", "matplotlib"},
        "descripcion": "Analista de Datos",
        "estilo": "analítico y preciso, con foco en números",
    },
    "escritora": {
        "apps": {"word", "docs", "libreoffice", "notion", "obsidian",
                 "typora", "markdown"},
        "descripcion": "Editora y Escritora",
        "estilo": "narrativo y cuidadoso con las palabras",
    },
}

def detectar_rol(titulo_ventana: str) -> dict:
    """Detecta el rol que debe adoptar Alisha según la app activa."""
    t = titulo_ventana.lower()
    for rol_id, datos in _ROL_MAP.items():
        if any(app in t for app in datos["apps"]):
            return {"rol": rol_id, **datos}
    return {"rol": "companion", "descripcion": "Compañera", "estilo": "casual y amigable"}


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class VisionSnapshot:
    """Instantánea de lo que Alisha "ve" en un momento dado."""
    timestamp:       float
    window_title:    str
    app_category:    str        # "trabajo" | "distraccion" | "neutro"
    ocr_text:        str        # texto extraído (máx 500 chars)
    errors_detected: List[str]  # errores visuales encontrados
    is_distraction:  bool
    is_work:         bool
    cpu_usage:       float


@dataclass
class VisionContext:
    """Contexto acumulado de visión para respuestas orgánicas."""
    snapshots:       List[VisionSnapshot] = field(default_factory=list)
    active_goal:     str = ""             # meta activa del usuario
    distraction_count: int = 0
    last_distraction_app: str = ""

    def get_summary(self) -> str:
        """Genera resumen orgánico SIN mencionar que 'veo X abierto'."""
        if not self.snapshots:
            return ""
        last = self.snapshots[-1]
        return (
            f"app_categoria={last.app_category}, "
            f"titulo='{last.window_title[:40]}', "
            f"errores={last.errors_detected}, "
            f"distracciones_sesion={self.distraction_count}"
        )

    def get_organic_context(self) -> str:
        """
        Contexto para el system prompt — describe la situación sin
        revelar que Alisha está "viendo la pantalla".
        """
        if not self.snapshots:
            return ""
        last = self.snapshots[-1]
        parts = []

        if last.is_distraction and self.active_goal:
            parts.append(
                f"Camila tiene una meta activa ('{self.active_goal}') "
                f"pero parece estar en algo que no es eso."
            )
        elif last.is_work:
            parts.append("Camila está trabajando en algo técnico.")

        if last.errors_detected:
            parts.append(
                f"Hay señales de problemas técnicos en lo que está haciendo: "
                f"{', '.join(last.errors_detected[:2])}."
            )

        if self.distraction_count >= 3:
            parts.append(
                f"Ya van {self.distraction_count} veces que se distrae en esta sesión."
            )

        return " ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# OCR PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class OCRPipeline:
    """
    Pipeline OCR liviano: captura → escala de grises → resize → texto.
    Diseñado para no saturar la CPU de la ASUS F15.
    """

    MAX_WIDTH  = 960   # ancho máximo para OCR (balance velocidad/precisión)
    JPEG_QUAL  = 55    # calidad JPEG para compresión rápida

    def extract_text(self, img_bytes: bytes) -> str:
        """Extrae texto de bytes de imagen JPEG."""
        if not img_bytes or not _PIL_OK:
            return ""
        try:
            img = _PILImage.open(io.BytesIO(img_bytes))

            # Escala de grises (más rápido para OCR)
            img_gray = img.convert("L")

            # Resize si es muy grande
            w, h = img_gray.size
            if w > self.MAX_WIDTH:
                ratio = self.MAX_WIDTH / w
                img_gray = img_gray.resize(
                    (self.MAX_WIDTH, int(h * ratio)),
                    _PILImage.LANCZOS
                )

            if _TESS_OK:
                # OCR con tesseract — config rápida
                texto = _tesseract.image_to_string(
                    img_gray,
                    lang="eng+spa",
                    config="--psm 6 --oem 1 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:!?()[]{}@#$%&*-_+=/<>'\""
                )
                return texto[:600].strip()
            else:
                # Sin tesseract: solo analizar título de ventana
                return ""
        except Exception:
            return ""

    def detect_errors_in_text(self, text: str) -> List[str]:
        """Detecta palabras clave de error en el texto OCR."""
        text_lower = text.lower()
        found = []
        for kw in _ERROR_VISUAL_KW:
            if kw in text_lower:
                found.append(kw)
        return found[:3]  # máximo 3 para no saturar

    def detect_tech_content(self, text: str) -> bool:
        """Detecta si hay contenido técnico/código en pantalla."""
        return any(kw in text for kw in _TECH_KW)


# ══════════════════════════════════════════════════════════════════════════════
# LIVE2D GAZE CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class GazeController:
    """
    Controla la mirada del modelo Live2D según lo que Alisha "ve".
    Escribe directamente en chibi_state.json.
    """

    def side_eye_disapproval(self) -> None:
        """
        'Mirada de reojo' con desaprobación.
        ParamEyeBallX hacia el centro (0.0), cejas fruncidas.
        """
        self._write_gaze(
            estado="frustración",
            eye_x=0.0,    # mirar al centro
            eye_y=0.1,    # levemente hacia arriba
            hablando=False,
        )
        print("[GazeController] 👀 Mirada de reojo — desaprobación")

    def look_at_screen(self) -> None:
        """Mirada hacia la pantalla (análisis activo)."""
        self._write_gaze(
            estado="curiosidad",
            eye_x=random.uniform(-0.3, 0.3),
            eye_y=random.uniform(-0.2, 0.2),
            hablando=False,
        )

    def look_away_distracted(self) -> None:
        """Mirada distraída — Alisha mira hacia otro lado."""
        self._write_gaze(
            estado="neutro",
            eye_x=random.uniform(0.5, 0.9),
            eye_y=random.uniform(-0.3, 0.3),
            hablando=False,
        )

    def return_to_normal(self) -> None:
        """Vuelve a la mirada normal."""
        self._write_gaze(
            estado="neutral",
            eye_x=0.0,
            eye_y=0.0,
            hablando=False,
        )

    @staticmethod
    def _write_gaze(estado: str, eye_x: float, eye_y: float,
                    hablando: bool) -> None:
        try:
            # Leer estado actual para no sobreescribir todo
            current = {}
            if STATE_FILE.exists():
                try:
                    current = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass

            current.update({
                "estado":        estado,
                "hablando":      hablando,
                "gaze_x":        round(eye_x, 3),
                "gaze_y":        round(eye_y, 3),
                "gaze_override": True,   # señal para cabina_virtual
            })
            STATE_FILE.write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# VISION ENGINE — núcleo principal
# ══════════════════════════════════════════════════════════════════════════════

class VisionEngine:
    """
    Motor de visión pasiva de Alisha.

    - Scan cada 10-15s (configurable)
    - No captura si CPU > 65%
    - Detecta distracciones y activa "mirada de reojo"
    - Integra con SmartRouter para respuestas contextuales
    - Mantiene context buffer orgánico
    """

    SCAN_INTERVAL_MIN = 15.0   # segundos mínimos entre scans (spec: 10-15s)
    SCAN_INTERVAL_MAX = 25.0   # segundos máximos entre scans
    CPU_LIMIT         = 50.0   # % CPU máximo para capturar (subido de 65%)
    MAX_SNAPSHOTS     = 10     # historial máximo (reducido de 20)

    def __init__(self):
        self._ocr      = OCRPipeline()
        self._gaze     = GazeController()
        self._context  = VisionContext()
        self._running  = False
        self._thread: Optional[threading.Thread] = None
        self._lock     = threading.Lock()
        self._callbacks: List[Callable[[VisionSnapshot], None]] = []
        self._last_snapshot: Optional[VisionSnapshot] = None

    # ── API pública ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicia el scan pasivo en hilo daemon."""
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        print(f"[VisionEngine] ✓ Iniciado (scan cada {self.SCAN_INTERVAL_MIN}-{self.SCAN_INTERVAL_MAX}s)")

    def stop(self) -> None:
        self._running = False

    def set_active_goal(self, goal: str) -> None:
        """Registra la meta activa del usuario para detectar distracciones."""
        with self._lock:
            self._context.active_goal = goal
        print(f"[VisionEngine] 🎯 Meta activa: '{goal}'")

    def on_snapshot(self, callback: Callable[[VisionSnapshot], None]) -> None:
        """Registra callback que se llama en cada snapshot."""
        self._callbacks.append(callback)

    def capture_now(self) -> Optional[VisionSnapshot]:
        """Captura inmediata — para cuando el usuario pregunta '¿qué opinás?'"""
        return self._take_snapshot(force=True)

    def get_context(self) -> VisionContext:
        return self._context

    def get_last_snapshot(self) -> Optional[VisionSnapshot]:
        return self._last_snapshot

    def get_organic_response_context(self) -> str:
        """
        Retorna el contexto orgánico para incluir en el system prompt.
        Describe la situación sin revelar que Alisha "ve la pantalla".
        """
        return self._context.get_organic_context()

    # ── Loop de scan pasivo ────────────────────────────────────────────────────

    def _scan_loop(self) -> None:
        while self._running:
            # Intervalo aleatorio para naturalidad
            interval = random.uniform(self.SCAN_INTERVAL_MIN, self.SCAN_INTERVAL_MAX)
            time.sleep(interval)

            if not self._running:
                break

            snapshot = self._take_snapshot()
            if snapshot:
                self._process_snapshot(snapshot)

    def _take_snapshot(self, force: bool = False) -> Optional[VisionSnapshot]:
        """Toma una instantánea de la pantalla actual."""
        # Verificar CPU
        cpu = 0.0
        if _PSUTIL_OK:
            try:
                cpu = _psutil.cpu_percent(interval=0.1)
                if not force and cpu > self.CPU_LIMIT:
                    return None
            except Exception:
                pass

        # Obtener info de ventana activa (sin captura de imagen)
        win_info = obtener_ventana_activa_info()
        titulo   = win_info.get("titulo", "Desconocido")

        # Categorizar app por título (rápido, sin imagen)
        app_cat, is_distraction, is_work = self._categorize_window(titulo)

        # Captura de imagen solo si es necesario (distracción o trabajo activo)
        ocr_text = ""
        errors   = []

        if is_distraction or is_work or force:
            img_bytes, _ = capturar_ventana_rapida(max_width=960)
            if img_bytes:
                ocr_text = self._ocr.extract_text(img_bytes)
                errors   = self._ocr.detect_errors_in_text(ocr_text)
                del img_bytes   # liberar memoria explícitamente

        snapshot = VisionSnapshot(
            timestamp=time.time(),
            window_title=titulo,
            app_category=app_cat,
            ocr_text=ocr_text,
            errors_detected=errors,
            is_distraction=is_distraction,
            is_work=is_work,
            cpu_usage=cpu,
        )

        with self._lock:
            self._last_snapshot = snapshot
            self._context.snapshots.append(snapshot)
            if len(self._context.snapshots) > self.MAX_SNAPSHOTS:
                self._context.snapshots = self._context.snapshots[-self.MAX_SNAPSHOTS:]

        return snapshot

    def _process_snapshot(self, snapshot: VisionSnapshot) -> None:
        """Procesa el snapshot y dispara reacciones si corresponde."""

        # ── Detección de distracción con meta activa ──────────────────────────
        if snapshot.is_distraction and self._context.active_goal:
            with self._lock:
                self._context.distraction_count += 1
                self._context.last_distraction_app = snapshot.window_title

            print(
                f"[VisionEngine] 😒 Distracción detectada: '{snapshot.window_title}' "
                f"(meta: '{self._context.active_goal}', "
                f"count={self._context.distraction_count})"
            )

            self._gaze.side_eye_disapproval()
            self._trigger_distraction_sarcasm(snapshot)
            self._generar_comentario_sarcasmo(snapshot)
            threading.Timer(3.0, self._gaze.return_to_normal).start()

        # ── Detección de errores en pantalla ─────────────────────────────────
        elif snapshot.errors_detected:
            print(f"[VisionEngine] ⚠ Errores en pantalla: {snapshot.errors_detected}")
            self._gaze.look_at_screen()
            # Comentario proactivo sobre el error
            self._generar_comentario_error(snapshot)
            threading.Timer(2.0, self._gaze.return_to_normal).start()

        # ── Trabajo activo — mirada de análisis ──────────────────────────────
        elif snapshot.is_work:
            self._gaze.look_at_screen()
            # Comentario positivo ocasional cuando hay contenido técnico (FASE 13)
            if snapshot.ocr_text and self._ocr.detect_tech_content(snapshot.ocr_text):
                import random as _rnd
                if _rnd.random() < 0.15:   # 15% de chance para no ser invasiva
                    self._generar_comentario_positivo(snapshot)
            threading.Timer(1.5, self._gaze.return_to_normal).start()

        # Notificar callbacks
        for cb in self._callbacks:
            try:
                cb(snapshot)
            except Exception:
                pass

    def _generar_comentario_error(self, snapshot: VisionSnapshot) -> None:
        """Genera comentario proactivo cuando detecta errores en pantalla.
        Usa Gemini Vision nativo si está disponible para describir la imagen real.
        """
        def _hablar():
            try:
                # Throttle: no comentar errores más de 1 vez cada 3 minutos
                now = time.time()
                if hasattr(self, '_ultimo_comentario_error'):
                    if now - self._ultimo_comentario_error < 180:
                        return
                self._ultimo_comentario_error = now

                from brain import get_brain
                brain = get_brain()
                errores = ", ".join(snapshot.errors_detected[:2])

                # Intentar descripción nativa con Gemini Vision (imagen real, sin OCR)
                descripcion_visual = ""
                try:
                    from gemini_vision import GeminiVision as _GV
                    _gv = _GV()
                    descripcion_visual = _gv.capture_and_analyze() or ""
                except Exception:
                    pass

                if descripcion_visual:
                    prompt = (
                        f"Ves esto en la pantalla de Camila: '{descripcion_visual}'. "
                        f"Hay señales de un problema técnico ({errores}). "
                        f"Hacé un comentario corto y útil en voseo rioplatense, "
                        f"máx 20 palabras, sin decir que ves la pantalla. "
                        f"Ofrecé ayuda de forma natural."
                    )
                else:
                    prompt = (
                        f"Detectás señales de un problema técnico ({errores}) "
                        f"en lo que está haciendo Camila. "
                        f"Hacé un comentario corto y útil en voseo rioplatense, "
                        f"máx 20 palabras, sin mencionar que ves la pantalla. "
                        f"Ofrecé ayuda de forma natural."
                    )

                response = brain.process(prompt)
                comentario = response.content
                if not comentario:
                    return

                from audio_visual_sync import get_audio_visual_sync
                avs = get_audio_visual_sync()
                avs.speak(
                    comentario,
                    sarcasm_score=0.1,
                    emotional_state="curiosidad",
                    async_mode=True,
                )
                # Guardar en chat web
                try:
                    from web_app import socketio
                    socketio.emit("respuesta", {
                        "texto": comentario,
                        "estado_emocional": "curiosidad",
                        "fuente": "vision",
                    })
                except Exception:
                    pass
                print(f"[VisionEngine] 🗣 Error detectado: {comentario}")
            except Exception as e:
                print(f"[VisionEngine] Error comentario error: {e}")

        threading.Thread(target=_hablar, daemon=True).start()

    def _generar_comentario_sarcasmo(self, snapshot: VisionSnapshot) -> None:
        """Genera comentario sarcástico con voz sobre la distracción detectada."""
        def _hablar():
            try:
                from brain import get_brain
                brain = get_brain()
                count = self._context.distraction_count
                goal  = self._context.active_goal

                if count == 1:
                    prompt = (
                        f"Camila tiene pendiente '{goal}' pero parece estar en otra cosa. "
                        f"Hacé un comentario sarcástico corto (máx 15 palabras) en voseo rioplatense, "
                        f"sin mencionar que ves la pantalla. Solo 1 oración."
                    )
                elif count <= 3:
                    prompt = (
                        f"Camila sigue distrayéndose (van {count} veces) con '{goal}' pendiente. "
                        f"Comentario irónico corto en voseo, máx 15 palabras."
                    )
                else:
                    prompt = (
                        f"Camila lleva {count} distracciones con '{goal}' sin terminar. "
                        f"Comentario muy sarcástico en voseo, máx 15 palabras."
                    )

                response = brain.process(prompt)
                comentario = response.content

                from audio_visual_sync import get_audio_visual_sync
                avs = get_audio_visual_sync()
                avs.speak(
                    comentario,
                    sarcasm_score=min(0.9, 0.5 + count * 0.1),
                    emotional_state="frustración",
                    async_mode=True,
                )
                print(f"[VisionEngine] 🗣 {comentario}")
            except Exception as e:
                print(f"[VisionEngine] Error comentario: {e}")

        threading.Thread(target=_hablar, daemon=True).start()

    def _generar_comentario_positivo(self, snapshot: VisionSnapshot) -> None:
        """Genera comentario de apoyo cuando detecta trabajo técnico activo."""
        def _hablar():
            try:
                # Throttle: no comentar positivo más de 1 vez cada 5 minutos
                now = time.time()
                if hasattr(self, '_ultimo_comentario_positivo'):
                    if now - self._ultimo_comentario_positivo < 300:
                        return
                self._ultimo_comentario_positivo = now

                from brain import get_brain
                brain = get_brain()

                # Enriquecer con descripción visual nativa si está disponible
                descripcion_visual = ""
                try:
                    from gemini_vision import GeminiVision as _GV
                    descripcion_visual = _GV().capture_and_analyze() or ""
                except Exception:
                    pass

                if descripcion_visual:
                    prompt = (
                        f"Ves que Camila está trabajando: '{descripcion_visual}'. "
                        f"Hacé un comentario de apoyo muy corto (máx 10 palabras) "
                        f"en voseo rioplatense, sin mencionar que ves la pantalla."
                    )
                else:
                    prompt = (
                        f"Camila está trabajando en algo técnico en '{snapshot.window_title[:40]}'. "
                        f"Hacé un comentario de apoyo muy corto (máx 10 palabras) "
                        f"en voseo rioplatense, sin mencionar que ves la pantalla."
                    )

                response = brain.process(prompt)
                comentario = response.content
                if not comentario:
                    return

                from audio_visual_sync import get_audio_visual_sync
                avs = get_audio_visual_sync()
                avs.speak(
                    comentario,
                    sarcasm_score=0.0,
                    emotional_state="alegría",
                    async_mode=True,
                )
                try:
                    from web_app import socketio
                    socketio.emit("respuesta", {
                        "texto": comentario,
                        "estado_emocional": "alegría",
                        "fuente": "vision",
                    })
                except Exception:
                    pass
                print(f"[VisionEngine] 💪 Apoyo: {comentario}")
            except Exception as e:
                print(f"[VisionEngine] Error comentario positivo: {e}")

        threading.Thread(target=_hablar, daemon=True).start()

    def _categorize_window(self, titulo: str) -> tuple[str, bool, bool]:
        """
        Categoriza la ventana activa.
        Retorna (categoria, is_distraction, is_work).
        """
        t = titulo.lower()

        # Ignorar ventanas del sistema que no son relevantes
        _IGNORAR = {"papelera", "recycle bin", "escritorio", "desktop",
                    "taskbar", "barra de tareas", "inicio", "start"}
        if any(ig in t for ig in _IGNORAR):
            return "neutro", False, False

        for app in _APPS_DISTRACCION:
            if app in t:
                return "distraccion", True, False

        for app in _APPS_TRABAJO:
            if app in t:
                return "trabajo", False, True

        return "neutro", False, False

    def _trigger_distraction_sarcasm(self, snapshot: VisionSnapshot) -> None:
        """
        Dispara Sarcasm Score 0.8 cuando detecta distracción con meta activa.
        Escribe en chibi_state.json para que la web app lo lea.
        """
        try:
            current = {}
            if STATE_FILE.exists():
                current = json.loads(STATE_FILE.read_text(encoding="utf-8"))

            current["vision_distraction"] = {
                "detected":    True,
                "app":         snapshot.window_title[:50],
                "goal":        self._context.active_goal,
                "sarcasm":     0.8,
                "timestamp":   snapshot.timestamp,
                "count":       self._context.distraction_count,
            }
            STATE_FILE.write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    # ── Integración con SmartRouter ────────────────────────────────────────────

    def analyze_for_query(self, query: str) -> str:
        """
        Cuando el usuario pregunta '¿qué opinás de lo que estoy haciendo?',
        toma captura inmediata y genera contexto para el brain.
        """
        snapshot = self.capture_now()
        if not snapshot:
            return ""

        parts = []

        # Contexto de app
        if snapshot.is_distraction:
            parts.append(
                f"Camila está en algo que no parece ser trabajo "
                f"('{snapshot.window_title[:40]}')."
            )
            if self._context.active_goal:
                parts.append(
                    f"Tiene pendiente: '{self._context.active_goal}'."
                )
        elif snapshot.is_work:
            parts.append(
                f"Camila está trabajando en '{snapshot.window_title[:40]}'."
            )

        # Errores detectados
        if snapshot.errors_detected:
            parts.append(
                f"Hay errores visibles: {', '.join(snapshot.errors_detected)}."
            )

        # Texto OCR relevante
        if snapshot.ocr_text and len(snapshot.ocr_text) > 30:
            # Solo primeras líneas relevantes
            lines = [l.strip() for l in snapshot.ocr_text.split('\n') if l.strip()][:3]
            if lines:
                parts.append(f"Contexto visible: {' | '.join(lines[:2])}")

        return " ".join(parts) if parts else f"Ventana activa: '{snapshot.window_title}'"


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRACIÓN CON BRAIN — patch del SmartRouter
# ══════════════════════════════════════════════════════════════════════════════

# Palabras clave que activan captura de pantalla inmediata
_VISION_TRIGGER_KW = {
    "qué opinás de lo que estoy haciendo",
    "qué ves",
    "qué estoy haciendo",
    "mirá mi pantalla",
    "qué tengo abierto",
    "qué estoy escribiendo",
    "cómo va lo que hago",
    "qué te parece lo que hago",
}

def should_capture_for_query(query: str) -> bool:
    """Detecta si la consulta requiere captura de pantalla."""
    q = query.lower()
    return any(kw in q for kw in _VISION_TRIGGER_KW)


def enrich_query_with_vision(query: str, engine: "VisionEngine") -> str:
    """
    Enriquece la consulta con contexto visual si corresponde.
    Retorna la consulta original + contexto de visión.
    """
    if not should_capture_for_query(query):
        # Igual agregar contexto orgánico si hay algo relevante
        organic = engine.get_organic_response_context()
        if organic:
            return f"{query}\n\n[Contexto de situación: {organic}]"
        return query

    # Captura inmediata
    vision_context = engine.analyze_for_query(query)
    if vision_context:
        return f"{query}\n\n[Lo que está pasando ahora: {vision_context}]"
    return query


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_vision_engine: Optional[VisionEngine] = None

def get_vision_engine() -> VisionEngine:
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
    return _vision_engine

