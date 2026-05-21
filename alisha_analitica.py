"""
alisha_analitica.py — Sistema analítico y humano de Alisha.

Nueva lógica:
- Bucle de análisis cada 10 minutos
- Comentarios con voseo rioplatense
- Análisis contextual inteligente
- Silencio operativo durante tareas repetitivas
- Personalidad de compañera de trabajo
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class ActivitySession:
    """Representa una sesión de actividad del usuario."""
    activity_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    details: List[str] = None
    window_titles: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []
        if self.window_titles is None:
            self.window_titles = []
    
    @property
    def duration_minutes(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() / 60

class AlishaAnalitica:
    """Sistema analítico y humano de Alisha con personalidad rioplatense."""
    
    def __init__(self, user_name: str = "Camila"):
        self.user_name = user_name
        self.current_session: Optional[ActivitySession] = None
        self.session_history: List[ActivitySession] = []
        self.last_analysis_time = datetime.now()
        self.analysis_interval = 600  # 10 minutos — habla solo cuando hay algo nuevo
        self.is_running = False
        self.silence_mode = False
        
        # Patrones de actividad para análisis contextual
        self.activity_patterns = {
            'coding': {
                'keywords': ['vscode', 'code', 'github', 'stackoverflow', 'python', 'javascript', 'html'],
                'personality_responses': [
                    "Che {name}, veo que le estás metiendo duro al código. ¿Querés que revise si quedó algún error pendiente?",
                    "Mirá vos, {name}, estás en modo programador intenso. ¿Cómo va ese proyecto?",
                    "Ey {name}, te veo concentrada con el código. Si necesitás una segunda opinión, acá estoy.",
                    "Che {name}, llevás un rato largo programando. ¿Todo bien o te trabaste en algo?"
                ]
            },
            'design': {
                'keywords': ['canva', 'figma', 'photoshop', 'design', 'creative'],
                'personality_responses': [
                    "Opa {name}, veo que estás en modo creativo. ¿Qué estás diseñando?",
                    "Che {name}, te noto inspirada con el diseño. ¿Es para algún proyecto especial?",
                    "Mirá vos {name}, estás en tu salsa creativa. ¿Cómo va quedando?",
                    "Ey {name}, llevás un buen rato diseñando. ¿Necesitás una opinión externa?"
                ]
            },
            'research': {
                'keywords': ['google', 'wikipedia', 'youtube', 'tutorial', 'documentation'],
                'personality_responses': [
                    "Che {name}, veo que estás investigando. ¿Buscás algo específico o andás explorando?",
                    "Mirá {name}, te veo en modo investigación. ¿Puedo ayudarte a encontrar algo?",
                    "Ey {name}, estás buceando información. ¿Es para algún proyecto nuevo?",
                    "Che {name}, veo que estás aprendiendo algo. ¿Qué tema te tiene enganchada?"
                ]
            },
            'communication': {
                'keywords': ['whatsapp', 'discord', 'telegram', 'email', 'slack'],
                'personality_responses': [
                    "Che {name}, veo que estás en modo social. ¿Todo bien con la gente?",
                    "Mirá {name}, andás charlando bastante. ¿Coordinando algo importante?",
                    "Ey {name}, te veo conectada con el mundo. ¿Alguna novedad interesante?",
                    "Che {name}, estás en modo comunicación. ¿Resolviendo temas de trabajo?"
                ]
            },
            'entertainment': {
                'keywords': ['netflix', 'youtube', 'spotify', 'music', 'video', 'game'],
                'personality_responses': [
                    "Che {name}, veo que te estás tomando un respiro. ¡Está perfecto!",
                    "Mirá {name}, un poco de entretenimiento nunca viene mal. ¿Qué estás viendo?",
                    "Ey {name}, te merecés un descanso. ¿Encontraste algo bueno?",
                    "Che {name}, está bueno relajarse un toque. ¿Es algo que recomendás?"
                ]
            },
            'work': {
                'keywords': ['word', 'excel', 'powerpoint', 'pdf', 'document', 'spreadsheet'],
                'personality_responses': [
                    "Che {name}, veo que estás con documentos. ¿Es algo pesado o va tranqui?",
                    "Mirá {name}, te veo organizando cosas. ¿Necesitás una mano con algo?",
                    "Ey {name}, estás en modo productivo. ¿Cómo va la cosa?",
                    "Che {name}, veo que estás laburando duro. ¿Todo bajo control?"
                ]
            }
        }
        
        # Cargar historial si existe
        self._load_session_history()
    
    def start_monitoring(self):
        """Inicia el monitoreo analítico."""
        self.is_running = True
        
        # Hilo para monitoreo continuo (silencioso)
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        # Hilo para análisis periódico (cada 10 min)
        analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        analysis_thread.start()
        
        print(f"[Alisha] Che {self.user_name}, acá estoy. Voy a estar observando en silencio y cada tanto te comento algo interesante.")
    
    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.is_running = False
        self._save_session_history()
        print(f"[Alisha] Nos vemos {self.user_name}, cualquier cosa me avisás.")
    
    def _monitor_loop(self):
        """Loop de monitoreo silencioso cada 30 segundos."""
        while self.is_running:
            try:
                self._update_current_activity()
                time.sleep(30)  # Monitoreo cada 30 segundos (silencioso)
            except Exception as e:
                print(f"[Alisha] Error en monitoreo: {e}")
                time.sleep(60)
    
    def _analysis_loop(self):
        """Loop de análisis cada 10 minutos."""
        while self.is_running:
            try:
                time.sleep(self.analysis_interval)  # 10 minutos
                if self.is_running:
                    self._perform_analysis()
            except Exception as e:
                print(f"[Alisha] Error en análisis: {e}")
    
    def _update_current_activity(self):
        """Actualiza la actividad actual sin comentarios."""
        try:
            from screen_vision import obtener_ventana_activa_info
            
            ventana_info = obtener_ventana_activa_info()
            window_title = ventana_info.get("titulo", "").lower()
            process_name = ventana_info.get("proceso", "").lower()
            
            # Detectar tipo de actividad
            activity_type = self._classify_activity(window_title, process_name)
            
            # Gestionar sesiones
            if self.current_session is None:
                # Iniciar nueva sesión
                self.current_session = ActivitySession(
                    activity_type=activity_type,
                    start_time=datetime.now()
                )
                self.current_session.window_titles.append(window_title)
            
            elif self.current_session.activity_type != activity_type:
                # Cambio de actividad - cerrar sesión actual
                self.current_session.end_time = datetime.now()
                self.session_history.append(self.current_session)
                
                # Iniciar nueva sesión
                self.current_session = ActivitySession(
                    activity_type=activity_type,
                    start_time=datetime.now()
                )
                self.current_session.window_titles.append(window_title)
            
            else:
                # Misma actividad - actualizar detalles
                if window_title not in self.current_session.window_titles:
                    self.current_session.window_titles.append(window_title)
            
            # Actualizar expresión facial (silencioso)
            self._update_facial_expression(activity_type)
            
        except Exception as e:
            pass  # Silencioso en caso de error
    
    def _classify_activity(self, window_title: str, process_name: str) -> str:
        """Clasifica la actividad basada en ventana y proceso."""
        combined_text = f"{window_title} {process_name}".lower()
        
        for activity_type, patterns in self.activity_patterns.items():
            for keyword in patterns['keywords']:
                if keyword in combined_text:
                    return activity_type
        
        return 'general'
    
    def _update_facial_expression(self, activity_type: str):
        """Actualiza la expresión facial según la actividad (silencioso)."""
        try:
            # Mapeo de actividades a expresiones
            expression_map = {
                'coding': '疑惑',      # concentración
                'design': '星星眼',    # creatividad
                'research': '疑惑',    # curiosidad
                'communication': '脸红', # social
                'entertainment': '星星眼', # diversión
                'work': '疑惑',        # concentración
                'general': '脸红'      # neutral
            }
            
            expression = expression_map.get(activity_type, '脸红')
            
            # Actualizar estado del chibi (si está disponible)
            try:
                from assistant_state import actualizar_estado, STATE_FILE
                import json as _json
                # Determinar modo_app para Live2D
                modo_app_live2d = ""
                if activity_type == "coding":
                    modo_app_live2d = "programadora"
                elif activity_type == "creative":
                    modo_app_live2d = "creativo"

                actualizar_estado(
                    estado=activity_type,
                    hablando=False,
                    texto="",
                    modo="OBSERVING"
                )
                # Escribir modo_app para que desktop_widget active modo programadora
                if modo_app_live2d:
                    try:
                        _data = _json.loads(STATE_FILE.read_text(encoding="utf-8"))
                        _data["modo_app"] = modo_app_live2d
                        STATE_FILE.write_text(_json.dumps(_data, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
            except Exception:
                pass
                
        except Exception:
            pass
    
    def _perform_analysis(self):
        """Realiza análisis y genera comentario solo si es relevante y no está en cooldown."""
        try:
            # Verificar semáforo global ANTES de analizar
            try:
                from alisha_silencio import puede_hablar_proactivo, ventana_cambio_significativo
                if not puede_hablar_proactivo("analitica"):
                    return
            except Exception:
                pass

            # Filtro de novedad: si la ventana no cambió, no comentar
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                buf  = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                titulo_actual = buf.value.strip()
                from alisha_silencio import ventana_cambio_significativo
                if not ventana_cambio_significativo(titulo_actual):
                    return  # misma ventana → silencio
            except Exception:
                pass

            if self.current_session:
                self.current_session.end_time = datetime.now()
                self.session_history.append(self.current_session)
                self.current_session = None
            
            recent_sessions = self._get_recent_sessions(minutes=10)
            if not recent_sessions:
                return
            
            analysis = self._generate_contextual_analysis(recent_sessions)
            
            if analysis and not self.silence_mode:
                # Validar que la actividad detectada coincide con la ventana activa AHORA
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    buf  = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                    ventana_actual = buf.value.strip().lower()
                    # Si la ventana activa es el chat de Alisha, no comentar
                    if "alisha" in ventana_actual or "localhost:5000" in ventana_actual:
                        return
                    # Si no hay ventana activa relevante, no comentar
                    if not ventana_actual or ventana_actual in ("", "escritorio", "desktop"):
                        return
                except Exception:
                    pass

                self._speak_analysis(analysis)
                # Registrar en semáforo global
                try:
                    from alisha_silencio import registrar_habla_proactivo
                    registrar_habla_proactivo("analitica")
                except Exception:
                    pass
                
            self._save_session_history()
            
        except Exception as e:
            print(f"[Alisha] Error en análisis: {e}")
    
    def _get_recent_sessions(self, minutes: int = 10) -> List[ActivitySession]:
        """Obtiene sesiones de los últimos N minutos."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [s for s in self.session_history if s.start_time >= cutoff_time]
    
    def _generate_contextual_analysis(self, sessions: List[ActivitySession]) -> Optional[str]:
        """Genera análisis contextual humano de las sesiones."""
        if not sessions:
            return None
        
        # Agrupar por tipo de actividad
        activity_summary = {}
        total_time = 0
        
        for session in sessions:
            activity_type = session.activity_type
            duration = session.duration_minutes
            
            if activity_type not in activity_summary:
                activity_summary[activity_type] = {
                    'duration': 0,
                    'sessions': 0,
                    'details': []
                }
            
            activity_summary[activity_type]['duration'] += duration
            activity_summary[activity_type]['sessions'] += 1
            activity_summary[activity_type]['details'].extend(session.window_titles)
            total_time += duration
        
        # Determinar actividad principal
        main_activity = max(activity_summary.keys(), 
                          key=lambda k: activity_summary[k]['duration'])
        main_duration = activity_summary[main_activity]['duration']
        
        # Generar comentario contextual
        return self._create_human_comment(main_activity, main_duration, activity_summary, total_time)
    
    def _create_human_comment(self, main_activity: str, main_duration: float, 
                            activity_summary: Dict, total_time: float) -> Optional[str]:
        """Crea comentario humano con personalidad rioplatense."""
        
        # No comentar si la sesión fue muy corta
        if total_time < 5:  # menos de 5 minutos
            return None
        
        # No comentar actividades muy repetitivas
        if self._is_repetitive_activity(main_activity):
            return None
        
        import random
        
        # Comentarios según contexto
        if main_activity == 'coding' and main_duration > 30:
            comments = [
                f"Che {self.user_name}, llevás {int(main_duration)} minutos programando sin parar. ¿Está saliendo bien o te trabaste en algo jodido?",
                f"Mirá {self.user_name}, te veo muy metida en el código. ¿Querés que revise algo o vas bien encaminada?",
                f"Ey {self.user_name}, {int(main_duration)} minutos de código puro. ¿Es algo complejo o ya le agarraste la mano?"
            ]
        
        elif main_activity == 'design' and main_duration > 20:
            comments = [
                f"Che {self.user_name}, estás hace {int(main_duration)} minutos en modo creativo. ¿Cómo va quedando el diseño?",
                f"Mirá {self.user_name}, te veo inspirada. ¿Es para algún proyecto copado?",
                f"Ey {self.user_name}, llevás un buen rato diseñando. ¿Necesitás una segunda opinión?"
            ]
        
        elif len(activity_summary) > 3:  # Multitasking
            comments = [
                f"Che {self.user_name}, andás saltando entre varias cosas. ¿Todo bajo control o necesitás organizarte?",
                f"Mirá {self.user_name}, te veo haciendo malabares con las tareas. ¿Puedo ayudarte a priorizar algo?",
                f"Ey {self.user_name}, estás en modo multitarea. ¿Cómo andás de tiempo?"
            ]
        
        elif main_activity == 'research' and main_duration > 15:
            comments = [
                f"Che {self.user_name}, llevás {int(main_duration)} minutos investigando. ¿Encontraste lo que buscabas?",
                f"Mirá {self.user_name}, te veo buceando información. ¿Puedo ayudarte a buscar algo específico?",
                f"Ey {self.user_name}, estás en modo exploración. ¿Es para algún proyecto nuevo?"
            ]
        
        elif main_activity == 'work' and main_duration > 25:
            comments = [
                f"Che {self.user_name}, {int(main_duration)} minutos de laburo intenso. ¿Cómo vas con los documentos?",
                f"Mirá {self.user_name}, te veo concentrada en el trabajo. ¿Todo tranqui o hay algo urgente?",
                f"Ey {self.user_name}, llevás un rato organizando cosas. ¿Necesitás una mano?"
            ]
        
        else:
            return None  # No comentar actividades menores
        
        return random.choice(comments) if comments else None
    
    def _is_repetitive_activity(self, activity: str) -> bool:
        """Determina si una actividad es repetitiva y no merece comentario."""
        # Verificar historial reciente para evitar comentarios repetitivos
        recent_comments = getattr(self, '_recent_comments', [])
        return activity in recent_comments[-3:]  # No comentar si fue comentado en las últimas 3 veces
    
    def _speak_analysis(self, analysis: str):
        """Habla el análisis usando AudioVisualSync (semáforo anti-doble-voz)."""
        try:
            print(f"[Alisha] {analysis}")
            try:
                from audio_visual_sync import get_audio_visual_sync
                get_audio_visual_sync().speak(analysis, sarcasm_score=0.0,
                                              emotional_state="curiosidad", async_mode=True)
            except Exception:
                pass
            if not hasattr(self, '_recent_comments'):
                self._recent_comments = []
            self._recent_comments.append(self.current_session.activity_type if self.current_session else 'general')
            if len(self._recent_comments) > 5:
                self._recent_comments.pop(0)
        except Exception as e:
            print(f"[Alisha] Error hablando: {e}")
    
    def _save_session_history(self):
        """Guarda el historial de sesiones."""
        try:
            from config import DATA_DIR
            history_file = DATA_DIR / "alisha_session_history.json"
            data = {
                'sessions': [
                    {
                        'activity_type': s.activity_type,
                        'start_time': s.start_time.isoformat(),
                        'end_time': s.end_time.isoformat() if s.end_time else None,
                        'details': s.details,
                        'window_titles': s.window_titles
                    }
                    for s in self.session_history[-50:]  # Solo últimas 50 sesiones
                ]
            }
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass
    
    def _load_session_history(self):
        """Carga el historial de sesiones."""
        try:
            from config import DATA_DIR
            history_file = DATA_DIR / "alisha_session_history.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for session_data in data.get('sessions', []):
                    session = ActivitySession(
                        activity_type=session_data['activity_type'],
                        start_time=datetime.fromisoformat(session_data['start_time']),
                        end_time=datetime.fromisoformat(session_data['end_time']) if session_data['end_time'] else None,
                        details=session_data.get('details', []),
                        window_titles=session_data.get('window_titles', [])
                    )
                    self.session_history.append(session)
                    
        except Exception:
            pass
    
    def set_silence_mode(self, enabled: bool):
        """Activa/desactiva modo silencio."""
        self.silence_mode = enabled
        status = "activado" if enabled else "desactivado"
        print(f"[Alisha] Modo silencio {status}.")
    
    def force_analysis(self):
        """Fuerza un análisis inmediato."""
        print(f"[Alisha] Dale {self.user_name}, te hago un análisis rápido...")
        self._perform_analysis()

# Instancia global
_alisha_analitica = None

def get_alisha_analitica(user_name: str = "Camila") -> AlishaAnalitica:
    """Obtiene la instancia global de Alisha Analítica."""
    global _alisha_analitica
    if _alisha_analitica is None:
        _alisha_analitica = AlishaAnalitica(user_name)
    return _alisha_analitica

def start_alisha_analitica(user_name: str = "Camila"):
    """Inicia Alisha Analítica."""
    alisha = get_alisha_analitica(user_name)
    alisha.start_monitoring()
    return alisha

def stop_alisha_analitica():
    """Detiene Alisha Analítica."""
    global _alisha_analitica
    if _alisha_analitica:
        _alisha_analitica.stop_monitoring()
        _alisha_analitica = None


# ---------------------------------------------------------------------------
# APM Counter (Actions Per Minute) + Flow State
# ---------------------------------------------------------------------------

class APMCounter:
    """Cuenta pulsaciones de teclado/mouse para detectar Flow State."""

    def __init__(self):
        self._actions = []
        self._lock = threading.Lock()
        self._flow_state = False
        self._last_action_time = time.time()
        self._running = False
        self._listener = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            from pynput import keyboard as _kb, mouse as _ms

            def _on_key(key):
                self._register_action()

            def _on_click(x, y, button, pressed):
                if pressed:
                    self._register_action()

            self._kb_listener = _kb.Listener(on_press=_on_key)
            self._ms_listener = _ms.Listener(on_click=_on_click)
            self._kb_listener.daemon = True
            self._ms_listener.daemon = True
            self._kb_listener.start()
            self._ms_listener.start()

            # Hilo de evaluación de flow state
            threading.Thread(target=self._eval_loop, daemon=True).start()
        except Exception:
            pass

    def _register_action(self) -> None:
        now = time.time()
        with self._lock:
            self._actions.append(now)
            self._last_action_time = now
            # Limpiar acciones de más de 60s
            self._actions = [t for t in self._actions if now - t < 60]

    def get_apm(self) -> int:
        now = time.time()
        with self._lock:
            return len([t for t in self._actions if now - t < 60])

    def is_flow(self) -> bool:
        return self._flow_state

    def seconds_since_last_action(self) -> float:
        return time.time() - self._last_action_time

    def _eval_loop(self) -> None:
        while self._running:
            apm = self.get_apm()
            # Flow state: más de 20 APM sostenidos
            self._flow_state = apm > 20
            # Escribir en chibi_state para que Live2D reaccione
            try:
                from assistant_state import STATE_FILE
                import json as _json
                data = _json.loads(STATE_FILE.read_text(encoding="utf-8"))
                data["flow_state"] = self._flow_state
                data["apm"] = apm
                STATE_FILE.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            time.sleep(5)


# ---------------------------------------------------------------------------
# Beat Detection (Spotify / YouTube)
# ---------------------------------------------------------------------------

class BeatDetector:
    """Detecta si hay música activa y mueve la cabeza de Alisha rítmicamente."""

    _MUSIC_APPS = {"spotify.exe", "chrome.exe", "msedge.exe", "firefox.exe"}
    _MUSIC_TITLES = {"spotify", "youtube", "soundcloud", "deezer", "tidal"}

    def __init__(self):
        self._running = False
        self._beat_active = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._detect_loop, daemon=True).start()

    def _detect_loop(self) -> None:
        import random
        while self._running:
            try:
                music_active = self._check_music_active()
                if music_active != self._beat_active:
                    self._beat_active = music_active
                    self._emit_beat_state(music_active)

                if music_active:
                    # Simular beat: mover cabeza cada ~0.5s (120 BPM aprox)
                    angle = random.uniform(-3, 3)
                    self._emit_head_angle(angle)
                    time.sleep(0.5)
                else:
                    time.sleep(3)
            except Exception:
                time.sleep(5)

    def _check_music_active(self) -> bool:
        try:
            import psutil
            for proc in psutil.process_iter(["name", "status"]):
                name = proc.info.get("name", "").lower()
                if name in self._MUSIC_APPS:
                    # Verificar si el título de la ventana menciona música
                    try:
                        import win32gui
                        def _check(hwnd, _):
                            if win32gui.IsWindowVisible(hwnd):
                                title = win32gui.GetWindowText(hwnd).lower()
                                for kw in self._MUSIC_TITLES:
                                    if kw in title:
                                        return True
                            return False
                        # Simplificado: si Spotify está corriendo, asumir música
                        if name == "spotify.exe":
                            return True
                    except Exception:
                        if name == "spotify.exe":
                            return True
        except Exception:
            pass
        return False

    def _emit_beat_state(self, active: bool) -> None:
        try:
            from assistant_state import STATE_FILE
            import json as _json
            data = _json.loads(STATE_FILE.read_text(encoding="utf-8"))
            data["beat_active"] = active
            STATE_FILE.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _emit_head_angle(self, angle: float) -> None:
        try:
            from assistant_state import STATE_FILE
            import json as _json
            data = _json.loads(STATE_FILE.read_text(encoding="utf-8"))
            data["beat_angle"] = angle
            STATE_FILE.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# Singletons
_apm_counter = APMCounter()
_beat_detector = BeatDetector()


def get_apm_counter() -> APMCounter:
    return _apm_counter


def get_beat_detector() -> BeatDetector:
    return _beat_detector


def iniciar_monitores_extra() -> None:
    """Inicia APM counter y beat detector."""
    _apm_counter.start()
    _beat_detector.start()
