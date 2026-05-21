"""
audio_visual_sync.py â€” SincronizaciÃ³n Audio-Visual Total para Alisha.

Cierra el cÃ­rculo: voz orgÃ¡nica + boca que reacciona a la amplitud real
del audio + entonaciÃ³n segÃºn Sarcasm Score + gaze mantenido mientras habla.

Construido sobre tts_engine.py existente. No lo reemplaza â€” lo extiende.

CaracterÃ­sticas:
  - Streaming TTS: Alisha empieza a hablar apenas se generan las primeras
    palabras (no espera a que termine toda la sÃ­ntesis)
  - Lip-sync real: ParamMouthOpenY vinculado a amplitud RMS del audio
  - EntonaciÃ³n sarcÃ¡stica: si score > 0.8 â†’ 10% mÃ¡s lento, pitch mÃ¡s bajo
  - Audio-VisiÃ³n sync: mantiene gaze_override mientras habla de algo que "vio"
  - Movimientos orgÃ¡nicos: micro-variaciones en boca para evitar efecto robot

IntegraciÃ³n:
  - Escribe en chibi_state.json (leÃ­do por cabina_virtual.py a 60fps)
  - Se conecta con brain.py (SarcasmScoreEngine)
  - Se conecta con vision_engine.py (gaze_override)
  - Extiende tts_engine.py (TTSEngine singleton)
"""

from __future__ import annotations

import io
import json
import math
import os
import random
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# â”€â”€ Dependencias opcionales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    import edge_tts as _edge_tts
    _EDGE_OK = True
except ImportError:
    _EDGE_OK = False

try:
    from pydub import AudioSegment as _AudioSegment
    # Configurar ruta de ffmpeg si no estÃ¡ en PATH
    import os as _os
    _FFMPEG_PATHS = [
        r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for _fp in _FFMPEG_PATHS:
        if _os.path.exists(_fp):
            _AudioSegment.converter = _fp
            _AudioSegment.ffmpeg    = _fp
            _AudioSegment.ffprobe   = _fp.replace("ffmpeg.exe", "ffprobe.exe")
            break
    _PYDUB_OK = True
except ImportError:
    _PYDUB_OK = False

try:
    import pygame as _pygame
    _PYGAME_OK = True
except ImportError:
    _PYGAME_OK = False

try:
    import numpy as _np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False

# Importar TTSEngine existente
from tts_engine import TTSEngine, DEFAULT_EDGE_VOICE


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PARÃMETROS DE ENTONACIÃ“N
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ToneProfile:
    """Perfil de entonaciÃ³n segÃºn estado emocional y sarcasmo."""

    def __init__(self, sarcasm_score: float = 0.0, emotional_state: str = "neutral"):
        self.sarcasm_score    = sarcasm_score
        self.emotional_state  = emotional_state

    @property
    def rate_modifier(self) -> float:
        """
        Modificador de velocidad:
          - Sarcasmo alto (>0.8) â†’ 10% mÃ¡s lento (mÃ¡s pesado/irÃ³nico)
          - Entusiasmo â†’ 10% mÃ¡s rÃ¡pido
          - Cansancio â†’ 15% mÃ¡s lento
        """
        if self.sarcasm_score > 0.8:
            return 0.90   # 10% mÃ¡s lento
        if self.sarcasm_score > 0.5:
            return 0.95   # 5% mÃ¡s lento
        if self.emotional_state == "entusiasmo":
            return 1.10
        if self.emotional_state == "cansancio":
            return 0.85
        if self.emotional_state == "frustraciÃ³n":
            return 0.92
        return 1.0

    @property
    def rate_str(self) -> str:
        """Formato edge-tts: '+10%' o '-10%' â€” suma al rate base del engine"""
        pct = int((self.rate_modifier - 1.0) * 100)
        return f"{pct:+d}%"

    @property
    def pitch_str(self) -> str:
        """
        Pitch ADICIONAL al base (+10Hz ya configurado en TTSEngine).
        Sarcasmo alto â†’ -5Hz extra (mÃ¡s grave/irÃ³nico)
        Entusiasmo â†’ +5Hz extra
        """
        if self.sarcasm_score > 0.8:
            return "-5Hz"
        if self.sarcasm_score > 0.5:
            return "-2Hz"
        if self.emotional_state == "entusiasmo":
            return "+5Hz"
        return "+0Hz"

    @property
    def volume_modifier(self) -> float:
        """Volumen relativo."""
        if self.emotional_state == "cansancio":
            return 0.85
        if self.emotional_state == "entusiasmo":
            return 1.0
        return 1.0


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIP SYNC ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class LipSyncEngine:
    """
    Sincroniza ParamMouthOpenY con la amplitud RMS real del audio.
    Escribe en chibi_state.json a ~50fps durante la reproducciÃ³n.
    """

    CHUNK_MS    = 20    # ms por chunk de anÃ¡lisis (50fps)
    SMOOTH_FAC  = 0.35  # factor de suavizado (evita saltos bruscos)
    NOISE_AMP   = 0.04  # micro-variaciÃ³n orgÃ¡nica

    def __init__(self):
        self._running   = False
        self._thread: Optional[threading.Thread] = None
        self._cur_mouth = 0.0

    def start_from_file(self, audio_path: str,
                        vision_context: bool = False) -> None:
        """
        Inicia lip-sync leyendo amplitud del archivo de audio.
        vision_context=True mantiene gaze_override mientras habla.
        """
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop,
            args=(audio_path, vision_context),
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._emit_mouth(0.0, hablando=False)

    def _sync_loop(self, audio_path: str, vision_context: bool) -> None:
        """Loop principal de sincronizaciÃ³n."""
        if _PYDUB_OK:
            self._sync_with_pydub(audio_path, vision_context)
        else:
            self._sync_fallback(audio_path, vision_context)

    def _sync_with_pydub(self, audio_path: str, vision_context: bool) -> None:
        """Lip-sync real usando pydub para leer amplitud RMS."""
        try:
            audio = _AudioSegment.from_file(audio_path)
            # Normalizar a mono para anÃ¡lisis de amplitud
            audio_mono = audio.set_channels(1)
            samples    = audio_mono.get_array_of_samples()
            rate       = audio_mono.frame_rate
            chunk_size = int(rate * self.CHUNK_MS / 1000)
            max_val    = float(2 ** (audio_mono.sample_width * 8 - 1))

            i = 0
            while self._running and i < len(samples):
                chunk = samples[i : i + chunk_size]
                if chunk:
                    # RMS de la amplitud
                    if _NUMPY_OK:
                        arr = _np.array(chunk, dtype=_np.float32)
                        rms = float(_np.sqrt(_np.mean(arr ** 2)))
                    else:
                        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))

                    # Normalizar a 0.0-1.0 con boost para visibilidad
                    # x1.4 de energÃ­a para acompaÃ±ar el tono mÃ¡s arriba
                    amplitude = min(1.0, (rms / max_val) * 5.5)

                    # Suavizado + micro-variaciÃ³n orgÃ¡nica
                    noise = random.uniform(-self.NOISE_AMP, self.NOISE_AMP)
                    target = amplitude + noise
                    self._cur_mouth = (
                        self._cur_mouth * (1 - self.SMOOTH_FAC)
                        + target * self.SMOOTH_FAC
                    )
                    self._cur_mouth = max(0.0, min(1.0, self._cur_mouth))

                    self._emit_mouth(self._cur_mouth, hablando=True,
                                     vision_context=vision_context)

                i += chunk_size
                time.sleep(self.CHUNK_MS / 1000.0)

        except Exception as e:
            print(f"[LipSync] Error pydub: {e}")
        finally:
            self._emit_mouth(0.0, hablando=False)

    def _sync_fallback(self, audio_path: str, vision_context: bool) -> None:
        """
        Fallback sin pydub: animaciÃ³n orgÃ¡nica basada en tiempo.
        Simula habla natural con ondas sinusoidales superpuestas.
        """
        t = 0.0
        # Estimar duraciÃ³n por tamaÃ±o del archivo
        try:
            size_kb = Path(audio_path).stat().st_size / 1024
            duration = max(2.0, size_kb / 16.0)  # ~16KB/s para MP3 128kbps
        except Exception:
            duration = 5.0

        t_end = time.time() + duration
        while self._running and time.time() < t_end:
            # MÃºltiples ondas para naturalidad
            val = (
                abs(math.sin(t * 8.0)) * 0.5
                + abs(math.sin(t * 13.7)) * 0.25
                + abs(math.sin(t * 5.3)) * 0.15
                + random.uniform(0, self.NOISE_AMP)
            )
            val = min(1.0, val * 0.8)
            self._cur_mouth = self._cur_mouth * 0.7 + val * 0.3
            self._emit_mouth(self._cur_mouth, hablando=True,
                             vision_context=vision_context)
            t += self.CHUNK_MS / 1000.0
            time.sleep(self.CHUNK_MS / 1000.0)

        self._emit_mouth(0.0, hablando=False)

    def _emit_mouth(self, amplitude: float, hablando: bool,
                    vision_context: bool = False) -> None:
        """Escribe amplitud de boca en el bridge en memoria Y en chibi_state.json."""

        # -- Prioridad 1: bridge en memoria (0ms, sin I/O de disco) ----------
        # cabina_virtual.py lee esto a 60fps con latencia cero.
        try:
            import alisha_bridge as _ab
            _ab.MOUTH_AMPLITUDE = round(amplitude, 3)
            _ab.IS_SPEAKING     = hablando
        except Exception:
            pass

        # -- Prioridad 2: chibi_state.json (fallback para desktop_widget.py) -
        try:
            current = {}
            if STATE_FILE.exists():
                try:
                    current = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass

            current["hablando"]        = hablando
            current["mouth_amplitude"] = round(amplitude, 3)

            # Mantener gaze_override si esta hablando de algo que "vio"
            if vision_context and hablando:
                current["gaze_override"] = True
            elif not hablando:
                current["gaze_override"] = False

            STATE_FILE.write_text(
                json.dumps(current, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STREAMING TTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class StreamingTTS:
    """
    TTS con streaming: Alisha empieza a hablar apenas se generan
    las primeras palabras, sin esperar a que termine toda la sÃ­ntesis.

    Estrategia:
      1. Dividir texto en chunks semÃ¡nticos (por puntuaciÃ³n)
      2. Sintetizar y reproducir chunk a chunk
      3. Lip-sync en tiempo real para cada chunk
    """

    # TamaÃ±o mÃ­nimo de chunk para no generar audio muy corto
    MIN_CHUNK_CHARS = 30
    MAX_CHUNK_CHARS = 150

    def __init__(self):
        self._lipsync = LipSyncEngine()
        self._playing = False
        self._lock    = threading.Lock()

    def speak_streaming(self, text: str, tone: ToneProfile,
                        vision_context: bool = False,
                        on_chunk_start: Optional[callable] = None) -> None:
        """
        Habla el texto en streaming.
        on_chunk_start: callback llamado antes de cada chunk (para UI).
        """
        chunks = self._split_text(text)
        if not chunks:
            return

        with self._lock:
            self._playing = True

        try:
            for i, chunk in enumerate(chunks):
                if not self._playing:
                    break

                if on_chunk_start:
                    on_chunk_start(chunk, i, len(chunks))

                self._speak_chunk(chunk, tone, vision_context)

        finally:
            with self._lock:
                self._playing = False
            self._lipsync.stop()

    def speak_streaming_async(self, text: str, tone: ToneProfile,
                               vision_context: bool = False,
                               on_done: Optional[callable] = None) -> None:
        """VersiÃ³n asÃ­ncrona â€” no bloquea."""
        def _run():
            self.speak_streaming(text, tone, vision_context)
            if on_done:
                on_done()

        threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            self._playing = False
        self._lipsync.stop()
        # Garantizar reset del bridge aunque lipsync.stop() falle
        try:
            import alisha_bridge as _ab
            _ab.IS_SPEAKING     = False
            _ab.MOUTH_AMPLITUDE = 0.0
        except Exception:
            pass

    def _speak_chunk(self, text: str, tone: ToneProfile,
                     vision_context: bool) -> None:
        """Sintetiza y reproduce un chunk con lip-sync."""
        if not text.strip():
            return

        tmp_path = None
        try:
            if _EDGE_OK:
                tmp_path = self._synthesize_edge(text, tone)
            else:
                # Sin edge-tts: lip-sync simulado sin audio duplicado
                words = len(text.split())
                duration = max(1.0, words / 2.5)
                self._lipsync_duration(duration, vision_context)
                return

            if tmp_path and Path(tmp_path).exists():
                self._play_with_lipsync(tmp_path, vision_context)

        except Exception as e:
            print(f"[StreamingTTS] Error en chunk: {e}")
            # NO llamar TTSEngine aquÃ­ â€” evita doble voz
            # Solo hacer lip-sync simulado
            try:
                words = len(text.split())
                self._lipsync_duration(max(1.0, words / 2.5), vision_context)
            except Exception:
                pass
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def _synthesize_edge(self, text: str, tone: ToneProfile) -> Optional[str]:
        """Sintetiza con edge-tts y retorna ruta del archivo temporal."""
        import asyncio

        async def _synth():
            # Combinar pitch base del engine (+10Hz) con el adicional del tono
            try:
                from tts_engine import TTSEngine as _TTS
                base_pitch_hz = int(_TTS()._edge_pitch.replace('Hz','').replace('+',''))
            except Exception:
                base_pitch_hz = 10

            add_pitch_str = tone.pitch_str  # ej: "+5Hz" o "-5Hz"
            add_hz = int(add_pitch_str.replace('Hz','').replace('+',''))
            total_hz = base_pitch_hz + add_hz
            final_pitch = f"{total_hz:+d}Hz"

            communicate = _edge_tts.Communicate(
                text,
                DEFAULT_EDGE_VOICE,
                rate=tone.rate_str,
                pitch=final_pitch,
                volume=f"{int((tone.volume_modifier - 1.0) * 100):+d}%",
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            await communicate.save(tmp)
            return tmp

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_synth())
            loop.close()
            return result
        except Exception as e:
            print(f"[StreamingTTS] edge-tts error: {e}")
            return None

    def _play_with_lipsync(self, audio_path: str, vision_context: bool) -> None:
        """Reproduce audio y sincroniza lip-sync en paralelo."""
        # Iniciar lip-sync en hilo separado
        self._lipsync.start_from_file(audio_path, vision_context)

        # Reproducir audio
        played = False
        if _PYGAME_OK:
            try:
                if not _pygame.mixer.get_init():
                    import os as _os_sdl; _os_sdl.environ.setdefault("SDL_VIDEODRIVER","dummy"); _os_sdl.environ.setdefault("SDL_AUDIODRIVER","directsound"); _pygame.mixer.pre_init(44100,-16,2,512); _pygame.mixer.init()
                _pygame.mixer.music.load(audio_path)
                _pygame.mixer.music.play()
                while _pygame.mixer.music.get_busy():
                    time.sleep(0.02)
                played = True
            except Exception as e:
                print(f"[StreamingTTS] pygame error: {e}")

        if not played:
            try:
                import playsound
                playsound.playsound(audio_path)
                played = True
            except Exception:
                pass

        if not played:
            # Sin fallback de os.startfile — no abrir Explorador ni reproductor
            # Si pygame y playsound fallan, el audio simplemente no suena
            # pero el lip-sync sigue funcionando
            try:
                if _PYDUB_OK:
                    audio = _AudioSegment.from_file(audio_path)
                    time.sleep(len(audio) / 1000.0)
                else:
                    time.sleep(3.0)
            except Exception:
                time.sleep(2.0)

        # Detener lip-sync
        self._lipsync.stop()

    def _lipsync_duration(self, duration: float, vision_context: bool) -> None:
        """Lip-sync fallback basado en duraciÃ³n estimada."""
        t = 0.0
        while t < duration:
            val = abs(math.sin(t * 9.0)) * 0.7 + random.uniform(0, 0.05)
            self._lipsync._emit_mouth(val, hablando=True,
                                      vision_context=vision_context)
            time.sleep(0.02)
            t += 0.02
        self._lipsync._emit_mouth(0.0, hablando=False)

    def _split_text(self, text: str) -> list[str]:
        """
        Divide el texto en chunks semÃ¡nticos para streaming.
        Corta por puntuaciÃ³n respetando tamaÃ±o mÃ­nimo/mÃ¡ximo.
        """
        import re

        # Limpiar texto
        text = text.strip()
        if not text:
            return []

        # Si es corto, no dividir
        if len(text) <= self.MAX_CHUNK_CHARS:
            return [text]

        # Dividir por puntuaciÃ³n fuerte primero
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""

        for sentence in sentences:
            if not sentence.strip():
                continue

            if len(current) + len(sentence) <= self.MAX_CHUNK_CHARS:
                current += (" " if current else "") + sentence
            else:
                if current and len(current) >= self.MIN_CHUNK_CHARS:
                    chunks.append(current.strip())
                    current = sentence
                elif not current:
                    # OraciÃ³n muy larga â€” dividir por comas
                    parts = re.split(r'(?<=,)\s+', sentence)
                    for part in parts:
                        if len(current) + len(part) <= self.MAX_CHUNK_CHARS:
                            current += (" " if current else "") + part
                        else:
                            if current:
                                chunks.append(current.strip())
                            current = part
                else:
                    chunks.append(current.strip())
                    current = sentence

        if current.strip():
            chunks.append(current.strip())

        return [c for c in chunks if c.strip()]


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AUDIO VISUAL SYNC â€” orquestador principal
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AudioVisualSync:
    """
    Orquestador de sincronizaciÃ³n audio-visual.
    Punto de entrada Ãºnico para hacer hablar a Alisha con todo integrado.

    Uso:
        avs = get_audio_visual_sync()
        avs.speak("Che, esto tiene sus cositas...", sarcasm_score=0.9)
    """

    def __init__(self):
        self._streaming = StreamingTTS()
        self._tts       = TTSEngine()   # singleton existente
        self._speaking  = False         # semÃ¡foro â€” solo una voz a la vez
        self._speak_lock = threading.Lock()

    def speak(self, text: str,
              sarcasm_score: float = 0.0,
              emotional_state: str = "neutral",
              vision_context: bool = False,
              async_mode: bool = True) -> None:
        """
        Hace hablar a Alisha con sincronizaciÃ³n completa.
        Si ya estÃ¡ hablando, descarta el nuevo texto para evitar superposiciÃ³n.
        """
        if not text.strip():
            return

        # Verificar si el TTS está silenciado (modelo 2D oculto)
        try:
            from config import DATA_DIR
            from pathlib import Path as _Path
            import json as _json
            _sf = DATA_DIR / "chibi_state.json"
            if _sf.exists():
                _sd = _json.loads(_sf.read_text(encoding="utf-8"))
                if _sd.get("tts_silenciado", False):
                    return  # silenciado — no reproducir
        except Exception:
            pass
        with self._speak_lock:
            if self._speaking:
                print(f"[AudioVisualSync] â­ Descartado (ya hablando): {text[:40]}...")
                return
            self._speaking = True

        tone = ToneProfile(sarcasm_score, emotional_state)

        print(
            f"[AudioVisualSync] ðŸŽ™ Hablando "
            f"(sarcasmo={sarcasm_score:.2f}, "
            f"rate={tone.rate_str}, pitch={tone.pitch_str}, "
            f"vision={vision_context})"
        )

        def _on_done():
            with self._speak_lock:
                self._speaking = False
            print("[AudioVisualSync] âœ“ Fin de habla")

        if async_mode:
            self._streaming.speak_streaming_async(
                text, tone, vision_context,
                on_done=_on_done
            )
        else:
            self._streaming.speak_streaming(text, tone, vision_context)
            with self._speak_lock:
                self._speaking = False

    def speak_from_brain_response(self, response, vision_context: bool = False) -> None:
        """
        Atajo para hablar directamente desde un AlishaResponse del brain.
        Extrae sarcasm_score y emotional_state automÃ¡ticamente.
        """
        from brain import AlishaResponse
        if not isinstance(response, AlishaResponse):
            self.speak(str(response))
            return

        emotional = "neutral"
        state = response.emotional_state
        if state.dopamina > 0.85:
            emotional = "entusiasmo"
        elif state.tension > 0.5:
            emotional = "preocupaciÃ³n"
        elif state.irritabilidad > 0.5:
            emotional = "frustraciÃ³n"
        elif state.dopamina < 0.3:
            emotional = "cansancio"

        self.speak(
            response.content,
            sarcasm_score=response.sarcasm_score,
            emotional_state=emotional,
            vision_context=vision_context,
        )

    def stop(self) -> None:
        self._streaming.stop()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SINGLETON
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_avs: Optional[AudioVisualSync] = None

def get_audio_visual_sync() -> AudioVisualSync:
    global _avs
    if _avs is None:
        _avs = AudioVisualSync()
    return _avs

