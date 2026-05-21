"""
desktop_widget.py — Alisha Completa: Personaje Live2D + IA + Web integrados.
"""
import argparse
import ctypes
import ctypes.wintypes
import json
import math
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── Forzar UTF-8 en stdout/stderr para soportar emojis en Windows ─────────────
import os as _os_enc
_os_enc.environ.setdefault("PYTHONIOENCODING", "utf-8")
import sys as _sys_enc
if _sys_enc.stdout is not None:
    try:
        _sys_enc.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if _sys_enc.stderr is not None:
    try:
        _sys_enc.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Configurar DPI de forma segura antes de importar Qt
try:
    # Configuración DPI más compatible
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QT_SCALE_FACTOR'] = '1'
    os.environ['QT_SCREEN_SCALE_FACTORS'] = '1'
    os.environ['QT_DEVICE_PIXEL_RATIO'] = '1'
except Exception:
    pass

import pyautogui
from config import LIVE2D_MODEL_PATH

# Lectura pasiva del mouse — sin hooks que bloqueen otros programas
try:
    from pynput import mouse as _pynput_mouse
    from pynput import keyboard as _pynput_keyboard
    _PYNPUT_OK = True
except ImportError:
    _PYNPUT_OK = False

# Importar Qt con manejo de errores
try:
    from PyQt6.QtCore import (
        Qt, QTimer, QUrl, pyqtSlot, QObject, pyqtSignal
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtWebChannel import QWebChannel
except ImportError as e:
    print(f"❌ Error importando PyQt6: {e}")
    print("💡 Instala PyQt6 con: pip install PyQt6 PyQt6-WebEngine")
    input("Presiona Enter para cerrar...")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

MODEL_FILE = Path(LIVE2D_MODEL_PATH)
from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# Mapeo emociones IA → expresiones del modelo IceGirl
EMOTION_TO_EXPRESSION = {
    "alegría":      "脸红",      # rubor/alegría
    "entusiasmo":   "星星眼",    # ojos de estrella
    "curiosidad":   "疑惑",      # duda/curiosidad
    "preocupación": "流泪",      # lágrimas
    "frustración":  "生气",      # enojo
    "nostalgia":    "流泪",      # lágrimas
    "cansancio":    "白眼",      # ojos en blanco
    "neutral":      None,        # expresión por defecto
    
    # Expresiones adicionales para reacciones
    "susto":        "惊讶",      # sorpresa/susto
    "enojo":        "生气",      # enojo
    "fastidio":     "白眼",      # ojos en blanco (fastidio)
    "concentracion": "疑惑",     # concentración
    "diversion":    "星星眼",    # diversión
    "sociable":     "脸红",      # sociable/tímida
}

# Tamaño y posición del widget — calculado dinámicamente según la resolución real
import ctypes as _ctypes
def _get_screen_size():
    """Obtiene el tamaño real de la pantalla respetando el DPI scaling de Qt."""
    try:
        # Usar Qt para obtener la geometría real (respeta DPI scaling)
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QScreen
        import sys as _sys
        _app = QApplication.instance() or QApplication(_sys.argv)
        screen = _app.primaryScreen()
        geom = screen.availableGeometry()  # excluye barra de tareas
        return geom.width(), geom.height()
    except Exception:
        pass
    try:
        # Fallback: Win32 con DPI awareness
        _ctypes.windll.user32.SetProcessDPIAware()
        w = _ctypes.windll.user32.GetSystemMetrics(0)
        h = _ctypes.windll.user32.GetSystemMetrics(1)
        return w, h
    except Exception:
        return 1920, 1080

_SW, _SH = _get_screen_size()
WIDGET_W = 380
WIDGET_H = 570
WIDGET_X = max(0, _SW - WIDGET_W - 15)   # esquina derecha, margen 15px
WIDGET_Y = max(0, _SH - WIDGET_H - 10)   # justo sobre la barra de tareas

# Configuración de seguimiento de mouse
MOUSE_TRACKING_ENABLED = True
MAX_EYE_OFFSET = 15      # máximo desplazamiento de ojos en píxeles
MAX_HEAD_TILT = 10       # máximo inclinación de cabeza en grados
SMOOTHING_FACTOR = 0.15  # factor de interpolación suave (0.1 = muy suave, 1.0 = inmediato)
MOUSE_POLL_RATE = 60     # Hz - frecuencia de lectura del mouse

# ---------------------------------------------------------------------------
# Seguimiento de Mouse
# ---------------------------------------------------------------------------

class MouseTracker(QObject):
    """Rastrea el mouse y calcula el offset para que el personaje siga la mirada."""
    
    mousePositionChanged = pyqtSignal(float, float)  # offset_x, offset_y
    mouseClicked = pyqtSignal(int)  # número de clics consecutivos
    
    def __init__(self, widget_x: int, widget_y: int, widget_w: int, widget_h: int):
        super().__init__()
        self.widget_x = widget_x
        self.widget_y = widget_y
        self.widget_w = widget_w
        self.widget_h = widget_h
        
        # Centro del personaje (donde están los ojos aproximadamente)
        self.center_x = widget_x + widget_w // 2
        self.center_y = widget_y + widget_h // 3  # ojos están en el tercio superior
        
        # Estado actual
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.last_click_state = False
        
        # Contador de clics consecutivos
        self.click_count = 0
        self.last_click_time = 0
        self.click_reset_delay = 3.0  # segundos para resetear contador
        
        # Hilo de seguimiento
        self._running = False
        self._thread = None
        
    def start_tracking(self):
        """Inicia el hilo de seguimiento y el listener pasivo de clics."""
        if self._running:
            return
        self._running = True

        # Listener pasivo de clics (pynput) — no bloquea otras apps
        if _PYNPUT_OK:
            def _on_click(x, y, button, pressed):
                if button == _pynput_mouse.Button.left and pressed:
                    current_time = time.time()
                    if current_time - self.last_click_time < self.click_reset_delay:
                        self.click_count += 1
                    else:
                        self.click_count = 1
                    self.last_click_time = current_time
                    self.mouseClicked.emit(self.click_count)

            self._click_listener = _pynput_mouse.Listener(on_click=_on_click)
            self._click_listener.start()

        self._thread = threading.Thread(target=self._track_loop, daemon=True)
        self._thread.start()

    def stop_tracking(self):
        """Detiene el seguimiento."""
        self._running = False
        if _PYNPUT_OK and hasattr(self, '_click_listener'):
            try:
                self._click_listener.stop()
            except Exception:
                pass

    def _track_loop(self):
        """Loop de seguimiento — lectura PASIVA de posición, sin hooks que bloqueen."""
        while self._running:
            try:
                # Lectura pasiva de posición (no instala hooks)
                mouse_x, mouse_y = pyautogui.position()

                current_time = time.time()
                # Resetear contador si pasó mucho tiempo sin clic
                if current_time - self.last_click_time > self.click_reset_delay:
                    self.click_count = 0

                # Calcular offset de mirada
                diff_x = mouse_x - self.center_x
                diff_y = mouse_y - self.center_y

                distance = math.sqrt(diff_x**2 + diff_y**2)
                if distance > 0:
                    norm_x = diff_x / distance
                    norm_y = diff_y / distance
                    max_distance = min(distance, 200)
                    intensity = min(max_distance / 200, 1.0)
                    target_offset_x = norm_x * MAX_EYE_OFFSET * intensity
                    target_offset_y = norm_y * MAX_EYE_OFFSET * intensity
                else:
                    target_offset_x = 0.0
                    target_offset_y = 0.0

                # Interpolación suave (lerp)
                self.current_offset_x += (target_offset_x - self.current_offset_x) * SMOOTHING_FACTOR
                self.current_offset_y += (target_offset_y - self.current_offset_y) * SMOOTHING_FACTOR

                self.mousePositionChanged.emit(self.current_offset_x, self.current_offset_y)

                # Sleep explícito — 60 FPS, no consume CPU al 100%
                time.sleep(1.0 / MOUSE_POLL_RATE)

            except Exception:
                time.sleep(0.05)


# ---------------------------------------------------------------------------
# Bridge Python ↔ JavaScript
# ---------------------------------------------------------------------------

class Live2DBridge(QObject):
    """Objeto expuesto al JavaScript para comunicación bidireccional."""

    modelReady = pyqtSignal()
    modelError = pyqtSignal(str)

    def __init__(self, view: QWebEngineView):
        super().__init__()
        self._view = view
        self._ready = False

    @pyqtSlot(str)
    def onMessage(self, msg: str) -> None:
        if msg == "ready":
            self._ready = True
            self.modelReady.emit()
            print("[Live2D] ✓ Modelo cargado y listo")
        elif msg == "woke_up":
            self.modelReady.emit()
            print("[Live2D] ✓ Secuencia de despertar completada")
        elif msg.startswith("error:"):
            self.modelError.emit(msg[6:])
            print(f"[Live2D] Error JS: {msg[6:]}")
        elif msg.startswith("warn:"):
            print(f"[Live2D] Warn JS: {msg[5:]}")
        elif msg.startswith("log:"):
            print(f"[Live2D] JS: {msg[4:]}")

    def set_expression(self, emocion: str) -> None:
        if not self._ready:
            return
        expr = EMOTION_TO_EXPRESSION.get(emocion)
        if expr:
            self._view.page().runJavaScript(
                f'window.live2dControl.setExpression("{expr}")'
            )
        else:
            # Resetear expresión
            self._view.page().runJavaScript(
                'window.live2dControl.setExpression("default")'
            )

    def set_hablando(self, hablando: bool) -> None:
        if not self._ready:
            return
        val = "true" if hablando else "false"
        self._view.page().runJavaScript(
            f'window.live2dControl.setHablando({val})'
        )

    def set_motion(self, grupo: str) -> None:
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setMotion("{grupo}")'
        )
    
    def set_eye_offset(self, offset_x: float, offset_y: float) -> None:
        """Ajusta la dirección de la mirada del modelo."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setEyeOffset({offset_x}, {offset_y})'
        )
    
    def set_head_tilt(self, angle: float) -> None:
        """Inclina ligeramente la cabeza del modelo."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setHeadTilt({angle})'
        )
    
    def trigger_blink(self) -> None:
        """Activa un parpadeo rápido."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            'window.live2dControl.triggerBlink()'
        )

    def set_sarcasm_level(self, nivel: int) -> None:
        """Mapea nivel de sarcasmo (0-3) a cejas y boca del modelo."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setSarcasmLevel({int(nivel)})'
        )

    def set_dopamina_adjust(self, ajuste: float) -> None:
        """Mapea ajuste de dopamina (+0.15/-0.10) a brillo y respiración."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setDopaminaAdjust({float(ajuste)})'
        )

    def set_modo_creativo(self) -> None:
        """Activa expresión de asombro creativo (Photoshop)."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            'window.live2dControl.setModoCreativo()'
        )

    def set_modo_cv_noche(self) -> None:
        """Activa expresión de preocupación empática (CV nocturno)."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            'window.live2dControl.setModoCVNoche()'
        )

    def set_iris_color(self, r: float, g: float, b: float, duration_ms: int = 1200) -> None:
        """Cambia el color multiplicador del iris. r,g,b en 0.0-1.0. Transición suave."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setIrisColor({r}, {g}, {b}, {duration_ms})'
        )

    def set_eye_brightness(self, opacity: float, duration_ms: int = 600) -> None:
        """Controla el brillo/opacidad del highlight de los ojos. 0.0=apagado, 1.0=radiante."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setEyeBrightness({opacity}, {duration_ms})'
        )

    def set_tool_animation(self, active: bool) -> None:
        """Activa/desactiva la animación de 'leyendo/buscando' (ojos moviéndose rápido)."""
        if not self._ready:
            return
        val = "true" if active else "false"
        self._view.page().runJavaScript(
            f'window.live2dControl.setToolAnimation({val})'
        )

    def set_programmer_mode(self, active: bool) -> None:
        """Activa/desactiva el modo programadora (luz azul + anteojos + concentración)."""
        if not self._ready:
            return
        val = "true" if active else "false"
        self._view.page().runJavaScript(
            f'window.live2dControl.setProgrammerMode({val})'
        )

    def set_mouth_amplitude(self, amplitude: float) -> None:
        """Actualiza la amplitud de boca para lip-sync real."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            f'window.live2dControl.setMouthAmplitude({amplitude})'
        )

    def start_dance_mode(self) -> None:
        """Activa la animación de baile fluida."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            'window.live2dControl.startDanceMode()'
        )

    def stop_dance_mode(self) -> None:
        """Desactiva la animación de baile y vuelve al idle."""
        if not self._ready:
            return
        self._view.page().runJavaScript(
            'window.live2dControl.stopDanceMode()'
        )


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class DesktopWidget(QMainWindow):

    def __init__(self, model_path: Path):
        super().__init__()
        self._model_path = model_path
        self._setup_window()
        self._setup_webview()
        self._setup_state_watcher()
        self._setup_mouse_tracking()
        self._setup_integrated_systems()

    def _setup_integrated_systems(self) -> None:
        """Inicia los sistemas integrados: servidor web y motor de IA."""
        print("[Alisha] Iniciando sistemas integrados...")
        
        # Iniciar servidor web en hilo separado
        self._start_web_server()
        
        # Iniciar motor de IA en hilo separado
        self._start_ia_engine()
        
        # Abrir navegador después de un momento
        QTimer.singleShot(3000, self._open_browser)
        
    def _start_web_server(self) -> None:
        """Inicia el servidor web Flask en un hilo separado."""
        def run_web_server():
            try:
                # Verificar si el puerto ya está en uso
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('localhost', 5000))
                    if result == 0:
                        print("[Alisha] ✓ Servidor web ya está ejecutándose en puerto 5000")
                        return
                
                # Importar y ejecutar la aplicación web directamente
                from web_app import app, socketio, _inicializar
                _inicializar()
                
                # Ejecutar en hilo separado
                socketio.run(app, host="127.0.0.1", port=5000, debug=False, 
                           allow_unsafe_werkzeug=True, use_reloader=False)
                print("[Alisha] ✓ Servidor web iniciado")
            except Exception as e:
                print(f"[Alisha] Error iniciando servidor web: {e}")
        
        threading.Thread(target=run_web_server, daemon=True).start()
        
    def _start_ia_engine(self) -> None:
        """Inicia el motor de IA en un hilo separado."""
        def run_ia_engine():
            try:
                # Verificar si ya hay una instancia ejecutándose
                import socket
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        result = s.connect_ex(('localhost', 11434))
                        if result != 0:
                            print("[Alisha] ⚠️ Ollama no está ejecutándose en puerto 11434")
                            return
                except Exception:
                    pass
                
                # El motor de IA se ejecuta a través de la web app, no necesita proceso separado
                print("[Alisha] ✓ Motor de IA integrado")
            except Exception as e:
                print(f"[Alisha] Error verificando motor de IA: {e}")
        
        threading.Thread(target=run_ia_engine, daemon=True).start()
        
    def _open_browser(self) -> None:
        """Abre el navegador con la interfaz web."""
        try:
            webbrowser.open("http://localhost:5000")
            print("[Alisha] ✓ Navegador abierto")
        except Exception as e:
            print(f"[Alisha] Error abriendo navegador: {e}")

    def _setup_window(self) -> None:
        """Configura la ventana: sin bordes, transparente, siempre encima SIN robar foco."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint       |
            Qt.WindowType.WindowStaysOnTopHint      |
            Qt.WindowType.Tool                      |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowOpacity(1.0)

        # Calcular posición usando Qt (respeta DPI scaling correctamente)
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            avail = screen.availableGeometry()
            x = avail.x() + avail.width()  - WIDGET_W - 15
            y = avail.y() + avail.height() - WIDGET_H - 10
            x = max(avail.x(), x)
            y = max(avail.y(), y)
        except Exception:
            x, y = WIDGET_X, WIDGET_Y

        self.setGeometry(x, y, WIDGET_W, WIDGET_H)
        self.setStyleSheet("background: transparent;")
        print(f"[Live2D] Ventana posicionada en ({x}, {y}) tamaño {WIDGET_W}x{WIDGET_H}")

    def _setup_webview(self) -> None:
        """Configura el WebView con el modelo Live2D."""
        self._view = QWebEngineView(self)
        self._view.setGeometry(0, 0, WIDGET_W, WIDGET_H)
        self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._view.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # ← no activa
        self._view.setFocusPolicy(Qt.FocusPolicy.NoFocus)                      # ← sin foco
        self._view.setStyleSheet("background: transparent;")

        # Fondo transparente en la página web
        page = self._view.page()
        page.setBackgroundColor(Qt.GlobalColor.transparent)

        # WebChannel para comunicación Python ↔ JS
        self._channel = QWebChannel()
        self._bridge = Live2DBridge(self._view)
        self._channel.registerObject("pyBridge", self._bridge)
        page.setWebChannel(self._channel)

        self._bridge.modelReady.connect(self._on_model_ready)
        self._bridge.modelError.connect(self._on_model_error)

        # Inyectar qwebchannel.js cuando la página cargue
        self._view.loadFinished.connect(self._on_load_finished)

        # Cargar el HTML después de que el servidor web esté listo (5s)
        QTimer.singleShot(5000, self._load_html)

    def _on_load_finished(self, ok: bool) -> None:
        """Inyecta el script de WebChannel después de que la página cargó."""
        if not ok:
            print("[Live2D] Error: página no cargó correctamente")
            return
        # Inyectar qwebchannel.js desde qrc y luego inicializar el canal
        self._view.page().runJavaScript("""
            (function() {
                var s = document.createElement('script');
                s.src = 'qrc:///qtwebchannel/qwebchannel.js';
                s.onload = function() {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.pyBridge = channel.objects.pyBridge;
                        if (window._startLive2D) window._startLive2D();
                    });
                };
                s.onerror = function() {
                    // qrc no disponible — intentar sin WebChannel
                    if (window._startLive2D) window._startLive2D();
                };
                document.head.appendChild(s);
            })();
        """)

    def _load_html(self) -> None:
        """Genera y carga el HTML con la ruta del modelo."""
        # Leer expresiones disponibles
        expressions = {}
        for f in self._model_path.parent.glob("*.exp3.json"):
            nombre = f.stem.replace(".exp3", "")
            expressions[nombre] = f.name

        template_path = Path("templates/live2d_viewer.html")
        if not template_path.exists():
            print(f"[Live2D] No se encontró {template_path}")
            return

        html = template_path.read_text(encoding="utf-8")

        # Servir el modelo via servidor HTTP local para evitar CORS
        model_dir = str(self._model_path.parent).replace("\\", "/")
        model_name = self._model_path.name

        # Iniciar servidor HTTP simple para los assets del modelo
        port = self._iniciar_servidor_modelo()
        model_url = f"http://localhost:{port}/{model_name}"

        html = html.replace("MODEL_PATH_PLACEHOLDER", model_url)
        html = html.replace("EXPRESSIONS_PLACEHOLDER",
                            json.dumps(expressions, ensure_ascii=False))

        # Cargar desde el servidor del modelo (8765) — siempre disponible
        # Los JS de Live2D también se sirven desde ahí via /static/js/live2d/
        base_url = QUrl(f"http://localhost:{port}/")
        self._view.setHtml(html, base_url)

    def _iniciar_servidor_modelo(self, port: int = 8765) -> int:
        """Inicia un servidor HTTP que sirve el modelo Live2D y los JS estáticos."""
        import http.server
        import threading
        import socket
        import os
        from pathlib import Path as _Path

        model_dir = str(self._model_path.parent)
        project_dir = str(_Path(__file__).parent)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=model_dir, **kwargs)

            def do_GET(self):
                # Servir /static/js/live2d/* desde el directorio del proyecto
                if self.path.startswith("/static/"):
                    rel = self.path.lstrip("/")
                    full = os.path.join(project_dir, rel)
                    if os.path.isfile(full):
                        try:
                            with open(full, "rb") as f:
                                data = f.read()
                            self.send_response(200)
                            if full.endswith(".js"):
                                self.send_header("Content-Type", "application/javascript")
                            self.send_header("Content-Length", str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                            return
                        except Exception:
                            pass
                super().do_GET()

            def log_message(self, format, *args):
                pass  # silenciar logs

        # Verificar si el puerto ya está en uso
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            already_running = s.connect_ex(("localhost", port)) == 0

        if not already_running:
            def _run():
                try:
                    server = http.server.HTTPServer(("localhost", port), Handler)
                    server.serve_forever()
                except OSError:
                    pass  # puerto ya en uso

            t = threading.Thread(target=_run, daemon=True)
            t.start()

            # Esperar hasta que el servidor esté realmente listo (máx 3s)
            deadline = time.time() + 3.0
            while time.time() < deadline:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        if s.connect_ex(("localhost", port)) == 0:
                            break
                except Exception:
                    pass
                time.sleep(0.05)

        return port

    def _on_model_ready(self) -> None:
        print("[Live2D] Modelo listo — iniciando secuencia de despertar")
        # Restaurar la última pose guardada (persistencia entre sesiones)
        QTimer.singleShot(500, self._restaurar_pose_inicial)
        # La secuencia de despertar se dispara desde JS automáticamente (3s)
        # Conectar el evento woke_up para el saludo inicial
        if MOUSE_TRACKING_ENABLED and hasattr(self, '_mouse_tracker'):
            self._mouse_tracker.start_tracking()
            print("[Live2D] ✓ Seguimiento de mouse activado")

    def _on_woke_up(self) -> None:
        """Callback cuando Alisha termina de despertar — emite saludo inicial."""
        print("[Live2D] ✓ Alisha despertó")
        QTimer.singleShot(800, self._emitir_saludo_inicial)

    def _emitir_saludo_inicial(self) -> None:
        """Genera el saludo inicial según hora y estado de ia_recuerdos.json."""
        try:
            from datetime import datetime
            import json as _json
            hora = datetime.now().hour
            recuerdos = {}
            try:
                recuerdos = _json.loads((DATA_DIR / "ia_recuerdos.json").read_text(encoding="utf-8"))
            except Exception:
                pass

            contradicciones = recuerdos.get("escepticismo", {}).get(
                "contradicciones_ultima_sesion", 0
            )
            nivel_sk_anterior = recuerdos.get("ultima_pose_fisica", {}).get(
                "nivel_sarcasmo", 0
            )

            # Elegir saludo según hora y contexto
            if 5 <= hora < 12:
                if hora < 8:
                    saludo = "Buen día, Camila... ¿otra vez madrugando o todavía no te acostaste?"
                else:
                    saludo = f"Buen día. Son las {hora}:00 — hora de arrancar."
            elif 12 <= hora < 19:
                saludo = "Buenas tardes. ¿En qué andamos hoy?"
            elif 19 <= hora < 23:
                saludo = "Buenas noches. ¿Trabajando tarde otra vez?"
            else:
                saludo = "Che... son las " + str(hora) + " de la noche. ¿Todo bien?"

            # Si hay muchas contradicciones, mirada de sospecha desde el inicio
            if contradicciones >= 3 or nivel_sk_anterior >= 2:
                self._bridge.set_sarcasm_level(min(nivel_sk_anterior, 2))
                saludo += " (Y sí, me acuerdo de todo lo de ayer.)"

            # Escribir en chibi_state para que la web app lo muestre
            from assistant_state import actualizar_estado
            actualizar_estado(estado="curiosidad", hablando=True, texto=saludo)

            # Hablar el saludo
            try:
                from tts_engine import speak
                speak(saludo)
            except Exception:
                pass

            print(f"[Alisha] {saludo}")
        except Exception as e:
            print(f"[Alisha] Error en saludo inicial: {e}")
    def _on_model_error(self, error: str) -> None:
        print(f"[Live2D] Error cargando modelo: {error}")
        print("  Verificá que la ruta del modelo sea correcta")

    def _setup_mouse_tracking(self) -> None:
        """Configura el seguimiento de mouse para que el personaje siga la mirada."""
        if not MOUSE_TRACKING_ENABLED:
            return

        self._click_through_active = False   # arranca en modo interactivo (visible)
        self._mouse_tracker = MouseTracker(WIDGET_X, WIDGET_Y, WIDGET_W, WIDGET_H)
        self._mouse_tracker.mousePositionChanged.connect(self._on_mouse_position_changed)
        self._mouse_tracker.mouseClicked.connect(self._on_mouse_clicked)
        self._mouse_tracker.start_tracking()
        print("[Live2D] ✓ Seguimiento de mouse activado (lectura pasiva)")

        # Hotkey global Ctrl+Shift+L — toggle click-through
        if _PYNPUT_OK:
            self._setup_global_hotkey()

        # Timer topmost — SIN robar foco
        self._topmost_timer = QTimer()
        self._topmost_timer.timeout.connect(self._ensure_topmost)
        self._topmost_timer.start(2000)

    def _setup_global_hotkey(self) -> None:
        """Registra Ctrl+Shift+L como hotkey global para toggle del click-through."""
        _pressed = set()

        def _on_press(key):
            _pressed.add(key)
            ctrl  = _pynput_keyboard.Key.ctrl_l  in _pressed or \
                    _pynput_keyboard.Key.ctrl_r  in _pressed
            shift = _pynput_keyboard.Key.shift   in _pressed or \
                    _pynput_keyboard.Key.shift_r in _pressed
            try:
                char = key.char
            except AttributeError:
                char = None
            if ctrl and shift and char == 'l':
                self._toggle_click_through()

        def _on_release(key):
            _pressed.discard(key)

        listener = _pynput_keyboard.Listener(
            on_press=_on_press, on_release=_on_release
        )
        listener.daemon = True
        listener.start()
        print("[Alisha] ✓ Hotkey Ctrl+Shift+L registrado (toggle interacción)")

    def _toggle_click_through(self) -> None:
        """Alterna entre modo observador (click-through) e interactivo."""
        self._click_through_active = not self._click_through_active
        if self._click_through_active:
            self.enable_click_through()
            print("[Alisha] Modo observador — clics pasan a otras apps")
        else:
            self.disable_click_through()
            print("[Alisha] Modo interactivo — podés hacer clic en Alisha")
        
    def _on_mouse_position_changed(self, offset_x: float, offset_y: float) -> None:
        """Callback cuando cambia la posición del mouse."""
        # Actualizar dirección de la mirada
        self._bridge.set_eye_offset(offset_x, offset_y)
        
        # Calcular inclinación sutil de la cabeza basada en la posición horizontal
        head_tilt = (offset_x / MAX_EYE_OFFSET) * MAX_HEAD_TILT
        self._bridge.set_head_tilt(head_tilt)
        
    def _on_mouse_clicked(self, click_count: int) -> None:
        """Callback cuando se hace clic con el mouse - reacciones según número de clics."""
        print(f"[Live2D] Clic detectado #{click_count}")
        
        # Obtener estado emocional actual
        current_emotion = self._last_estado
        
        if click_count == 1:
            # Primer clic: susto/sorpresa
            self._bridge.set_expression("惊讶")  # sorpresa
            self._bridge.set_motion("Surprised")
            self._bridge.trigger_blink()
            print("[Live2D] Reacción: ¡Susto!")
            
        elif click_count == 2:
            # Segundo clic: curiosidad
            self._bridge.set_expression("疑惑")  # curiosidad
            self._bridge.set_motion("Idle")
            print("[Live2D] Reacción: Curiosidad")
            
        elif click_count >= 3:
            # Tercer clic o más: enojo (según estado emocional)
            if current_emotion in ("frustración", "preocupación"):
                self._bridge.set_expression("生气")  # enojo
                self._bridge.set_motion("Angry")
                print("[Live2D] Reacción: ¡Enojo!")
            else:
                self._bridge.set_expression("白眼")  # ojos en blanco (fastidio)
                self._bridge.set_motion("Idle")
                print("[Live2D] Reacción: Fastidio")
        
        # Volver al estado normal después de 3 segundos
        QTimer.singleShot(3000, self._restore_normal_expression)
    
    def _restore_normal_expression(self) -> None:
        """Restaura la expresión normal después de una reacción."""
        self._bridge.set_expression(self._last_estado)
        if self._last_estado in ("alegría", "entusiasmo"):
            self._bridge.set_motion("Happy")
        elif self._last_estado in ("preocupación", "frustración"):
            self._bridge.set_motion("Sad")
        else:
            self._bridge.set_motion("Idle")
    
    def _ensure_topmost(self) -> None:
        """Mantiene la ventana visualmente al frente SIN robar el foco del teclado."""
        try:
            hwnd = int(self.winId())
            HWND_TOPMOST  = -1
            SWP_NOMOVE    = 0x0002
            SWP_NOSIZE    = 0x0001
            SWP_NOACTIVATE = 0x0010   # ← clave: no activa ni roba foco
            SWP_NOSENDCHANGING = 0x0400

            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOSENDCHANGING
            )
        except Exception:
            pass

    def _setup_state_watcher(self) -> None:
        """Observa el archivo de estado para reaccionar a las emociones de la IA."""
        self._last_estado = "neutral"
        self._last_hablando = False
        self._last_modo = "IDLE"
        self._last_interaccion = time.time()
        self._idle_timer_count = 0

        self._timer = QTimer()
        self._timer.timeout.connect(self._check_state)
        self._timer.start(300)

        # Timer para animaciones idle aleatorias (cuna virtual)
        self._idle_timer = QTimer()
        self._idle_timer.timeout.connect(self._idle_animation)
        self._idle_timer.start(8000)  # cada 8 segundos
        
        # Timer para observación de pantalla (ahora usa sistema analítico)
        from alisha_analitica import start_alisha_analitica
        
        # Iniciar sistema analítico en lugar del observador simple
        try:
            # Obtener nombre del usuario desde memoria
            user_name = "Camila"  # Por defecto
            try:
                from memory import cargar_memoria
                memoria = cargar_memoria()
                user_name = memoria.get("perfil", {}).get("nombre", "Camila")
            except Exception:
                pass
            
            # Iniciar Alisha Analítica
            self._alisha_analitica = start_alisha_analitica(user_name)
            print(f"[Live2D] ✓ Sistema analítico iniciado para {user_name}")
            
        except Exception as e:
            print(f"[Live2D] Error iniciando sistema analítico: {e}")
            # Fallback al sistema anterior si falla
            self._screen_timer = QTimer()
            self._screen_timer.timeout.connect(self._observe_screen_fallback)
            self._screen_timer.start(300000)  # 5 minutos como fallback

    def _idle_animation(self) -> None:
        """Animaciones espontáneas cuando no hay conversación activa."""
        import random
        tiempo_sin_hablar = time.time() - self._last_interaccion

        # Solo si lleva más de 30 segundos sin interacción
        if tiempo_sin_hablar < 30:
            return

        self._idle_timer_count += 1
        acciones = [
            lambda: self._bridge.set_motion("Idle"),
            lambda: self._bridge.set_expression("疑惑"),   # curiosidad
            lambda: self._bridge.set_expression("脸红"),   # rubor suave
            lambda: self._bridge.set_motion("Idle"),
            lambda: self._bridge.set_expression(None),     # resetear
        ]
        # Elegir acción aleatoria
        random.choice(acciones)()

        # Cada 5 ciclos idle, resetear expresión
        if self._idle_timer_count % 5 == 0:
            self._bridge.set_expression("default")

    def _check_state(self) -> None:
        """Lee el estado de la IA y actualiza el modelo."""
        try:
            if not STATE_FILE.exists():
                return
            with open(STATE_FILE, "r") as f:
                data = json.load(f)

            estado   = data.get("estado", "neutral")
            hablando = data.get("hablando", False)

            if hablando:
                self._last_interaccion = time.time()

            if estado != self._last_estado:
                self._last_estado = estado
                self._bridge.set_expression(estado)
                if estado in ("alegría", "entusiasmo"):
                    self._bridge.set_motion("Happy")
                elif estado in ("preocupación", "frustración"):
                    self._bridge.set_motion("Sad")
                else:
                    self._bridge.set_motion("Idle")

            modo = data.get("modo", "IDLE")
            if modo != self._last_modo:
                self._last_modo = modo
                if modo == "OVERLOADED":
                    self._bridge.set_motion("Sad")
                else:
                    self._bridge.set_motion("Idle")

            if hablando != self._last_hablando:
                self._last_hablando = hablando
                self._bridge.set_hablando(hablando)

            # ── Lip-sync real: amplitud de boca desde TTS ────────────────
            mouth_amp = float(data.get("mouth_amplitude", 0.0))
            if abs(mouth_amp - getattr(self, "_last_mouth_amp", 0.0)) > 0.02:
                self._last_mouth_amp = mouth_amp
                self._bridge.set_mouth_amplitude(mouth_amp)

            # ── Feedback visual cuando una herramienta está corriendo ─────
            tool_running = data.get("tool_running", False)
            if tool_running != getattr(self, "_last_tool_running", False):
                self._last_tool_running = tool_running
                if tool_running:
                    # Activar animación de "leyendo/buscando": ojos moviéndose
                    self._start_tool_animation()
                else:
                    self._stop_tool_animation()

            # ── Escepticismo → parámetros Live2D ─────────────────────────
            nivel_sk = int(data.get("nivel_sarcasmo", 0))
            if nivel_sk != getattr(self, "_last_nivel_sk", -1):
                self._last_nivel_sk = nivel_sk
                # setSarcasmLevel ya maneja color de iris y brillo internamente
                self._bridge.set_sarcasm_level(nivel_sk)
                # Si hay contradicción (nivel > 0), interrumpir Idle con pose de alerta
                if nivel_sk > 0:
                    self._bridge.set_motion("Idle")  # interrumpe animación actual
                    self._bridge.set_expression("疑惑" if nivel_sk == 1 else "生气")

            ajuste_dop = float(data.get("ajuste_dopamina", 0.0))
            if ajuste_dop != getattr(self, "_last_ajuste_dop", None):
                self._last_ajuste_dop = ajuste_dop
                # setDopaminaAdjust ya maneja brillo de ojos internamente
                self._bridge.set_dopamina_adjust(ajuste_dop)

            # ── Modo creativo / CV nocturno ───────────────────────────────
            modo_app = data.get("modo_app", "")
            if modo_app != getattr(self, "_last_modo_app", ""):
                self._last_modo_app = modo_app
                if modo_app == "creativo":
                    self._bridge.set_modo_creativo()
                elif modo_app == "cv_noche":
                    self._bridge.set_modo_cv_noche()
                elif modo_app == "programadora":
                    self._bridge.set_programmer_mode(True)
                else:
                    self._bridge.set_programmer_mode(False)

            # ── Beat detection: mover cabeza rítmicamente ────────────────
            beat_angle = float(data.get("beat_angle", 0.0))
            if beat_angle != getattr(self, "_last_beat_angle", 0.0):
                self._last_beat_angle = beat_angle
                if data.get("beat_active", False):
                    self._bridge.set_head_tilt(beat_angle)

            # ── Modo baile: activar cuando hay música detectada ───────────
            music_mode = data.get("music_mode", False)
            if music_mode != getattr(self, "_last_music_mode", False):
                self._last_music_mode = music_mode
                if music_mode:
                    self._bridge.start_dance_mode()
                    print("[Live2D] 🎵 Modo baile activado")
                else:
                    self._bridge.stop_dance_mode()
                    print("[Live2D] 🎵 Modo baile desactivado")

            # ── Flow state: silencio visual durante concentración ─────────
            flow = data.get("flow_state", False)
            if flow != getattr(self, "_last_flow", False):
                self._last_flow = flow
                if flow:
                    # En flow: respiración rítmica, mirada fija
                    self._bridge.set_dopamina_adjust(0.0)
                    print("[Live2D] Flow state activo — silencio visual")

            # ── Persistir pose física cada vez que cambia el estado ───────
            self._persistir_pose(nivel_sk, ajuste_dop, estado)

        except Exception:
            pass

    def _start_tool_animation(self) -> None:
        """Inicia la animación de 'leyendo/buscando' en el modelo Live2D."""
        self._bridge.set_tool_animation(True)
        print("[Live2D] Animación de herramienta activada")

    def _stop_tool_animation(self) -> None:
        """Detiene la animación de herramienta y restaura estado normal."""
        self._bridge.set_tool_animation(False)
        print("[Live2D] Animación de herramienta desactivada")
        """Guarda la pose física actual en ia_recuerdos.json de forma async."""
        # Solo persistir si algo cambió
        _pose = {"nivel_sarcasmo": nivel_sarcasmo,
                 "ajuste_dopamina": ajuste_dopamina,
                 "estado": estado}
        if _pose == getattr(self, "_last_pose_persistida", None):
            return
        self._last_pose_persistida = _pose

        def _write():
            try:
                from config import DATA_DIR
                p = DATA_DIR / "ia_recuerdos.json"
                data = {}
                if p.exists():
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        data = {}
                data["ultima_pose_fisica"] = {
                    "nivel_sarcasmo":  nivel_sarcasmo,
                    "ajuste_dopamina": ajuste_dopamina,
                    "estado":          estado,
                    "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
            except Exception:
                pass

        threading.Thread(target=_write, daemon=True).start()

    def _restaurar_pose_inicial(self) -> None:
        """Al iniciar, restaura la última pose guardada en ia_recuerdos.json."""
        try:
            from config import DATA_DIR
            p = DATA_DIR / "ia_recuerdos.json"
            if not p.exists():
                return
            data = json.loads(p.read_text(encoding="utf-8"))
            pose = data.get("ultima_pose_fisica", {})
            if not pose:
                return

            nivel_sk  = int(pose.get("nivel_sarcasmo", 0))
            ajuste_dop = float(pose.get("ajuste_dopamina", 0.0))
            estado     = pose.get("estado", "neutral")

            print(f"[Live2D] Restaurando pose: estado={estado} sarcasmo={nivel_sk}")
            self._bridge.set_expression(estado)
            self._bridge.set_sarcasm_level(nivel_sk)
            self._bridge.set_dopamina_adjust(ajuste_dop)

            # Inicializar los "last" para que _check_state no los sobreescriba
            self._last_nivel_sk       = nivel_sk
            self._last_ajuste_dop     = ajuste_dop
            self._last_pose_persistida = pose
        except Exception:
            pass
    
    def _observe_screen_fallback(self) -> None:
        """Método fallback de observación simple si el sistema analítico falla."""
        try:
            from screen_vision import obtener_ventana_activa_info
            
            ventana_info = obtener_ventana_activa_info()
            ventana_titulo = ventana_info.get("titulo", "").lower()
            proceso = ventana_info.get("proceso", "").lower()
            
            # Solo actualizar expresión facial, sin comentarios
            nueva_expresion = None
            
            if any(code in ventana_titulo or code in proceso for code in ["vscode", "code", "github"]):
                nueva_expresion = "疑惑"  # concentración
            elif any(design in ventana_titulo for design in ["canva", "figma", "photoshop"]):
                nueva_expresion = "星星眼"  # creatividad
            elif any(browser in proceso for browser in ["chrome", "firefox", "edge", "opera"]):
                nueva_expresion = "脸红"  # navegación
            else:
                nueva_expresion = "脸红"  # neutral
            
            if nueva_expresion:
                self._bridge.set_expression(nueva_expresion)
                
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Desktop Embedding — anclar al escritorio
    # ------------------------------------------------------------------

    def anchor_to_desktop(self) -> bool:
        """Ancla la ventana al escritorio usando SetParent(hwnd, WorkerW)."""
        try:
            hwnd = int(self.winId())
            return _embed_in_desktop(hwnd)
        except Exception as e:
            print(f"[Desktop] No se pudo anclar al escritorio: {e}")
            return False

    # ------------------------------------------------------------------
    # Click-through
    # ------------------------------------------------------------------

    def enable_click_through(self) -> None:
        """Hace la ventana transparente a los clics del mouse Y sin foco."""
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE  = 0x08000000   # ← no activa al hacer clic
            WS_EX_TOOLWINDOW  = 0x00000080   # ← no aparece en Alt+Tab

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT
                      | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
            print("[Desktop] Click-through activado (sin robo de foco)")
        except Exception as e:
            print(f"[Desktop] No se pudo activar click-through: {e}")

    def disable_click_through(self) -> None:
        """Desactiva el click-through (para poder interactuar con el personaje)."""
        try:
            import ctypes
            hwnd = int(self.winId())
            GWL_EXSTYLE      = -20
            WS_EX_LAYERED    = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style & ~WS_EX_TRANSPARENT | WS_EX_LAYERED
            )
        except Exception as e:
            print(f"[Desktop] Error: {e}")


# ---------------------------------------------------------------------------
# Desktop Embedding
# ---------------------------------------------------------------------------

def _find_workerw() -> int:
    """Encuentra el handle de WorkerW (capa del escritorio). Versión robusta."""
    progman = ctypes.windll.user32.FindWindowW("Progman", None)
    if not progman:
        return 0

    # Enviar mensaje especial múltiples veces para asegurar que WorkerW se cree
    for _ in range(3):
        ctypes.windll.user32.SendMessageTimeoutW(
            progman, 0x052C, 0, 0, 0, 1000, None
        )
        time.sleep(0.3)

    workerw = ctypes.c_int(0)

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_int, ctypes.c_int
    )

    def enum_callback(hwnd, lparam):
        # Buscar SHELLDLL_DefView dentro de cada ventana
        shell = ctypes.windll.user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shell:
            # WorkerW está justo después del hwnd que contiene SHELLDLL_DefView
            ww = ctypes.windll.user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if ww:
                workerw.value = ww
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_callback), 0)

    # Si no encontró WorkerW, intentar con Progman directamente como fallback
    if not workerw.value:
        print("[Desktop] WorkerW no encontrado, usando Progman como fallback")
        return progman

    return workerw.value


def _embed_in_desktop(hwnd: int) -> bool:
    """Ancla una ventana al escritorio."""
    workerw = _find_workerw()
    if not workerw:
        print("[Desktop] No se encontró WorkerW")
        return False

    result = ctypes.windll.user32.SetParent(hwnd, workerw)
    if result:
        print(f"[Desktop] ✓ Personaje anclado al escritorio (WorkerW={workerw:#x})")
        return True
    else:
        print("[Desktop] SetParent falló")
        return False


def _configurar_startup() -> None:
    """Crea un acceso directo en Startup de Windows para iniciar Alisha automáticamente."""
    try:
        import os
        startup_dir = Path(os.environ.get("APPDATA", "")) / \
                      "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if not startup_dir.exists():
            return

        shortcut_path = startup_dir / "Alisha.bat"
        if shortcut_path.exists():
            return  # ya existe, no sobreescribir

        script_dir = Path(__file__).parent.absolute()
        python_exe = sys.executable

        bat_content = f"""@echo off
cd /d "{script_dir}"
start "" /B "{python_exe}" "{script_dir / 'desktop_widget.py'}"
"""
        shortcut_path.write_text(bat_content, encoding="utf-8")
        print(f"[Startup] ✓ Acceso directo creado: {shortcut_path}")
    except Exception as e:
        print(f"[Startup] No se pudo crear acceso directo: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Alisha Completa - Personaje Live2D + IA + Web integrados")
    parser.add_argument("--model", default=str(MODEL_FILE),
                        help="Ruta al archivo .model3.json")
    parser.add_argument("--x", type=int, default=WIDGET_X)
    parser.add_argument("--y", type=int, default=WIDGET_Y)
    parser.add_argument("--w", type=int, default=WIDGET_W)
    parser.add_argument("--h", type=int, default=WIDGET_H)
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"❌ Modelo no encontrado: {model_path}")
        # Buscar automáticamente en el directorio padre
        model_dir = model_path.parent
        if model_dir.exists():
            found = list(model_dir.glob("*.model3.json"))
            if found:
                model_path = found[0]
                print(f"✅ Usando: {model_path}")
            else:
                print(f"❌ No se encontró ningún modelo .model3.json en {model_dir}")
                print("💡 Verificá que la ruta del modelo Live2D sea correcta en config.py")
                print("🔧 Puedes continuar sin Live2D, solo se usará la interfaz web")
                continuar = input("¿Continuar sin Live2D? (s/N): ").lower().startswith('s')
                if not continuar:
                    sys.exit(1)
                # Usar modo solo web
                print("🌐 Iniciando solo interfaz web...")
                import subprocess
                subprocess.run([sys.executable, "iniciar_web.py"])
                return
        else:
            print(f"❌ Directorio no existe: {model_dir}")
            print("💡 Verificá que VTube Studio esté instalado y la ruta sea correcta")
            print("🔧 Puedes continuar sin Live2D, solo se usará la interfaz web")
            continuar = input("¿Continuar sin Live2D? (s/N): ").lower().startswith('s')
            if not continuar:
                sys.exit(1)
            # Usar modo solo web
            print("🌐 Iniciando solo interfaz web...")
            import subprocess
            subprocess.run([sys.executable, "iniciar_web.py"])
            return

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Alisha - Asistente IA Completa")
        
        # Suprimir warnings de Qt sobre DPI
        try:
            app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton)
        except AttributeError:
            # Atributo no disponible en esta versión de Qt
            pass
        
    except Exception as e:
        print(f"❌ Error iniciando aplicación Qt: {e}")
        print("🔧 Iniciando modo web alternativo...")
        import subprocess
        subprocess.run([sys.executable, "iniciar_web.py"])
        return

    # (no se matan procesos Python anteriores para no interrumpir el arranque)

    try:
        widget = DesktopWidget(model_path)
        widget.show()
        widget.raise_()           # traer al frente de todas las ventanas
        widget.activateWindow()   # activar la ventana

        # Forzar topmost via Win32 después de que Qt la muestre
        try:
            import ctypes
            hwnd = int(widget.winId())
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
        except Exception:
            pass

        # Iniciar en modo INTERACTIVO (visible) — el usuario puede activar click-through con Ctrl+Shift+L
        # NO llamar enable_click_through() al inicio porque WS_EX_TRANSPARENT puede hacer invisible la ventana
        # QTimer.singleShot(600, widget.enable_click_through)  # desactivado — arranca visible

        print(f"\n🎭 Alisha Completa Iniciada")
        print(f"  ✨ Personaje Live2D: {model_path.name}")
        print(f"  📍 Posición: ({args.x}, {args.y})")
        print(f"  🖱️ Seguimiento de mouse: Activado")
        print(f"  👆 Reacciones por clics: Activado")
        print(f"  👁️ Observación de pantalla: Activado (modo silencioso)")
        print(f"  🔝 Siempre al frente: Activado")
        print(f"  🌐 Interfaz web: http://localhost:5000")
        print(f"  🤖 Motor de IA: Integrado")
        print(f"\n💡 Funcionalidades:")
        print(f"  • Mueve el mouse para que Alisha te siga con la mirada")
        print(f"  • Haz clics cerca del personaje: 1=susto, 2=curiosidad, 3+=enojo")
        print(f"  • Cambia de aplicación y observa sus reacciones sutiles")
        print(f"  • Usa la interfaz web para chatear")
        print(f"\n🤫 Modo silencioso activado - No molestará con comentarios")
        print(f"Cerrá con Ctrl+C en la terminal\n")

        # Configurar acceso directo en Startup de Windows (solo si no existe)
        _configurar_startup()

        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ Error iniciando Alisha: {e}")
        print("🔧 Iniciando modo web alternativo...")
        import subprocess
        subprocess.run([sys.executable, "iniciar_web.py"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Alisha cerrada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        print("🔧 Intentando modo web alternativo...")
        try:
            import subprocess
            subprocess.run([sys.executable, "iniciar_web.py"])
        except Exception:
            print("💡 Ejecuta 'python iniciar_web.py' manualmente para usar la interfaz web")
            input("Presiona Enter para cerrar...")
