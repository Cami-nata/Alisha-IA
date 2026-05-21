"""Motor TTS singleton con cola asÃ­ncrona para procesamiento FIFO.
Soporta edge-tts (voces neurales de Microsoft) con fallback a pyttsx3.
"""

import asyncio
import math
import os
import queue
import threading
import tempfile

# Intentar edge-tts primero (mejor calidad)
try:
    import edge_tts
    _EDGE_TTS_OK = True
except ImportError:
    _EDGE_TTS_OK = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_NAME

# Voz por defecto â€” Elena Argentina (acento rioplatense natural)
DEFAULT_EDGE_VOICE = "es-AR-ElenaNeural"
EDGE_VOICES_ES = {
    "alisha":   "es-AR-ElenaNeural",      # Voz principal de Alisha (Elena - Argentina)
    "elena":    "es-AR-ElenaNeural",      # Argentina vibrante â€” voz principal
    "elvira":   "es-ES-ElviraNeural",     # EspaÃ±ola (fallback)
    "dalia":    "es-MX-DaliaNeural",      # Mexicana dulce
    "salome":   "es-CO-SalomeNeural",     # Colombiana expresiva
    "valentina":"es-UY-ValentinaNeural",  # Uruguaya cÃ¡lida
    "camila":   "es-PE-CamilaNeural",     # Peruana suave
    "paloma":   "es-US-PalomaNeural",     # Estados Unidos
    "helena":   "0",                      # SAPI Helena (ID: 0)
}
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
ELEVENLABS_VOICE_FALLBACK = "Elena"


def _is_silenciado() -> bool:
    """Retorna True si el modelo 2D está oculto y la voz debe silenciarse."""
    try:
        from config import DATA_DIR
        import json as _j
        sf = DATA_DIR / "chibi_state.json"
        if sf.exists():
            return _j.loads(sf.read_text(encoding="utf-8")).get("tts_silenciado", False)
    except Exception:
        pass
    return False


def calcular_amplitudes_rms(audio_bytes: bytes, sample_rate: int = 24000) -> list[float]:
    """
    Pre-calcula array de amplitudes RMS con chunks de 40ms.
    Retorna lista de floats en [0.0, 1.0].
    Fallback sinusoidal si numpy/pydub no están disponibles.
    """
    try:
        import numpy as np
        from pydub import AudioSegment
        import io

        audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)

        chunk_size = int(sample_rate * 0.040)
        amplitudes: list[float] = []
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i:i + chunk_size]
            if len(chunk) == 0:
                continue
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            amp = min(1.0, rms / 8000.0)
            amplitudes.append(amp)

        return amplitudes if amplitudes else [0.0]

    except Exception:
        # Fallback sinusoidal si numpy/pydub no están disponibles
        chunk_size = int(sample_rate * 0.040)
        num_chunks = max(1, len(audio_bytes) // (chunk_size * 2))  # 2 bytes por muestra (16-bit)
        return [
            abs(math.sin(i * 0.040 * 8.0)) * 0.6 + 0.1
            for i in range(num_chunks)
        ]


class LipSyncThread:
    """
    Hilo daemon que escribe mouth_amplitude en chibi_state.json a 25 Hz.
    Recibe un array pre-calculado de amplitudes y las emite en orden.
    Fail-silent: errores de escritura se descartan sin interrumpir la reproducción.
    """
    INTERVAL_S  = 0.040    # 40ms = 25 Hz
    NORM_FACTOR = 8000.0   # calibrado para edge-tts

    def __init__(self, amplitudes: list, state_file):
        self._amplitudes  = amplitudes
        self._state_file  = state_file
        self._stop_event  = threading.Event()
        self._thread      = threading.Thread(target=self._run, daemon=True,
                                             name="LipSyncThread")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._write_amplitude(0.0)

    def _run(self) -> None:
        for amp in self._amplitudes:
            if self._stop_event.is_set():
                break
            self._write_amplitude(amp)
            import time as _t
            _t.sleep(self.INTERVAL_S)
        self._write_amplitude(0.0)

    def _write_amplitude(self, amp: float) -> None:
        try:
            import json as _json
            from pathlib import Path as _Path
            sf = _Path(self._state_file) if not hasattr(self._state_file, 'read_text') else self._state_file
            data = {}
            if sf.exists():
                try:
                    data = _json.loads(sf.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data["mouth_amplitude"] = max(0.0, min(1.0, amp))
            sf.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # fail-silent: no interrumpir reproducción


class TTSEngine:
    """Singleton TTS con soporte edge-tts (neuronal) y fallback a pyttsx3."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._queue: queue.Queue = queue.Queue()
        self._engine = None          # pyttsx3 fallback
        self._rate = 175             # Velocidad mÃ¡s natural y humana
        self._volume = 1.0           # Volumen mÃ¡ximo
        self._voice_id = None
        self._edge_voice = DEFAULT_EDGE_VOICE
        self._edge_rate  = "+5%"     # +5% velocidad base â€” mÃ¡s juvenil
        self._edge_pitch = "+10Hz"   # +10Hz tono base â€” mÃ¡s joven, menos seria
        self._use_eleven = _REQUESTS_OK and bool(ELEVENLABS_API_KEY)
        self._use_edge = not self._use_eleven and _EDGE_TTS_OK
        self._rate_modifier = 1.0    # modificador de velocidad (energÃ­a)
        self._active_lipsync: "LipSyncThread | None" = None
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TTSWorker")
        self._thread.start()

    def _set_hablando(self, hablando: bool) -> None:
        """Actualiza el estado hablando en chibi_state.json para sincronizar el modelo Live2D."""
        try:
            from assistant_state import actualizar_estado
            actualizar_estado(hablando=hablando)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Hilo daemon
    # ------------------------------------------------------------------

    def _worker(self):
        """Procesa mensajes de la cola en orden FIFO."""
        if getattr(self, "_use_eleven", False):
            self._worker_elevenlabs()
        elif self._use_edge:
            self._worker_edge()
        elif pyttsx3 is None:
            self._worker_print()
        else:
            self._worker_pyttsx3()

    def _get_eleven_voice_id(self) -> str:
        """Resuelve la voz de ElevenLabs por nombre o ID."""
        if not _REQUESTS_OK or not ELEVENLABS_API_KEY:
            return ELEVENLABS_VOICE_NAME
        try:
            resp = requests.get(
                f"{ELEVENLABS_API_BASE}/voices",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            voices = data.get("voices", [])
            candidate = None
            voice_name = str(self._edge_voice or ELEVENLABS_VOICE_NAME).strip().lower()
            for voice in voices:
                name = str(voice.get("name", "")).strip().lower()
                vid = voice.get("voice_id")
                if name == voice_name and vid:
                    return vid
                if "elena" in name and vid:
                    candidate = vid
            return candidate or (voices[0].get("voice_id") if voices else ELEVENLABS_VOICE_NAME)
        except Exception:
            return ELEVENLABS_VOICE_NAME

    def _worker_elevenlabs(self):
        """Worker usando ElevenLabs cuando estÃ¡ configurado."""
        while True:
            item = self._queue.get()
            if item is None:
                break
            text, event = item
            try:
                print(text)
                self._set_hablando(True)
                self._speak_elevenlabs(text)
            except Exception as exc:
                print(f"[TTSEngine/elevenlabs] Error: {exc}")
            finally:
                self._set_hablando(False)
                if event:
                    event.set()
                self._queue.task_done()

    def _speak_elevenlabs(self, text: str) -> None:
        """
        Sintetiza con ElevenLabs Multilingual v2 con streaming real y lip-sync.

        Flujo:
          1. Solicita audio con streaming (chunks llegan mientras se genera)
          2. Escribe chunks a archivo temporal mientras los recibe
          3. Reproduce con pygame en cuanto el archivo estÃ¡ listo
          4. Lip-sync: calcula amplitudes reales con pydub+numpy (igual que edge-tts)
        """
        voice_id = self._get_eleven_voice_id()
        if not voice_id:
            raise RuntimeError("No se pudo resolver voice_id de ElevenLabs.")
        try:
            # â”€â”€ Endpoint con streaming + modelo Multilingual v2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            url = f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}/stream"
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",   # â† Multilingual v2
                "voice_settings": {
                    "stability":         0.45,   # mÃ¡s variaciÃ³n = mÃ¡s expresiva
                    "similarity_boost":  0.75,   # fidelidad a la voz original
                    "style":             0.35,   # estilo/emociÃ³n (0=neutro, 1=mÃ¡ximo)
                    "use_speaker_boost": True,   # claridad extra
                },
                "optimize_streaming_latency": 3,  # 0-4: mayor = menos latencia, menos calidad
            }
            headers = {
                "xi-api-key":   ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept":       "audio/mpeg",
            }

            # â”€â”€ Descargar chunks y escribir al archivo temporal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name

            with requests.post(url, json=payload, headers=headers,
                               stream=True, timeout=90) as resp:
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=4096):
                        if chunk:
                            f.write(chunk)

            # â”€â”€ Reproducir con pygame + lip-sync real â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            try:
                import pygame
                import time as _time
                os.environ.setdefault("SDL_VIDEODRIVER","dummy"); os.environ.setdefault("SDL_AUDIODRIVER","directsound"); pygame.mixer.pre_init(44100,-16,2,512); pygame.mixer.init()
                pygame.mixer.music.load(tmp_path)

                # Pre-calcular amplitudes reales del MP3 con calcular_amplitudes_rms
                try:
                    with open(tmp_path, "rb") as _f:
                        _audio_bytes = _f.read()
                    _amplitudes = calcular_amplitudes_rms(_audio_bytes)
                except Exception:
                    _amplitudes = []

                pygame.mixer.music.play()

                # Lip-sync con LipSyncThread
                from config import DATA_DIR
                _state_file = DATA_DIR / "chibi_state.json"
                _lipsync_amps = _amplitudes if _amplitudes else calcular_amplitudes_rms(b"", sample_rate=24000)
                _lipsync = LipSyncThread(amplitudes=_lipsync_amps, state_file=_state_file)
                self._active_lipsync = _lipsync
                _lipsync.start()

                while pygame.mixer.music.get_busy():
                    _time.sleep(0.05)
                    # Cortar si se silencia durante la reproducción
                    if _is_silenciado():
                        pygame.mixer.music.stop()
                        break

                _lipsync.stop()
                self._active_lipsync = None

            except Exception:
                try:
                    import playsound
                    playsound.playsound(tmp_path)
                except Exception:
                    pass  # sin fallback — no abrir Explorador
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            raise RuntimeError(f"[elevenlabs] {e}")

    def _worker_edge(self):
        """Worker usando edge-tts (voces neurales)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            item = self._queue.get()
            if item is None:
                break
            text, event = item
            try:
                print(text)
                self._set_hablando(True)
                loop.run_until_complete(self._speak_edge(text))
            except Exception as exc:
                print(f"[TTSEngine/edge] Error: {exc}")
            finally:
                self._set_hablando(False)
                if event:
                    event.set()
                self._queue.task_done()

    async def _speak_edge(self, text: str) -> None:
        """Sintetiza con edge-tts con streaming real, lip-sync y word timestamps."""
        try:
            rate_pct = int((self._rate_modifier - 1.0) * 100)
            # Combinar rate base (+5%) con modificador dinÃ¡mico
            base_rate = int(self._edge_rate.replace('%','').replace('+',''))
            total_rate = base_rate + rate_pct
            rate_str = f"{total_rate:+d}%"

            communicate = edge_tts.Communicate(
                text,
                self._edge_voice,
                rate=rate_str,
                pitch=self._edge_pitch,
            )

            audio_chunks = []
            word_timestamps = []   # [{word, offset_s}, ...]

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # offset en unidades de 100 nanosegundos â†’ segundos
                    offset_s = chunk.get("offset", 0) / 10_000_000.0
                    word = chunk.get("text", "")
                    if word:
                        word_timestamps.append({"word": word, "offset_s": offset_s})

            if not audio_chunks:
                return

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
                for c in audio_chunks:
                    f.write(c)

            # Publicar timestamps en el bridge ANTES de reproducir
            try:
                import alisha_bridge as _bridge
                _bridge.WORD_TIMESTAMPS = word_timestamps
            except Exception:
                pass

            try:
                import pygame
                import time as _time
                os.environ.setdefault("SDL_VIDEODRIVER","dummy"); os.environ.setdefault("SDL_AUDIODRIVER","directsound"); pygame.mixer.pre_init(44100,-16,2,512); pygame.mixer.init()
                pygame.mixer.music.load(tmp_path)

                # Pre-calcular amplitudes reales del MP3 con pydub
                _amplitudes = []
                try:
                    from pydub import AudioSegment
                    import numpy as np
                    audio = AudioSegment.from_mp3(tmp_path)
                    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                    chunk_ms = 40  # 40ms por chunk = 25fps
                    chunk_size = int(audio.frame_rate * chunk_ms / 1000)
                    for i in range(0, len(samples), chunk_size):
                        chunk = samples[i:i+chunk_size]
                        if len(chunk) > 0:
                            rms = float(np.sqrt(np.mean(chunk**2)))
                            amp = min(1.0, rms / 8000.0)
                            _amplitudes.append(amp)
                except Exception:
                    _amplitudes = []

                pygame.mixer.music.play()

                # Registrar timestamp de inicio de reproducciÃ³n en el bridge
                try:
                    import alisha_bridge as _bridge
                    _bridge.AUDIO_START_TS = _time.time()
                except Exception:
                    pass

                # Lip-sync con LipSyncThread
                from config import DATA_DIR
                _state_file = DATA_DIR / "chibi_state.json"
                _lipsync_amps = _amplitudes if _amplitudes else calcular_amplitudes_rms(b"", sample_rate=24000)
                _lipsync = LipSyncThread(amplitudes=_lipsync_amps, state_file=_state_file)
                self._active_lipsync = _lipsync
                _lipsync.start()

                while pygame.mixer.music.get_busy():
                    _time.sleep(0.05)

                _lipsync.stop()
                self._active_lipsync = None

                # Limpiar timestamps al terminar
                try:
                    import alisha_bridge as _bridge
                    _bridge.WORD_TIMESTAMPS = []
                    _bridge.AUDIO_START_TS  = 0.0
                except Exception:
                    pass

            except Exception:
                try:
                    import playsound
                    playsound.playsound(tmp_path)
                except Exception:
                    pass  # sin fallback — no abrir Explorador

            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        except Exception as e:
            print(f"[edge-tts] Error: {e}")

    def _worker_pyttsx3(self):
        """Worker usando pyttsx3 (fallback)."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass
        try:
            self._engine = pyttsx3.init()
            self._apply_config()
        except Exception as exc:
            print(f"[TTSEngine] No se pudo inicializar pyttsx3: {exc}")
            self._engine = None

        while True:
            item = self._queue.get()
            if item is None:
                break
            text, event = item
            try:
                print(text)
                self._set_hablando(True)
                if self._engine is not None:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception as exc:
                print(f"[TTSEngine] Error al hablar: {exc}")
            finally:
                self._set_hablando(False)
                if event:
                    event.set()
                self._queue.task_done()

    def _worker_print(self):
        """Fallback: solo imprime."""
        while True:
            item = self._queue.get()
            if item is None:
                break
            text, event = item
            print(text)
            if event:
                event.set()
            self._queue.task_done()

    def _apply_config(self):
        if self._engine is None:
            return
        try:
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)
            if self._voice_id is not None:
                self._engine.setProperty("voice", self._voice_id)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # API pÃºblica
    # ------------------------------------------------------------------

    def speak(self, text: str) -> None:
        """Encola el texto para hablar de forma asíncrona (no bloquea)."""
        if _is_silenciado():
            return
        self._queue.put((text, None))

    def speak_sync(self, text: str) -> None:
        """Encola el texto y bloquea hasta que el audio termina."""
        if _is_silenciado():
            return
        event = threading.Event()
        self._queue.put((text, event))
        event.wait()

    def stop_audio(self) -> None:
        """Detiene el audio en curso y vacía la cola."""
        # Vaciar cola
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                break
        # Detener pygame
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.stop()
        except Exception:
            pass
        # Detener lipsync activo
        if self._active_lipsync is not None:
            self._active_lipsync.stop()
            self._active_lipsync = None
        self._emit_mouth(0.0)

    def set_rate(self, rate: int) -> None:
        """Cambia la velocidad de habla (palabras por minuto)."""
        self._rate = rate
        if self._engine is not None:
            try:
                self._engine.setProperty("rate", rate)
            except Exception:
                pass

    def set_volume(self, volume: float) -> None:
        """Cambia el volumen (0.0 a 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if self._engine is not None:
            try:
                self._engine.setProperty("volume", self._volume)
            except Exception:
                pass

    def set_voice(self, voice_id: str) -> None:
        """Cambia la voz. Acepta nombre corto ('dalia', 'elena') o ID completo."""
        voz_completa = EDGE_VOICES_ES.get(voice_id.lower(), voice_id)
        if getattr(self, "_use_eleven", False):
            self._edge_voice = voz_completa
            print(f"[TTS] ElevenLabs voice configurada: {voz_completa}")
        elif self._use_edge:
            self._edge_voice = voz_completa
            print(f"[TTS] Voz Edge-TTS cambiada a: {voz_completa}")
        else:
            # Para pyttsx3, si es un nÃºmero, usar como Ã­ndice
            if voice_id.isdigit():
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    voices = engine.getProperty('voices')
                    voice_index = int(voice_id)
                    if 0 <= voice_index < len(voices):
                        self._voice_id = voices[voice_index].id
                        print(f"[TTS] Voz SAPI cambiada a: {voices[voice_index].name}")
                    else:
                        print(f"[TTS] Ãndice de voz invÃ¡lido: {voice_index}")
                except Exception as e:
                    print(f"[TTS] Error configurando voz por Ã­ndice: {e}")
            else:
                self._voice_id = voice_id
                print(f"[TTS] Voz SAPI configurada: {voice_id}")
            
            if self._engine is not None:
                try:
                    self._engine.setProperty("voice", self._voice_id)
                except Exception:
                    pass

    def set_rate_modifier(self, modifier: float) -> None:
        """Modifica la velocidad segÃºn energÃ­a. 1.0=normal, 0.7=lento."""
        self._rate_modifier = max(0.5, min(1.5, modifier))

    def _start_lipsync(self, audio_path: str) -> None:
        """Inicia el hilo de lip-sync leyendo la amplitud del audio."""
        self._lipsync_running = True
        import threading
        t = threading.Thread(target=self._lipsync_loop, args=(audio_path,), daemon=True)
        t.start()

    def _stop_lipsync(self) -> None:
        """Detiene el lip-sync y cierra la boca."""
        self._lipsync_running = False
        self._emit_mouth(0.0)

    def _lipsync_loop(self, audio_path: str) -> None:
        """Lee la amplitud del MP3 y emite valores de boca al chibi_state."""
        try:
            # Decodificar MP3 a PCM con pydub para leer amplitud
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(audio_path)
                samples = audio.get_array_of_samples()
                sample_rate = audio.frame_rate
                chunk_size = sample_rate // 20  # 50ms por chunk

                i = 0
                while self._lipsync_running and i < len(samples):
                    chunk = samples[i:i + chunk_size]
                    if chunk:
                        # RMS de la amplitud
                        import math
                        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
                        # Normalizar a 0.0-1.0
                        max_val = 32768.0
                        amplitude = min(1.0, rms / max_val * 3.0)
                        self._emit_mouth(amplitude)
                    i += chunk_size
                    import time
                    time.sleep(0.05)
            except ImportError:
                # Sin pydub: usar animaciÃ³n simple basada en tiempo
                import time, math
                t = 0
                while self._lipsync_running:
                    t += 0.1
                    val = abs(math.sin(t * 8)) * 0.7
                    self._emit_mouth(val)
                    time.sleep(0.05)
        except Exception:
            pass
        finally:
            self._emit_mouth(0.0)

    def _emit_mouth(self, amplitude: float) -> None:
        """Emite amplitud de boca via JSON (Ãºnico canal entre procesos)."""
        try:
            from assistant_state import STATE_FILE
            import json
            # Leer estado actual
            data = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data["mouth_amplitude"] = round(amplitude, 3)
            data["hablando"] = amplitude > 0.01
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def listar_voces_disponibles(self) -> list[str]:
        """Retorna las voces en espaÃ±ol disponibles."""
        return list(EDGE_VOICES_ES.keys())

    def stop(self) -> None:
        """Detiene el hilo TTS limpiamente."""
        try:
            self._queue.put(None)
        except Exception:
            pass


def _limpiar_texto_para_tts(texto: str) -> str:
    """Limpia y prepara el texto para una sÃ­ntesis de voz mÃ¡s natural."""
    import re

    # â”€â”€ Onomatopeyas y expresiones informales â†’ versiÃ³n hablable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Risas: jajaja, jeje, haha â†’ reemplazar por pausa natural
    texto = re.sub(r'\b(ja){2,}\b', 'ja ja ja', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\b(je){2,}\b', 'je je', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\b(ha){2,}\b', 'ha ha', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\b(ji){2,}\b', 'ji ji', texto, flags=re.IGNORECASE)

    # Dudas/pausas: umm, mmm, ehh â†’ pausa con coma
    texto = re.sub(r'\b(u+m+|m+m+|e+h+|a+h+)\b', ',', texto, flags=re.IGNORECASE)

    # Expresiones con letras separadas: u-m-m, j-a-j-a â†’ unir
    texto = re.sub(r'([a-zA-Z])-([a-zA-Z])', r'\1\2', texto)

    # ── Detectar y procesar acciones de animación antes de limpiar ──────────────
    # Buscar acciones entre asteriscos (*acción*) y procesarlas
    asterisk_actions = re.findall(r'\*([^*]+)\*', texto)
    
    if asterisk_actions:
        try:
            # Importar la función de animación
            import alisha_bridge
            
            # Procesar cada acción encontrada
            for action in asterisk_actions:
                action_clean = action.strip()
                if action_clean:
                    print(f"[TTS] Procesando animación: *{action_clean}*")
                    alisha_bridge.trigger_animation(action_clean)
        except Exception as e:
            print(f"[TTS] Error procesando animaciones: {e}")

    # Eliminar asteriscos de roleplay DESPUÉS de procesarlos para animación
    texto = re.sub(r'\*[^*]+\*', '', texto)

    # Eliminar TOOL_CALL y texto tÃ©cnico que no debe leerse
    texto = re.sub(r'TOOL_CALL:\s*\w+\s*\([^)]*\)', '', texto)
    texto = re.sub(r'\[Resultado de [^\]]+\]:[^\n]*', '', texto)

    # Eliminar emojis y caracteres especiales (preservar espaÃ±ol)
    texto = re.sub(r'[^\w\s.,;:!?Â¿Â¡\-Ã¡Ã©Ã­Ã³ÃºÃ¼Ã±ÃÃ‰ÃÃ“ÃšÃœÃ‘]', '', texto)

    # Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto)

    # Pausas en puntuaciÃ³n
    texto = re.sub(r'\.', '. ', texto)
    texto = re.sub(r',', ', ', texto)
    texto = re.sub(r'!', '! ', texto)
    texto = re.sub(r'\?', '? ', texto)

    texto = re.sub(r'\s+', ' ', texto).strip()

    if texto and not texto.endswith(('.', '!', '?')):
        texto += '.'

    return texto


# ------------------------------------------------------------------
# FunciÃ³n de mÃ³dulo â€” compatibilidad con voice.py existente
# ------------------------------------------------------------------

def speak(text: str) -> None:
    """Interfaz de módulo compatible con la función speak() de voice.py."""
    texto_limpio = _limpiar_texto_para_tts(text)
    if texto_limpio:
        TTSEngine().speak(texto_limpio)

