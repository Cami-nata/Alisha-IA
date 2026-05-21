"""
gemini_vision.py — Análisis semántico silencioso de capturas de pantalla.

Toma capturas periódicas y las analiza con Gemini para entender qué está
haciendo el usuario. Opera en modo completamente silencioso: sin logs visibles,
sin voz, sin modificar el flujo de chat.

Principio fail-silent: toda excepción se captura y registra internamente;
nunca se propaga al sistema principal.
"""
from __future__ import annotations

import os
import random
import threading
import time
from typing import Optional

# ── Dependencias opcionales ────────────────────────────────────────────────────
try:
    from google import genai as _genai
    from google.genai import types as _genai_types
    _GEMINI_SDK_OK = True
except ImportError:
    _GEMINI_SDK_OK = False

try:
    import psutil as _psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

try:
    from screen_vision import capturar_ventana_rapida as _capturar_ventana_rapida
    _SCREEN_VISION_OK = True
except Exception:
    _SCREEN_VISION_OK = False

# ── Constantes ─────────────────────────────────────────────────────────────────
_BUFFER_CAPACITY = 5
_FRESHNESS_SECONDS = 30.0
_CAPTURE_INTERVAL_MIN = 20.0   # Mínimo 20s entre capturas (anti-CAPTCHA)
_CAPTURE_INTERVAL_MAX = 35.0   # Máximo 35s entre capturas
_CPU_PAUSE_THRESHOLD = 70.0
_CPU_RESUME_THRESHOLD = 60.0
_API_TIMEOUT_SECONDS = 15.0
_API_RETRY_WAIT_SECONDS = 60.0
_MAX_CALLS_PER_MINUTE = 3      # Límite estricto: máx 3 llamadas por minuto
_GEMINI_PROMPT = (
    "Describí brevemente en 1-2 oraciones qué está haciendo esta persona en su "
    "computadora. Sé específico sobre la app y la tarea visible."
)
_GEMINI_MODEL = "gemini-2.0-flash"


class GeminiVision:
    """
    Análisis semántico silencioso de capturas de pantalla usando Gemini.

    Mantiene un buffer circular de las últimas 5 descripciones y provee
    la descripción más reciente si tiene menos de 30 segundos de antigüedad.
    """

    def __init__(self) -> None:
        # Buffer circular: lista de dicts {"description": str, "timestamp": float}
        self._buffer: list[dict] = []
        self._buffer_lock = threading.Lock()

        # Control del hilo de captura
        self._running = False
        self._hilo: Optional[threading.Thread] = None

        # Cliente Gemini (inicializado bajo demanda)
        self._client = None
        self._client_lock = threading.Lock()

        # Control de quota — si Gemini falla por 429, usar fallback local
        self._gemini_quota_ok = True
        self._gemini_quota_reset = 0.0  # timestamp para reintentar Gemini

        # Rate limiting — registro de timestamps de llamadas recientes
        self._api_call_timestamps: list[float] = []
        self._rate_limit_lock = threading.Lock()

    # ── Rate limiting ──────────────────────────────────────────────────────────

    def _check_rate_limit(self) -> bool:
        """
        Verifica si se puede hacer una llamada a la API sin superar el límite.
        Retorna True si está permitido, False si hay que esperar.
        """
        with self._rate_limit_lock:
            now = time.time()
            # Limpiar timestamps de más de 60 segundos
            self._api_call_timestamps = [
                ts for ts in self._api_call_timestamps if now - ts < 60.0
            ]
            if len(self._api_call_timestamps) >= _MAX_CALLS_PER_MINUTE:
                return False
            self._api_call_timestamps.append(now)
            return True

    # ── Cliente Gemini ─────────────────────────────────────────────────────────

    def _get_client(self):
        """Retorna el cliente Gemini, inicializándolo si es necesario."""
        with self._client_lock:
            if self._client is not None:
                return self._client

            if not _GEMINI_SDK_OK:
                return None

            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                return None

            try:
                self._client = _genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[GeminiVision] Error al inicializar cliente: {e}")
                self._client = None

            return self._client

    # ── Análisis de imagen ─────────────────────────────────────────────────────

    def _analyze(self, img_bytes: bytes) -> Optional[str]:
        """
        Analiza la pantalla. Intenta Gemini primero; si falla por quota (429),
        usa fallback local: OCR + título de ventana + Groq para descripción.
        """
        if not img_bytes:
            return None

        # Verificar rate limit antes de llamar a la API
        if not self._check_rate_limit():
            # Límite alcanzado — usar análisis local sin API
            return self._analyze_local()

        # Intento 1: Gemini (si está disponible y no tiene quota agotada)
        if self._gemini_quota_ok:
            try:
                client = self._get_client()
                if client is not None:
                    result_holder: list[Optional[str]] = [None]
                    error_holder: list[Optional[Exception]] = [None]

                    def _call_api():
                        try:
                            response = client.models.generate_content(
                                model=_GEMINI_MODEL,
                                contents=[
                                    _genai_types.Part.from_bytes(
                                        data=img_bytes,
                                        mime_type="image/jpeg",
                                    ),
                                    _GEMINI_PROMPT,
                                ],
                            )
                            result_holder[0] = response.text
                        except Exception as exc:
                            error_holder[0] = exc

                    api_thread = threading.Thread(target=_call_api, daemon=True)
                    api_thread.start()
                    api_thread.join(timeout=_API_TIMEOUT_SECONDS)

                    if not api_thread.is_alive() and error_holder[0] is None:
                        return result_holder[0]

                    # Verificar si es error de quota
                    err = error_holder[0]
                    if err and ("429" in str(err) or "RESOURCE_EXHAUSTED" in str(err) or "quota" in str(err).lower()):
                        self._gemini_quota_ok = False
                        self._gemini_quota_reset = time.time() + 3600  # reintentar en 1 hora
                        print("[GeminiVision] Quota agotada — usando fallback local")
            except Exception:
                pass

        # Fallback local: título de ventana + OCR básico + Groq
        return self._analyze_local()

    def _analyze_local(self) -> Optional[str]:
        """Análisis local sin API de imágenes — usa título de ventana y Groq."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            buf  = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            titulo = buf.value.strip()

            if not titulo or titulo.lower() in ("", "escritorio", "desktop"):
                return None

            # Usar Groq para generar descripción basada en el título
            try:
                from brain import get_brain
                brain = get_brain()
                resp = brain.process(
                    f"En 1 oración corta, describí qué está haciendo Cami basándote "
                    f"en que tiene abierto: '{titulo}'. Sin mencionar que ves la pantalla."
                )
                if resp and resp.content:
                    return resp.content.strip()
            except Exception:
                pass

            # Fallback mínimo: retornar el título como descripción
            return f"Cami está usando: {titulo}"
        except Exception:
            return None

    # ── Buffer circular ────────────────────────────────────────────────────────

    def _add_to_buffer(self, description: str) -> None:
        """Agrega una descripción al buffer circular (capacidad 5)."""
        entry = {"description": description, "timestamp": time.time()}
        with self._buffer_lock:
            self._buffer.append(entry)
            # Mantener solo los últimos _BUFFER_CAPACITY elementos
            if len(self._buffer) > _BUFFER_CAPACITY:
                self._buffer = self._buffer[-_BUFFER_CAPACITY:]

    # ── Captura periódica ──────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """
        Bucle de captura periódica. Usa Gemini si está disponible,
        fallback local (OCR + Groq) si Gemini tiene quota agotada.
        """
        while self._running:
            try:
                # Verificar si la quota de Gemini se puede reintentar
                if not self._gemini_quota_ok and time.time() > self._gemini_quota_reset:
                    self._gemini_quota_ok = True
                    print("[GeminiVision] Reintentando Gemini (quota reset)")

                # Esperar intervalo aleatorio
                intervalo = random.uniform(_CAPTURE_INTERVAL_MIN, _CAPTURE_INTERVAL_MAX)
                _wait_interruptible(intervalo, lambda: not self._running)

                if not self._running:
                    break

                # Verificar CPU antes de capturar
                _wait_for_cpu(lambda: not self._running)

                if not self._running:
                    break

                # Si Gemini no está disponible, usar análisis local directamente
                if not self._gemini_quota_ok:
                    descripcion = self._analyze_local()
                    if descripcion:
                        self._add_to_buffer(descripcion)
                    continue

                # Capturar imagen para Gemini
                if not _SCREEN_VISION_OK:
                    # Sin captura de pantalla, usar análisis local
                    descripcion = self._analyze_local()
                    if descripcion:
                        self._add_to_buffer(descripcion)
                    continue

                try:
                    img_bytes, _titulo = _capturar_ventana_rapida()
                except Exception as e:
                    print(f"[GeminiVision] Error en captura: {e}")
                    continue

                # Si la captura retorna bytes vacíos, saltar el análisis
                if not img_bytes:
                    continue

                # Analizar con Gemini y liberar memoria inmediatamente
                descripcion = self._analyze(img_bytes)
                del img_bytes   # liberar bytes de imagen explícitamente
                if descripcion:
                    self._add_to_buffer(descripcion)

            except Exception as e:
                print(f"[GeminiVision] Error en _capture_loop: {e}")
                # Continuar el bucle

    # ── Captura bajo demanda ───────────────────────────────────────────────────

    def capture_and_analyze(self) -> Optional[str]:
        """
        Captura inmediata bajo demanda y retorna la descripción.

        Retorna None si la captura falla o Gemini no está disponible.
        """
        try:
            if not _SCREEN_VISION_OK:
                return None

            img_bytes, _titulo = _capturar_ventana_rapida()
            if not img_bytes:
                return None

            descripcion = self._analyze(img_bytes)
            if descripcion:
                self._add_to_buffer(descripcion)
            return descripcion

        except Exception as e:
            print(f"[GeminiVision] Error en capture_and_analyze: {e}")
            return None

    # ── Descripción más reciente ───────────────────────────────────────────────

    def get_latest_description(self) -> Optional[str]:
        """
        Retorna la descripción más reciente si tiene menos de 30 segundos.

        Retorna None si el buffer está vacío o la descripción es antigua.
        """
        with self._buffer_lock:
            if not self._buffer:
                return None
            latest = self._buffer[-1]

        ahora = time.time()
        antiguedad = ahora - latest["timestamp"]

        if antiguedad < _FRESHNESS_SECONDS:
            return latest["description"]
        return None

    # ── Control del hilo ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicia el hilo daemon de captura periódica."""
        if self._running:
            return
        self._running = True
        self._hilo = threading.Thread(
            target=self._capture_loop,
            name="GeminiVision-capture",
            daemon=True,
        )
        self._hilo.start()

    def stop(self) -> None:
        """Detiene el hilo de captura periódica."""
        self._running = False
        # El hilo terminará en el próximo ciclo de _wait_interruptible


# ── Helpers ────────────────────────────────────────────────────────────────────

def _wait_interruptible(seconds: float, stop_condition) -> None:
    """
    Espera `seconds` segundos, pero verifica `stop_condition` cada 0.5s
    para poder interrumpir la espera.
    """
    deadline = time.time() + seconds
    while time.time() < deadline:
        if stop_condition():
            return
        time.sleep(min(0.5, deadline - time.time()))


def _wait_for_cpu(stop_condition) -> None:
    """
    Pausa si el CPU supera el 70%, esperando hasta que baje del 60%.
    Si psutil no está disponible, no hace nada.
    """
    if not _PSUTIL_OK:
        return

    try:
        cpu = _psutil.cpu_percent(interval=0.1)
        if cpu <= _CPU_PAUSE_THRESHOLD:
            return

        # CPU alta: esperar hasta que baje del umbral de reanudación
        while True:
            if stop_condition():
                return
            time.sleep(1.0)
            try:
                cpu = _psutil.cpu_percent(interval=0.1)
                if cpu < _CPU_RESUME_THRESHOLD:
                    return
            except Exception:
                return
    except Exception:
        pass
