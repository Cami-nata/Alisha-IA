"""Servidor Flask — interfaz web para el asistente IA."""
import base64
import os
import sys
import threading
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging para reducir ruido
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

# Forzar UTF-8 en la terminal de Windows (solo si hay stdout/stderr)
if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr is not None and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit

# Importar el núcleo del asistente
from config import LOG_FILE
from emotion_engine import EmotionEngine

# ── HybridIntelligenceCore — cerebro unificado de Alisha ─────────────────────
try:
    from brain import get_brain, get_idle_watcher
    _brain = get_brain()
    _idle_watcher = get_idle_watcher()
    _idle_watcher.start()
    _BRAIN_OK = True
    print("[WebApp] ✓ HybridIntelligenceCore conectado")
except Exception as _brain_err:
    _brain = None
    _BRAIN_OK = False
    print(f"[WebApp] ⚠ Brain no disponible: {_brain_err}")

# ── DocumentIntelligence ──────────────────────────────────────────────────────
try:
    from document_intelligence import get_document_intelligence
    _doc_intel = get_document_intelligence()
    _DOC_INTEL_OK = True
except Exception:
    _doc_intel = None
    _DOC_INTEL_OK = False

# ── VisionEngine ──────────────────────────────────────────────────────────────
try:
    from vision_engine import get_vision_engine, enrich_query_with_vision
    _vision = get_vision_engine()
    _vision.start()
    _VISION_OK = True
    print("[WebApp] ✓ VisionEngine conectado (scan pasivo activo)")
except Exception as _vision_err:
    _vision = None
    _VISION_OK = False
    print(f"[WebApp] ⚠ VisionEngine no disponible: {_vision_err}")

# ── AudioVisualSync ───────────────────────────────────────────────────────────
try:
    from audio_visual_sync import get_audio_visual_sync
    _avs = get_audio_visual_sync()
    _AVS_OK = True
    print("[WebApp] ✓ AudioVisualSync conectado")
except Exception as _avs_err:
    _avs = None
    _AVS_OK = False
    print(f"[WebApp] ⚠ AudioVisualSync no disponible: {_avs_err}")

# ── AgentLoop (fail-silent) ───────────────────────────────────────────────────
_agent_loop = None
try:
    from agent_loop import AgentLoop as _AgentLoop
    _AGENT_LOOP_OK = True
except Exception:
    _AgentLoop = None
    _AGENT_LOOP_OK = False

# ── MemoryDB — persistencia SQLite ───────────────────────────────────────────
try:
    from memory_db import MemoryDB as _MemoryDB
    _memory_db = _MemoryDB()
    _MEMORY_DB_OK = True
    print("[WebApp] ✓ MemoryDB SQLite conectado")
except Exception as _mdb_err:
    _memory_db = None
    _MEMORY_DB_OK = False
    print(f"[WebApp] ⚠ MemoryDB no disponible: {_mdb_err}")
from identity_evolution import evaluar_evolucion
from memory import (
    agregar_memoria, cargar_identidad, cargar_memoria, configurar_autostart,
    guardar_identidad, guardar_memoria, guardar_memoria_personal, guardar_perfil,
    guardar_estado, guardar_recordatorio, obtener_estado_vigente,
    reiniciar_memoria, limpiar_historial,
)
from ia import inicializar_asistente, procesar_turno
# audio_listener importado lazy para evitar conflicto con torch/whisper al arrancar con pythonw
_transcribir_audio_bytes = None
def _get_transcribir():
    global _transcribir_audio_bytes
    if _transcribir_audio_bytes is None:
        try:
            from audio_listener import transcribir_audio_bytes
            _transcribir_audio_bytes = transcribir_audio_bytes
        except Exception as e:
            print(f"[WebApp] ⚠ audio_listener no disponible: {e}")
            _transcribir_audio_bytes = lambda b: ""
    return _transcribir_audio_bytes
from pc_controller import abort_all_actions
from tts_engine import speak
from reminder_engine import ReminderEngine
from virtual_cradle import iniciar_cuna
from file_analyzer import analizar_archivo, es_archivo_soportado, GeminiAPIError

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False)

# ── Configurar ffmpeg para pydub (lip-sync) — búsqueda dinámica ──────────────
try:
    import shutil as _shutil
    from pydub import AudioSegment as _AS

    def _encontrar_ffmpeg() -> str:
        """Busca ffmpeg en el sistema de forma dinámica — compatible con cualquier PC."""
        # 1. Buscar en PATH del sistema (lo más portable)
        en_path = _shutil.which("ffmpeg")
        if en_path:
            return en_path
        # 2. Rutas comunes de instalación en Windows
        _FFMPEG_PATHS = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            # WinGet instala en AppData del usuario actual (dinámico)
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"),
        ]
        for fp in _FFMPEG_PATHS:
            if os.path.exists(fp):
                return fp
        return ""

    _ffmpeg_path = _encontrar_ffmpeg()
    if _ffmpeg_path:
        _AS.converter = _ffmpeg_path
        _AS.ffmpeg    = _ffmpeg_path
        _AS.ffprobe   = _ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        print(f"[WebApp] ✓ ffmpeg configurado: {_ffmpeg_path}")
except Exception:
    pass
    pass

# ---------------------------------------------------------------------------
# Estado global del asistente (compartido entre requests)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_identidad: dict = {}
_memoria: dict = {}
_emo: EmotionEngine | None = None
_last_message_id = 0
_session_id: int = -1   # ID de sesión activa en SQLite
_session_msg_count: int = 0  # contador de mensajes en la sesión activa


def _inicializar() -> None:
    global _identidad, _memoria, _emo, _session_id
    _identidad, _memoria, _emo = inicializar_asistente()
    # Asegurar que el nombre de usuario esté guardado en disco como "Cami"
    perfil = _memoria.setdefault("perfil", {})
    nombre_actual = perfil.get("nombre", "")
    if not nombre_actual or nombre_actual.lower() == "alisha":
        from memory import guardar_perfil
        guardar_perfil(_memoria, nombre="Cami")
        print("[WebApp] ✓ Nombre de usuario guardado: Cami")
    # Iniciar loop de animaciones de espera (parpadeo/respiración)
    try:
        from alisha_bridge import start_idle_loop
        start_idle_loop()
    except Exception as _idle_err:
        print(f"[WebApp] ⚠ Idle loop: {_idle_err}")
    # Limpiar procesos huérfanos de Python de arranques anteriores
    try:
        from agent_loop import AgentLoop as _AL
        _orphan_result = _AL().cleanup_orphan_python_processes()
        if _orphan_result["terminated_count"] > 0:
            print(f"[WebApp] ✓ Procesos huérfanos limpiados: {_orphan_result['terminated_count']}")
    except Exception as _orphan_err:
        print(f"[WebApp] ⚠ Orphan cleanup: {_orphan_err}")
    from pc_controller import iniciar_hotkey_bloqueo
    iniciar_hotkey_bloqueo()
    if _MEMORY_DB_OK and _memory_db:
        try:
            _session_id = _memory_db.start_session()
            print(f"[WebApp] ✓ Sesión SQLite iniciada: ID={_session_id}")
        except Exception:
            pass
    # Monitor de salud del sistema
    try:
        from alisha_health import iniciar_monitor
        iniciar_monitor()
    except Exception as e:
        print(f"[WebApp] Health monitor: {e}")

    # Motor de sugerencias proactivas
    try:
        from alisha_sugerencias import iniciar_sugerencias
        iniciar_sugerencias()
        print("[WebApp] ✓ Motor de sugerencias iniciado")
    except Exception as e:
        print(f"[WebApp] Sugerencias: {e}")

    # Motor de curiosidad autónoma (FASE 2 — JCySharp)
    try:
        from alisha_curiosidad import iniciar_curiosidad

        def _callback_curiosidad(texto: str) -> None:
            """Emite la iniciativa de curiosidad al chat web y por voz."""
            try:
                socketio.emit("respuesta", {
                    "texto": texto,
                    "estado_emocional": "curiosidad",
                    "fuente": "curiosidad",
                })
            except Exception:
                pass
            try:
                from audio_visual_sync import get_audio_visual_sync
                get_audio_visual_sync().speak(
                    texto,
                    sarcasm_score=0.0,
                    emotional_state="curiosidad",
                    async_mode=True,
                )
            except Exception:
                pass

        iniciar_curiosidad(_callback_curiosidad)
        print("[WebApp] ✓ Motor de curiosidad autónoma iniciado")
    except Exception as e:
        print(f"[WebApp] Curiosidad: {e}")


# ---------------------------------------------------------------------------
# Rutas HTTP
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    # Asegurar que el nombre del usuario sea siempre "Cami" si no está configurado
    nombre_usuario = _memoria.get("perfil", {}).get("nombre", "") or "Cami"
    if nombre_usuario.lower() == "alisha":
        nombre_usuario = "Cami"
    return render_template("index.html",
                           nombre_ia=_identidad.get("nombre", "IA"),
                           nombre_usuario=nombre_usuario)


@app.route("/api/perfil", methods=["GET"])
def get_perfil():
    perfil = _memoria.get("perfil", {})
    emo_estado = _emo.obtener_estado_actual() if _emo else {"estado": "neutral", "dopamina": 0.0, "cansancio": 0.0}
    energia = None
    try:
        from autonomous_agent import get_agent
        agente = get_agent()
        if agente:
            energia = agente.get_energy().get_energia()
    except Exception:
        pass
    # Asegurar identidad correcta: usuario siempre es Cami, nunca Alisha
    nombre_usuario = perfil.get("nombre", "") or "Cami"
    if nombre_usuario.lower() == "alisha":
        nombre_usuario = "Cami"
    return jsonify({
        "nombre_ia": _identidad.get("nombre", "IA"),
        "nombre_usuario": nombre_usuario,
        "estado_emocional": emo_estado.get("estado", "neutral"),
        "dopamina": emo_estado.get("dopamina", 0.0),
        "cansancio": emo_estado.get("cansancio", 0.0),
        "energia": energia,
        "version": _identidad.get("version", 1),
    })


@app.route("/api/perfil/nombre", methods=["POST"])
def set_nombre():
    data = request.json or {}
    nombre = data.get("nombre", "").strip()
    if nombre:
        guardar_perfil(_memoria, nombre=nombre)
    return jsonify({"ok": True})


@app.route("/api/historial", methods=["GET"])
def get_historial():
    """
    Retorna el historial de conversaciones.
    Prioridad: SQLite (memory_db) → JSON en RAM (_memoria).
    """
    if _MEMORY_DB_OK and _memory_db:
        try:
            recientes = _memory_db.load_recent(n=30)
            if recientes:
                return jsonify(recientes)
        except Exception:
            pass
    # Fallback al JSON en RAM
    historial = _memoria.get("historial", [])[-30:]
    return jsonify(historial)


@app.route("/api/sesiones", methods=["GET"])
def get_sesiones():
    """Retorna las últimas sesiones para la barra lateral."""
    if not _MEMORY_DB_OK or not _memory_db or _memory_db._using_fallback:
        return jsonify([])
    try:
        cursor = _memory_db._conn.execute(
            "SELECT id, inicio, resumen, actividad_principal, titulo, mensajes_count "
            "FROM sesiones ORDER BY id DESC LIMIT 99999"
        )
        rows = cursor.fetchall()
        sesiones = []
        for r in rows:
            titulo = r["titulo"] or r["resumen"] or r["actividad_principal"] or "Conversación"
            sesiones.append({
                "id":       r["id"],
                "inicio":   r["inicio"],
                "titulo":   titulo,
                "mensajes": r["mensajes_count"] or 0,
            })
        return jsonify(sesiones)
    except Exception as e:
        return jsonify([])


@app.route("/api/sesion/<int:session_id>", methods=["GET"])
def get_sesion_detalle(session_id: int):
    """Retorna las conversaciones de una sesión específica."""
    if not _MEMORY_DB_OK or not _memory_db:
        return jsonify([])
    try:
        mensajes = _memory_db.load_by_session(session_id, n=200)
        return jsonify(mensajes)
    except Exception:
        return jsonify([])


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    global _memoria
    with _lock:
        _memoria = limpiar_historial(_memoria)
    return jsonify({"ok": True})


@app.route("/api/nuevo_chat", methods=["POST"])
def nuevo_chat():
    """Crea una nueva sesión de chat y la activa."""
    global _session_id, _session_msg_count
    if _MEMORY_DB_OK and _memory_db:
        try:
            _session_id = _memory_db.start_session()
            _session_msg_count = 0
            print(f"[WebApp] ✓ Nueva sesión creada: ID={_session_id}")
            return jsonify({"ok": True, "session_id": _session_id})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "session_id": -1})


@app.route("/api/sesion/<int:session_id>/mensajes", methods=["GET"])
def get_mensajes_sesion(session_id: int):
    """Carga los mensajes de una sesión específica."""
    if not _MEMORY_DB_OK or not _memory_db:
        return jsonify([])
    try:
        mensajes = _memory_db.load_by_session(session_id)
        return jsonify(mensajes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_archivo():
    """Recibe un archivo, lo analiza y retorna el resultado."""
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    pregunta = request.form.get("pregunta", "")

    # ── Reacción física inmediata: Alisha mira el archivo ────────────────────
    try:
        import json as _j
        from config import DATA_DIR
        _sf = DATA_DIR / "chibi_state.json"
        _sd = _j.loads(_sf.read_text(encoding="utf-8")) if _sf.exists() else {}
        _sd["estado"]   = "curiosidad"
        _sd["hablando"] = False
        _sf.write_text(_j.dumps(_sd, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    # Guardar temporalmente
    tmp_path = Path(__file__).parent / "static" / "tmp" / file.filename
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(tmp_path)

    if not es_archivo_soportado(str(tmp_path)):
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": f"Formato no soportado: {tmp_path.suffix}"}), 400

    try:
        resultado = analizar_archivo(str(tmp_path), pregunta)
    except GeminiAPIError as e:
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": f"Error procesando imagen: {e}"}), 500

    tmp_path.unlink(missing_ok=True)

    if resultado:
        titulo = pregunta or f"Escaneo de {file.filename}"
        categoria = "Razonamiento" if "problema" in resultado.lower() or "ejercicio" in resultado.lower() else "Imagen"
        guardar_memoria_personal(_memoria, titulo=titulo, contenido=resultado, categoria=categoria, tipo="Imagen")
        guardar_memoria(_memoria)

        # ── Alisha habla el resultado por los parlantes ───────────────────────
        if _AVS_OK and _avs and resultado:
            resumen = resultado[:200].replace('\n', ' ')
            def _hablar_resultado():
                _avs.speak(
                    f"Mirá lo que encontré: {resumen}",
                    sarcasm_score=0.0,
                    emotional_state="curiosidad",
                    async_mode=True,
                )
            threading.Thread(target=_hablar_resultado, daemon=True).start()

    return jsonify({"resultado": resultado})


@app.route("/api/analyze-doc", methods=["POST"])
def analyze_document():
    """
    Analiza un documento .docx/.pdf con el DocumentIntelligence.
    Retorna errores, sugerencias y Sarcasm Score.
    """
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    pregunta = request.form.get("pregunta", "")

    tmp_path = Path(__file__).parent / "static" / "tmp" / file.filename
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(tmp_path)

    try:
        if _DOC_INTEL_OK:
            analysis = _doc_intel.analyze(str(tmp_path), pregunta)
            errors_data = [
                {
                    "tipo": e.tipo,
                    "descripcion": e.descripcion,
                    "ubicacion": e.ubicacion,
                    "severidad": e.severidad,
                }
                for e in analysis.errors
            ]

            # Generar respuesta sarcástica con el brain si hay errores
            alisha_feedback = ""
            if _BRAIN_OK and _brain and analysis.errors:
                error_strings = [f"{e.tipo}: {e.descripcion}" for e in analysis.errors]
                context_prompt = (
                    f"Revisé el documento '{file.filename}' y encontré estos problemas: "
                    + "; ".join(error_strings[:5])
                    + ". Dame tu feedback honesto."
                )
                brain_resp = _brain.process(context_prompt, errors=error_strings)
                alisha_feedback = brain_resp.content
                socketio.emit("engine_indicator", {
                    "engine": brain_resp.engine_used,
                    "sarcasm_score": round(brain_resp.sarcasm_score, 2),
                })

            result = {
                "word_count":      analysis.word_count,
                "errors":          errors_data,
                "suggestions":     analysis.suggestions,
                "sarcasm_score":   round(analysis.sarcasm_score, 2),
                "sections":        analysis.sections,
                "processing_time": round(analysis.processing_time, 2),
                "from_cache":      analysis.from_cache,
                "alisha_feedback": alisha_feedback,
            }
            # Emitir feedback visual via WebSocket
            socketio.emit("doc_analysis", {
                "filename":      file.filename,
                "sarcasm_score": result["sarcasm_score"],
                "error_count":   len(errors_data),
            })
        else:
            from file_analyzer import analizar_documento
            content = analizar_documento(str(tmp_path), pregunta)
            result = {"resultado": content, "errors": [], "suggestions": []}
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": f"Error analizando documento: {e}"}), 500

    tmp_path.unlink(missing_ok=True)
    return jsonify(result)


@app.route("/api/brain/status", methods=["GET"])
def brain_status():
    """Estado del HybridIntelligenceCore."""
    if not _BRAIN_OK:
        return jsonify({"available": False})
    state = _brain.get_emotional_state()
    return jsonify({
        "available":    True,
        "ollama_ok":    _brain._ollama.is_available(),
        "openai_ok":    _brain._openai.is_available(),
        "dopamina":     round(state.dopamina, 2),
        "humor":        round(state.humor, 2),
        "tension":      round(state.tension, 2),
    })


@app.route("/api/vision/goal", methods=["POST"])
def set_vision_goal():
    """Registra la meta activa del usuario para detección de distracciones."""
    if not _VISION_OK:
        return jsonify({"error": "VisionEngine no disponible"}), 503
    data = request.json or {}
    goal = data.get("goal", "").strip()
    if goal:
        _vision.set_active_goal(goal)
    return jsonify({"ok": True, "goal": goal})


@app.route("/api/vision/snapshot", methods=["GET"])
def get_vision_snapshot():
    """Retorna el último snapshot de visión."""
    if not _VISION_OK:
        return jsonify({"available": False})
    snap = _vision.get_last_snapshot()
    if not snap:
        return jsonify({"available": True, "snapshot": None})
    return jsonify({
        "available":      True,
        "snapshot": {
            "window_title":    snap.window_title,
            "app_category":    snap.app_category,
            "is_distraction":  snap.is_distraction,
            "is_work":         snap.is_work,
            "errors_detected": snap.errors_detected,
            "cpu_usage":       round(snap.cpu_usage, 1),
        },
        "context": {
            "active_goal":        _vision.get_context().active_goal,
            "distraction_count":  _vision.get_context().distraction_count,
        }
    })


@app.route("/api/audio", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No se recibió audio"}), 400

    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"error": "Archivo de audio vacío"}), 400

    try:
        texto = _get_transcribir()(audio_bytes)
    except Exception as e:
        return jsonify({"error": f"No se pudo transcribir audio: {e}"}), 500

    if not texto.strip():
        return jsonify({"error": "No se detectó texto en el audio."}), 422

    global _identidad, _memoria
    with _lock:
        try:
            _identidad, _memoria, respuesta = procesar_turno(texto, _identidad, _memoria, _emo)
            _identidad = evaluar_evolucion(_identidad, _memoria)
            estado_emo = _emo.obtener_estado_actual().get("estado", "neutral")
        except Exception as e:
            return jsonify({"error": f"Error procesando el mensaje: {e}"}), 500

    return jsonify({
        "texto": texto,
        "respuesta": respuesta,
        "estado_emocional": estado_emo,
    })


@app.route("/api/status", methods=["GET"])
def get_status():
    perfil = _memoria.get("perfil", {})
    # Asegurar identidad correcta: usuario siempre es Cami, nunca Alisha
    nombre_usuario = perfil.get("nombre", "") or "Cami"
    if nombre_usuario.lower() == "alisha":
        nombre_usuario = "Cami"
    datos = {
        "nombre_ia": _identidad.get("nombre", "IA"),
        "nombre_usuario": nombre_usuario,
        "estado_emocional": _emo.obtener_estado_actual().get("estado", "neutral"),
        "dopamina": _emo.obtener_estado_actual().get("dopamina", 0.0),
        "cansancio": _emo.obtener_estado_actual().get("cansancio", 0.0),
        "energia": None,
        "media_actual": None,
    }
    try:
        from autonomous_agent import get_agent
        agente = get_agent()
        if agente:
            datos["energia"] = agente.get_energy().get_energia()
    except Exception:
        datos["energia"] = None

    # Media Sync — leer desde chibi_state.json (escrito por AgentLoop)
    try:
        from assistant_state import cargar_estado
        estado = cargar_estado()
        media = estado.get("media_actual")
        if media and media.get("title"):
            datos["media_actual"] = media
    except Exception:
        pass

    return jsonify(datos)


@app.route("/api/agent/status", methods=["GET"])
def get_agent_status():
    """Estado del AgentLoop y sus sub-componentes."""
    if _agent_loop is None:
        return jsonify({"error": "AgentLoop no iniciado"})
    try:
        return jsonify(_agent_loop.get_status())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/stop", methods=["POST"])
def stop_actions():
    abort_all_actions()
    try:
        from autonomous_agent import get_task_manager
        get_task_manager().cancelar_todas()
    except Exception:
        pass
    return jsonify({"ok": True, "mensaje": "Abortando acciones del agente."})


@app.route("/api/cleanup_orphans", methods=["POST"])
def cleanup_orphan_processes():
    """
    Limpia procesos huérfanos de Python que quedaron si Alisha se crasheó.
    Útil para llamar al arrancar o cuando se detecta comportamiento extraño.
    """
    if _agent_loop is None:
        # Crear instancia temporal solo para la limpieza
        try:
            from agent_loop import AgentLoop as _AL
            temp_loop = _AL()
            result = temp_loop.cleanup_orphan_python_processes()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    else:
        result = _agent_loop.cleanup_orphan_python_processes()
    return jsonify({"ok": True, **result})


@app.route("/api/test_mouse", methods=["POST"])
def test_mouse():
    """
    Comando de prueba: mueve el cursor en un pequeño círculo para verificar
    que PyAutoGUI tiene control del sistema operativo.
    """
    def _mover():
        import time as _t
        try:
            import pyautogui
            # Obtener posición actual
            x0, y0 = pyautogui.position()
            # Mover en un pequeño cuadrado de 80px
            pasos = [(x0+80, y0), (x0+80, y0+80), (x0, y0+80), (x0, y0)]
            for px, py in pasos:
                pyautogui.moveTo(px, py, duration=0.3)
                _t.sleep(0.1)
            # Volver al origen
            pyautogui.moveTo(x0, y0, duration=0.3)
            socketio.emit("respuesta", {
                "texto": "✓ Test de mouse OK — el cursor se movió. PyAutoGUI tiene control del sistema.",
                "estado_emocional": "alegría",
            })
        except Exception as e:
            socketio.emit("respuesta", {
                "texto": f"✗ Test de mouse FALLÓ: {e}. Verificá que Alisha_IA.py corra como administrador.",
                "estado_emocional": "frustración",
            })

    threading.Thread(target=_mover, daemon=True).start()
    return jsonify({"ok": True, "mensaje": "Test de mouse iniciado — mirá el cursor."})


@app.route("/api/escribir_en", methods=["POST"])
def escribir_en_app():
    """
    Endpoint directo para escribir en una app específica.
    Body: {"app": "bloc de notas", "texto": "hola mundo"}
    """
    data = request.json or {}
    app_destino = data.get("app", "").strip()
    texto       = data.get("texto", "").strip()

    if not texto:
        return jsonify({"ok": False, "error": "Falta el texto"}), 400

    def _ejecutar():
        import time as _t
        try:
            from actions import enfocar_ventana, escribir_texto, abrir_app
            from pc_controller import esta_bloqueado

            if esta_bloqueado():
                socketio.emit("respuesta", {
                    "texto": "Control bloqueado. Presioná Ctrl+Shift+L para desbloquearlo.",
                    "estado_emocional": "preocupación",
                })
                return

            socketio.emit("respuesta", {
                "texto": f"Tomando control{'de ' + app_destino if app_destino else ''}... moviendo el mouse.",
                "estado_emocional": "curiosidad",
            })

            if app_destino:
                _APP_MAP = {
                    "bloc de notas": "notepad", "notepad": "notepad",
                    "word": "word", "excel": "excel",
                    "powerpoint": "powerpoint", "vscode": "vscode",
                }
                app_cmd = _APP_MAP.get(app_destino.lower(), app_destino)
                enfocado = enfocar_ventana(app_destino, abrir_si_no_existe=app_cmd)
                if not enfocado:
                    socketio.emit("respuesta", {
                        "texto": f"No encontré '{app_destino}'. ¿Está abierta?",
                        "estado_emocional": "preocupación",
                    })
                    return

            _t.sleep(0.3)
            escribir_texto(texto, ventana_destino=app_destino)

            socketio.emit("respuesta", {
                "texto": f"¡Listo! Escribí en {app_destino or 'la ventana activa'}.",
                "estado_emocional": "alegría",
            })
        except Exception as e:
            socketio.emit("respuesta", {
                "texto": f"Error al escribir: {e}",
                "estado_emocional": "frustración",
            })

    threading.Thread(target=_ejecutar, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/confirmar_accion", methods=["POST"])
def confirmar_accion_agente():
    """
    El usuario confirmó una propuesta de acción de Alisha.
    Body: {"accion_id": "buscar_en_web", "contexto": {...}}
    """
    data      = request.json or {}
    accion_id = data.get("accion_id", "")
    contexto  = data.get("contexto", {})

    def _ejecutar_confirmada():
        import time as _t
        try:
            if accion_id == "buscar_en_web":
                query = contexto.get("query", "")
                if query:
                    socketio.emit("respuesta", {
                        "texto": f"Buscando '{query}' con mi cerebro interno...",
                        "estado_emocional": "curiosidad",
                    })
                    # NO abrir navegador — usar brain directamente
                    if _BRAIN_OK and _brain:
                        resp = _brain.process(
                            f"Investigá sobre '{query}' y dame los 3 puntos más importantes "
                            f"en voseo rioplatense, máximo 4 oraciones. "
                            f"Usá tu conocimiento interno, no menciones que buscaste en Google."
                        )
                        socketio.emit("respuesta", {
                            "texto": resp.content,
                            "estado_emocional": "curiosidad",
                        })
                        socketio.emit("propuesta_accion", {
                            "mensaje": "¿Querés que te lo escriba en el Bloc de Notas?",
                            "accion_id": "escribir_solucion",
                            "contexto": {"texto": resp.content, "app": "bloc de notas"},
                        })

            elif accion_id == "escribir_solucion":
                texto   = contexto.get("texto", "")
                app_dst = contexto.get("app", "bloc de notas")
                if texto:
                    socketio.emit("respuesta", {
                        "texto": f"Abriendo {app_dst} y escribiendo...",
                        "estado_emocional": "entusiasmo",
                    })
                    from actions import enfocar_ventana, escribir_texto
                    _APP_MAP = {"bloc de notas": "notepad", "notepad": "notepad",
                                "word": "word", "vscode": "vscode"}
                    app_cmd = _APP_MAP.get(app_dst.lower(), "notepad")
                    enfocar_ventana(app_dst, abrir_si_no_existe=app_cmd)
                    _t.sleep(0.5)
                    escribir_texto(texto, ventana_destino=app_dst)
                    socketio.emit("respuesta", {
                        "texto": "¡Listo! Ya escribí la solución en tu pantalla.",
                        "estado_emocional": "alegría",
                    })

            elif accion_id == "confirmar_impresion":
                # Modo seguro: abre carpeta, NO imprime directamente
                try:
                    from alisha_print import get_print_manager
                    pm = get_print_manager()
                    resultado = pm.abrir_para_usuario()
                    socketio.emit("respuesta", {
                        "texto": resultado["mensaje"],
                        "estado_emocional": "alegría" if resultado["ok"] else "frustración",
                    })
                except Exception as e:
                    socketio.emit("respuesta", {
                        "texto": f"No pude abrir la carpeta: {e}",
                        "estado_emocional": "frustración",
                    })

            elif accion_id == "abrir_para_imprimir":
                # Igual que confirmar — abre carpeta
                try:
                    from alisha_print import get_print_manager
                    resultado = get_print_manager().abrir_para_usuario()
                    socketio.emit("respuesta", {
                        "texto": resultado["mensaje"],
                        "estado_emocional": "alegría" if resultado["ok"] else "frustración",
                    })
                except Exception as e:
                    socketio.emit("respuesta", {"texto": f"Error: {e}", "estado_emocional": "frustración"})

            elif accion_id.startswith("sugerencia_"):
                # Sugerencia proactiva aceptada — ejecutar acción
                accion_real = accion_id.replace("sugerencia_", "")
                tipo        = contexto.get("tipo", "")
                titulo_win  = ""
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    buf  = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                    titulo_win = buf.value.strip()
                except Exception:
                    pass

                contexto["titulo_ventana"] = titulo_win

                # Registrar aceptación (aprendizaje)
                try:
                    from alisha_sugerencias import get_suggestion_engine
                    get_suggestion_engine().registrar_respuesta(accion_real, tipo, acepto=True)
                except Exception:
                    pass

                # Ejecutar la acción
                try:
                    from alisha_sugerencias import ejecutar_sugerencia
                    resultado = ejecutar_sugerencia(accion_real, contexto)
                    socketio.emit("respuesta", {
                        "texto": resultado["mensaje"],
                        "estado_emocional": "alegría" if resultado["ok"] else "frustración",
                    })
                    if resultado["ok"]:
                        _t.sleep(1.0)
                        socketio.emit("respuesta", {
                            "texto": "Listo, ya te adelanté esa parte. ¿Necesitás algo más?",
                            "estado_emocional": "alegría",
                        })
                except Exception as e:
                    socketio.emit("respuesta", {"texto": f"No pude hacerlo: {e}", "estado_emocional": "frustración"})

            elif accion_id == "investigar_y_resumir":
                tema = contexto.get("tema", "")
                if tema and _BRAIN_OK and _brain:
                    socketio.emit("respuesta", {
                        "texto": f"Investigando '{tema}'... dame un segundo.",
                        "estado_emocional": "curiosidad",
                    })
                    # NO abrir navegador — usar brain directamente
                    resp = _brain.process(
                        f"Investigá sobre '{tema}' y dame un resumen práctico en voseo rioplatense. "
                        f"Incluí: qué es, cómo se usa/aplica, y 2-3 pasos concretos. Máximo 6 oraciones. "
                        f"Usá tu conocimiento interno."
                    )
                    socketio.emit("respuesta", {
                        "texto": resp.content,
                        "estado_emocional": "curiosidad",
                    })
                    socketio.emit("propuesta_accion", {
                        "mensaje": "¿Querés que te lo escriba en el Bloc de Notas para guardarlo?",
                        "accion_id": "escribir_solucion",
                        "contexto": {"texto": resp.content, "app": "bloc de notas"},
                    })

        except Exception as e:
            socketio.emit("respuesta", {
                "texto": f"Ups, algo falló: {e}",
                "estado_emocional": "frustración",
            })

    threading.Thread(target=_ejecutar_confirmada, daemon=True).start()
    return jsonify({"ok": True})


# ── Módulo de Entrenamiento ───────────────────────────────────────────────────

@app.route("/api/entrenar", methods=["POST"])
def iniciar_entrenamiento():
    data   = request.json or {}
    nombre = data.get("nombre", "").strip() or f"habilidad_{datetime.now().strftime('%H%M%S')}"
    try:
        from alisha_trainer import get_trainer
        trainer = get_trainer(socketio_emit=socketio.emit)
        msg = trainer.iniciar_grabacion(nombre)
        return jsonify({"ok": True, "mensaje": msg, "nombre": nombre})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/parar_entrenamiento", methods=["POST"])
def parar_entrenamiento():
    try:
        from alisha_trainer import get_trainer
        trainer = get_trainer(socketio_emit=socketio.emit)
        msg = trainer.detener_grabacion()
        return jsonify({"ok": True, "mensaje": msg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/habilidades", methods=["GET"])
def listar_habilidades():
    try:
        from memory_db import MemoryDB
        habilidades = MemoryDB().listar_habilidades()
        return jsonify(habilidades)
    except Exception:
        return jsonify([])


@app.route("/api/ejecutar_habilidad", methods=["POST"])
def ejecutar_habilidad():
    data   = request.json or {}
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"ok": False, "error": "Falta el nombre"}), 400
    try:
        from alisha_trainer import get_trainer
        trainer = get_trainer(socketio_emit=socketio.emit)
        msg = trainer.ejecutar_habilidad(nombre)
        return jsonify({"ok": True, "mensaje": msg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/config")
def config_panel():
    return render_template("config.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Retorna la configuración actual."""
    from config import DATA_DIR
    import json as _j

    # Leer personalidad
    personalidad = {}
    try:
        pf = DATA_DIR / "personalidad_alisha.json"
        if pf.exists():
            personalidad = _j.loads(pf.read_text(encoding="utf-8"))
    except Exception:
        pass

    # Leer config guardada
    config = {}
    try:
        cf = DATA_DIR / "alisha_config.json"
        if cf.exists():
            config = _j.loads(cf.read_text(encoding="utf-8"))
    except Exception:
        pass

    return jsonify({
        "voz":        config.get("voz", "alisha"),
        "rate":       config.get("rate", 175),
        "modelo":     config.get("modelo", "auto"),
        "sarcasmo":   config.get("sarcasmo", 5),
        "frecuencia": config.get("frecuencia", 5),
        "personalidad": personalidad,
    })


@app.route("/api/config", methods=["POST"])
def set_config():
    """Guarda la configuración y la aplica en tiempo real."""
    from pathlib import Path as _P
    import json as _j

    data = request.json or {}

    # Guardar config general
    from config import DATA_DIR
    config = {
        "voz":        data.get("voz", "alisha"),
        "rate":       data.get("rate", 175),
        "modelo":     data.get("modelo", "auto"),
        "sarcasmo":   data.get("sarcasmo", 6),
        "frecuencia": data.get("frecuencia", 5),
    }
    (DATA_DIR / "alisha_config.json").write_text(
        _j.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Guardar personalidad
    if "personalidad" in data:
        pf = DATA_DIR / "personalidad_alisha.json"
        existing = {}
        if pf.exists():
            try: existing = _j.loads(pf.read_text(encoding="utf-8"))
            except Exception: pass
        existing.update(data["personalidad"])
        pf.write_text(_j.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    # Aplicar voz en tiempo real
    try:
        from tts_engine import TTSEngine
        TTSEngine().set_voice(config["voz"])
        TTSEngine().set_rate(config["rate"])
    except Exception:
        pass

    return jsonify({"ok": True})


@app.route("/api/config/reset", methods=["POST"])
def reset_config():
    """Resetea la personalidad de Alisha."""
    from config import DATA_DIR
    try:
        (DATA_DIR / "personalidad_alisha.json").unlink(missing_ok=True)
        (DATA_DIR / "alisha_personalidad.json").unlink(missing_ok=True)
    except Exception:
        pass
    return jsonify({"ok": True})


@app.route("/api/despertar", methods=["POST"])
def despertar_alisha():
    """
    Despierta a Alisha si está dormida, o la inicia si no está corriendo.
    """
    # Si hay sistema de sueño activo, despertar directamente
    _ss = globals().get("_sistema_sueño")
    if _ss is not None:
        try:
            _ss.despertar_manual()
            return jsonify({"ok": True, "modo": "despertar_manual"})
        except Exception:
            pass

    # Si no está corriendo, iniciar el proceso
    import subprocess, sys
    from pathlib import Path as _P
    try:
        pythonw = _P(sys.executable).parent / "pythonw.exe"
        exe = str(pythonw) if pythonw.exists() else sys.executable
        base = _P(__file__).parent
        subprocess.Popen(
            [exe, str(base / "Alisha_IA.py")],
            cwd=str(base),
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True, "modo": "inicio_proceso"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# Variable global para el sistema de sueño (inyectada desde Alisha_IA.py)
_sistema_sueno = None


@app.route("/api/lock", methods=["GET"])
def get_lock():
    from pc_controller import esta_bloqueado
    return jsonify({"bloqueado": esta_bloqueado()})


@app.route("/api/lock", methods=["POST"])
def set_lock():
    from pc_controller import set_bloqueado
    data = request.json or {}
    valor = data.get("bloqueado", True)
    mensaje = set_bloqueado(valor)
    socketio.emit("lock_state", {"bloqueado": valor})
    return jsonify({"ok": True, "bloqueado": valor, "mensaje": mensaje})


# ---------------------------------------------------------------------------
# Helper — mapea EmotionalState del brain a string para Live2D
# ---------------------------------------------------------------------------

def _map_brain_emotion(state) -> str:
    """Convierte EmotionalState del brain al string que usa cabina_virtual."""
    if state.dopamina > 0.85:
        return "entusiasmo"
    if state.flow > 0.6:
        return "alegría"
    if state.tension > 0.5:
        return "preocupación"
    if state.irritabilidad > 0.5:
        return "frustración"
    if state.dopamina < 0.3:
        return "cansancio"
    return "neutral"


# ---------------------------------------------------------------------------
# Detección y ejecución de acciones físicas desde el brain
# ---------------------------------------------------------------------------

# Palabras clave que indican que el usuario quiere control físico del PC
_KW_ESCRIBIR = {
    "escribí", "escribi", "escribe", "escribir", "escribime",
    "anotá", "anota", "anotar", "anotame",
    "poné", "pone", "pon", "poner",
    "tipea", "tipear", "ingresá", "ingresa", "ingresa",
    "redacta", "redactá", "redactar",
    "escribe en", "escribi en", "escribí en",
}
_KW_ABRIR = {
    "abrí", "abri", "abre", "abrir",
    "lanzá", "lanza", "lanzar",
    "iniciá", "inicia", "iniciar",
    "ejecutá", "ejecuta", "ejecutar",
    "abrime", "abrile",
}
_KW_APPS = {
    "bloc de notas": "notepad",
    "notepad":       "notepad",
    "word":          "word",
    "excel":         "excel",
    "powerpoint":    "powerpoint",
    "vscode":        "vscode",
    "vs code":       "vscode",
    "chrome":        "chrome",
    "edge":          "edge",
    "calculadora":   "calc",
    "paint":         "paint",
    "explorador":    "explorer",
    "spotify":       "spotify",
}


def _detectar_accion_fisica(mensaje_usuario: str, respuesta_ia: str) -> dict | None:
    """
    Detecta si el usuario pidió una acción física (escribir en app, abrir app, etc.)
    Retorna un dict con la acción a ejecutar, o None si no hay acción física.
    """
    msg = mensaje_usuario.lower()

    # ── Detectar "escribí X en [app]" ────────────────────────────────────────
    tiene_escribir = any(kw in msg for kw in _KW_ESCRIBIR)
    if tiene_escribir:
        # Detectar app destino
        app_destino = ""
        ventana_destino = ""
        for kw_app, app_cmd in _KW_APPS.items():
            if kw_app in msg:
                app_destino = app_cmd
                ventana_destino = kw_app
                break

        # Extraer el texto a escribir del mensaje del usuario
        # Buscar patrones como: "escribí 'hola mundo'" o "escribí hola mundo en el bloc"
        import re
        texto_match = re.search(
            r'(?:escribí|escribe|escribir|anotá|anota|poné|pon|tipea)\s+["\']?(.+?)["\']?\s*(?:en\s+\w+|$)',
            msg, re.IGNORECASE
        )
        texto_escribir = ""
        if texto_match:
            texto_escribir = texto_match.group(1).strip()
            # Limpiar palabras de app del texto
            for kw_app in _KW_APPS:
                texto_escribir = texto_escribir.replace(kw_app, "").strip()

        if texto_escribir or app_destino:
            return {
                "tipo": "escribir",
                "texto": texto_escribir or "Hola, soy Alisha.",
                "ventana": ventana_destino,
                "app": app_destino,
            }

    # ── Detectar "abrí [app]" ─────────────────────────────────────────────────
    tiene_abrir = any(kw in msg for kw in _KW_ABRIR)
    if tiene_abrir:
        for kw_app, app_cmd in _KW_APPS.items():
            if kw_app in msg:
                return {
                    "tipo": "abrir",
                    "app": app_cmd,
                    "ventana": kw_app,
                }

    return None


# ---------------------------------------------------------------------------
# Generación de título de sesión con Gemini (async, no bloquea)
# ---------------------------------------------------------------------------

_titulo_sesion_generado = False   # solo generar una vez por sesión


# ---------------------------------------------------------------------------
# Análisis de intención — Alisha propone acciones proactivas
# ---------------------------------------------------------------------------

# Patrones que indican que el usuario necesita ayuda concreta
_INTENT_AYUDA = {
    "ayudame", "ayúdame", "no entiendo", "no sé", "no se",
    "tengo un error", "hay un error", "me da error", "falla",
    "cómo hago", "como hago", "cómo se hace", "como se hace",
    "qué significa", "que significa", "explicame", "explicá",
    "no funciona", "no me sale", "no me anda",
}
_INTENT_BUSCAR = {
    "buscá", "busca", "buscar", "investigá", "investiga",
    "qué hay sobre", "que hay sobre", "info sobre", "información sobre",
    "recursos de", "ejemplos de", "referencias de",
}
_INTENT_ESCRIBIR = {
    "escribí", "escribe", "anotá", "anota", "redactá", "redacta",
    "hacé un", "hace un", "creá un", "crea un",
}


def _analizar_intencion_y_proponer(mensaje: str, respuesta_ia: str) -> dict | None:
    """
    Analiza el mensaje del usuario y decide si Alisha debe proponer una acción.
    """
    msg = mensaje.lower()

    # ── Comando de impresión ──────────────────────────────────────────────────
    _INTENT_IMPRIMIR = ["imprimí", "imprimi", "imprime", "imprimir", "mandar a imprimir",
                        "manda a imprimir", "print"]
    if any(kw in msg for kw in _INTENT_IMPRIMIR):
        # Detectar tipo de archivo
        tipo = "pdf"
        if any(w in msg for w in ["word", "docx", "doc", "documento"]):
            tipo = "word"
        elif any(w in msg for w in ["foto", "imagen", "image", "jpg", "png"]):
            tipo = "imagen"
        elif any(w in msg for w in ["pdf"]):
            tipo = "pdf"

        # Detectar nombre específico
        import re as _re_print
        nombre_match = _re_print.search(
            r'(?:imprimí?|imprimir|print)\s+(?:el\s+)?(?:archivo\s+)?["\']?([^"\'?]+?)["\']?\s*(?:\?|$)',
            msg
        )
        nombre = nombre_match.group(1).strip() if nombre_match else ""
        # Limpiar palabras genéricas del nombre
        for w in ["último", "ultimo", "pdf", "word", "imagen", "archivo", "el", "la", "un", "una"]:
            nombre = nombre.replace(w, "").strip()

        # Buscar el archivo inmediatamente
        try:
            from alisha_print import get_print_manager
            pm = get_print_manager()
            resultado = pm.solicitar_impresion(tipo=tipo, nombre=nombre if nombre else None)
            if resultado.get("encontrado"):
                return {
                    "mensaje": resultado["mensaje_confirmacion"],
                    "accion_id": "confirmar_impresion",
                    "contexto": resultado,
                    "botones": ["Sí, imprimilo", "No, cancelar"],
                }
            else:
                return {
                    "mensaje": resultado.get("mensaje", "No encontré archivos para imprimir."),
                    "accion_id": None,
                    "contexto": {},
                    "botones": [],
                }
        except Exception:
            pass

    # ── Error o problema técnico → ofrecer buscar solución ───────────────────
    tiene_error = any(kw in msg for kw in _INTENT_AYUDA)
    tiene_codigo = any(c in mensaje for c in ["error:", "traceback", "exception",
                                               "undefined", "null", "NaN", "404",
                                               "500", "failed", "cannot"])

    if tiene_error or tiene_codigo:
        query = mensaje[:80].strip()
        return {
            "mensaje": "¿Querés que busque la solución en Google y te la escriba en el Bloc de Notas?",
            "accion_id": "buscar_en_web",
            "contexto": {"query": f"solución {query}"},
            "botones": ["Sí, buscalo", "No gracias"],
        }

    # ── Pedido de investigación → ofrecer investigar ─────────────────────────
    tiene_buscar = any(kw in msg for kw in _INTENT_BUSCAR)
    if tiene_buscar:
        import re
        tema_match = re.search(
            r'(?:buscá?|buscar|investigá?|info sobre|recursos de|ejemplos de)\s+(.+?)(?:\?|$)',
            msg
        )
        tema = tema_match.group(1).strip() if tema_match else mensaje[:60]
        return {
            "mensaje": f"¿Querés que investigue '{tema}' y te traiga un resumen listo?",
            "accion_id": "investigar_y_resumir",
            "contexto": {"tema": tema},
            "botones": ["Sí, investigalo", "No gracias"],
        }

    # ── Pedido de escritura → ofrecer escribir en app ────────────────────────
    tiene_escribir = any(kw in msg for kw in _INTENT_ESCRIBIR)
    if tiene_escribir and len(respuesta_ia) > 50:
        return {
            "mensaje": "¿Querés que te escriba esto en el Bloc de Notas?",
            "accion_id": "escribir_solucion",
            "contexto": {"texto": respuesta_ia, "app": "bloc de notas"},
            "botones": ["Sí, escribilo", "No gracias"],
        }

    return None


def _generar_titulo_sesion_async(entrada: str, respuesta: str) -> None:
    """
    Genera un título corto (3 palabras) para la sesión actual usando el brain.
    Se llama en hilo daemon para no bloquear la respuesta.
    Solo se ejecuta una vez por sesión.
    """
    global _titulo_sesion_generado
    if _titulo_sesion_generado:
        return
    _titulo_sesion_generado = True

    def _generar():
        try:
            if not _MEMORY_DB_OK or not _memory_db or _session_id < 0:
                return
            if not _BRAIN_OK or not _brain:
                palabras = entrada.split()[:3]
                titulo = " ".join(palabras).capitalize()
                _memory_db.end_session(_session_id, titulo)
                return

            prompt = (
                f"Generá un título de exactamente 3 palabras en español para esta conversación. "
                f"Solo las 3 palabras, sin puntuación ni explicación.\n"
                f"Mensaje: {entrada[:100]}\nRespuesta: {respuesta[:100]}"
            )
            resp = _brain.process(prompt)
            titulo = resp.content.strip()
            palabras = titulo.split()[:3]
            titulo_final = " ".join(palabras)
            if titulo_final:
                _memory_db.end_session(_session_id, titulo_final)
                print(f"[WebApp] ✓ Título de sesión: '{titulo_final}'")
        except Exception as e:
            print(f"[WebApp] Error generando título: {e}")

    threading.Thread(target=_generar, daemon=True).start()


def _generar_titulo_automatico_async(entrada: str, respuesta: str) -> None:
    """
    Genera un título descriptivo tras 3 mensajes usando el contexto completo.
    Más preciso que el título inicial — usa los primeros 3 intercambios.
    """
    def _generar():
        try:
            if not _MEMORY_DB_OK or not _memory_db or _session_id < 0:
                return
            # Cargar los 3 mensajes de esta sesión
            mensajes = _memory_db.load_by_session(_session_id, n=3)
            if not mensajes:
                return
            contexto = " | ".join(m.get("entrada", "")[:60] for m in mensajes)

            if _BRAIN_OK and _brain:
                prompt = (
                    f"Analizá estos mensajes y generá un título descriptivo de 3-5 palabras "
                    f"en español para esta conversación. Solo el título, sin puntuación extra.\n"
                    f"Mensajes: {contexto}"
                )
                resp = _brain.process(prompt)
                titulo = resp.content.strip().split("\n")[0][:60]
            else:
                # Fallback: primeras palabras del primer mensaje
                titulo = " ".join(mensajes[0].get("entrada", "").split()[:4]).capitalize()

            if titulo:
                _memory_db.update_session_title(_session_id, titulo)
                # Notificar al frontend para actualizar el sidebar
                socketio.emit("session_title_updated", {
                    "session_id": _session_id,
                    "titulo": titulo,
                })
                print(f"[WebApp] ✓ Título automático: '{titulo}'")
        except Exception as e:
            print(f"[WebApp] Error en título automático: {e}")

    threading.Thread(target=_generar, daemon=True).start()


def _ejecutar_accion_fisica(accion: dict, socketio_inst) -> None:
    """
    Ejecuta una acción física real en el PC.
    Se llama DESPUÉS de que el TTS termina para no interferir con el audio.
    """
    tipo = accion.get("tipo")

    try:
        from actions import enfocar_ventana, abrir_app, escribir_texto
        from pc_controller import esta_bloqueado

        # Verificar que el control no esté bloqueado
        if esta_bloqueado():
            socketio_inst.emit("respuesta", {
                "texto": "El control del PC está bloqueado. Presioná Ctrl+Shift+L para desbloquearlo.",
                "estado_emocional": "preocupación",
            })
            return

        if tipo == "abrir":
            app = accion.get("app", "")
            ventana = accion.get("ventana", app)
            socketio_inst.emit("respuesta", {
                "texto": f"Abriendo {ventana}...",
                "estado_emocional": "curiosidad",
            })
            abrir_app(app)
            import time; time.sleep(2.0)

        elif tipo == "escribir":
            texto = accion.get("texto", "")
            ventana = accion.get("ventana", "")
            app = accion.get("app", "")

            if not texto:
                return

            # Notificar que va a tomar control
            socketio_inst.emit("respuesta", {
                "texto": f"Moviendo el mouse y tomando el foco{'de ' + ventana if ventana else ''}...",
                "estado_emocional": "curiosidad",
            })

            # Si hay app destino, abrirla/enfocarla
            if ventana:
                enfocado = enfocar_ventana(ventana, abrir_si_no_existe=app)
                if not enfocado:
                    socketio_inst.emit("respuesta", {
                        "texto": f"No pude encontrar '{ventana}'. ¿Está abierta?",
                        "estado_emocional": "preocupación",
                    })
                    return
            else:
                # Sin app específica: usar la ventana activa (no el navegador)
                import time; time.sleep(0.5)

            # Escribir el texto
            import time as _t
            _t.sleep(0.3)
            try:
                escribir_texto(texto, ventana_destino=ventana)
                socketio_inst.emit("respuesta", {
                    "texto": f"Dale, escribí: \"{texto[:60]}{'...' if len(texto) > 60 else ''}\"",
                    "estado_emocional": "alegría",
                })
            except Exception as write_err:
                socketio_inst.emit("respuesta", {
                    "texto": f"Che Cami, intenté escribir pero Windows no me dejó: {write_err}. ¿Tenés la ventana abierta?",
                    "estado_emocional": "frustración",
                })
                return

    except Exception as e:
        print(f"[WebApp] Error ejecutando acción física: {e}")
        socketio_inst.emit("respuesta", {
            "texto": f"Che, intenté hacer eso pero algo falló: {e}. Avisame si querés que lo intente de otra forma.",
            "estado_emocional": "frustración",
        })


# ---------------------------------------------------------------------------
# WebSocket — mensajes en tiempo real
# ---------------------------------------------------------------------------

@socketio.on("mensaje")
def handle_mensaje(data):
    texto = data.get("texto", "").strip()
    if not texto:
        return

    # Reacción inmediata del modelo 2D — no esperar al procesamiento
    try:
        from assistant_state import actualizar_estado
        actualizar_estado(estado="curiosidad", modo="THINKING", hablando=False)
    except Exception:
        pass

    global _identidad, _memoria

    def procesar():
        global _identidad, _memoria
        with _lock:
            try:
                # Indicar que está pensando + activar animación de lectura
                from assistant_state import actualizar_estado
                actualizar_estado(modo="THINKING", hablando=False)
                socketio.emit("pensando", {"activo": True})

                # ── Usar HybridIntelligenceCore si está disponible ────────────
                if _BRAIN_OK and _brain:
                    _idle_watcher.register_interaction()
                    # Resetear cooldown de silencio cuando Cami habla
                    try:
                        from alisha_silencio import registrar_interaccion_usuario
                        registrar_interaccion_usuario()
                    except Exception:
                        pass

                    # Enriquecer query con contexto visual si corresponde
                    texto_enriquecido = texto
                    if _VISION_OK and _vision:
                        texto_enriquecido = enrich_query_with_vision(texto, _vision)
                        if texto_enriquecido != texto:
                            print(f"[WebApp] 👁 Query enriquecida con visión")

                    # Agregar metadatos de medios (Spotify/YouTube) como contexto prioritario
                    try:
                        from alisha_media import get_media_description
                        media_desc = get_media_description()
                        if media_desc:
                            texto_enriquecido = (
                                f"{texto_enriquecido}\n\n"
                                f"[Contexto de medios activos: {media_desc}]"
                            )
                    except Exception:
                        pass

                    # Agregar ventana activa como contexto de actividad
                    try:
                        import ctypes, ctypes.wintypes
                        hwnd = ctypes.windll.user32.GetForegroundWindow()
                        buf  = ctypes.create_unicode_buffer(256)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                        titulo_ventana = buf.value.strip()
                        if titulo_ventana and "alisha" not in titulo_ventana.lower():
                            # Interpretar semánticamente el título
                            from vision_engine import detectar_rol
                            rol = detectar_rol(titulo_ventana)
                            ctx_actividad = f"[Actividad actual: '{titulo_ventana}' — Alisha actúa como {rol['descripcion']}]"
                            texto_enriquecido = f"{texto_enriquecido}\n\n{ctx_actividad}"
                    except Exception:
                        pass

                    brain_response = _brain.process(texto_enriquecido)
                    respuesta   = brain_response.content
                    estado_emo  = _map_brain_emotion(brain_response.emotional_state)
                    engine_used = brain_response.engine_used
                    _sarcasm    = round(brain_response.sarcasm_score, 2)

                    # ── Análisis de intención — proponer acción proactiva ─────
                    # Si el usuario pide ayuda con algo concreto, Alisha propone
                    # actuar ANTES de que el usuario tenga que pedírselo.
                    _propuesta = _analizar_intencion_y_proponer(texto, respuesta)
                    if _propuesta:
                        # Emitir propuesta con botones de confirmación
                        socketio.emit("propuesta_accion", _propuesta)

                    # ── Detectar y ejecutar acciones físicas desde la respuesta ──
                    # El brain puede indicar acciones en su respuesta.
                    # Las detectamos aquí y las ejecutamos DESPUÉS del TTS.
                    _accion_fisica = _detectar_accion_fisica(texto, respuesta)
                    if _accion_fisica:
                        # Ejecutar en hilo separado DESPUÉS del audio
                        def _ejecutar_accion_diferida(accion_info):
                            import time as _t
                            palabras = len(respuesta.split())
                            duracion_tts = max(1.5, (palabras / 150) * 60)
                            _t.sleep(duracion_tts + 0.5)  # esperar que termine el audio
                            _ejecutar_accion_fisica(accion_info, socketio)
                        threading.Thread(
                            target=_ejecutar_accion_diferida,
                            args=(_accion_fisica,),
                            daemon=True
                        ).start()

                    # ── Escribir sarcasm_score en chibi_state ANTES de hablar ─
                    try:
                        import json as _json
                        from config import DATA_DIR
                        _sf = DATA_DIR / "chibi_state.json"
                        _sd = _json.loads(_sf.read_text(encoding="utf-8")) if _sf.exists() else {}
                        _sd["sarcasm_score"] = _sarcasm
                        _sd["estado"]        = estado_emo
                        _sd["hablando"]      = False
                        _sf.write_text(_json.dumps(_sd, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass

                    # Emitir indicador de motor al frontend
                    socketio.emit("engine_indicator", {
                        "engine": engine_used,
                        "sarcasm_score": _sarcasm,
                    })
                else:
                    # Fallback al sistema original
                    _identidad, _memoria, respuesta = procesar_turno(texto, _identidad, _memoria, _emo)
                    _identidad = evaluar_evolucion(_identidad, _memoria)
                    estado_emo = _emo.obtener_estado_actual().get("estado", "neutral")
                    engine_used = "legacy"

                # Actualizar estado del personaje con la emoción y marcar hablando
                actualizar_estado(estado=estado_emo, hablando=True, texto=respuesta, modo="IDLE")
            except Exception as e:
                respuesta = f"Ups, algo salió mal: {e}"
                estado_emo = "neutral"
                from assistant_state import actualizar_estado
                actualizar_estado(estado="neutral", hablando=False, modo="IDLE")

        socketio.emit("pensando", {"activo": False})

        # ── Guardar en SQLite INMEDIATAMENTE — antes de enviar al frontend ────
        if _MEMORY_DB_OK and _memory_db:
            try:
                _memory_db.save_conversation(
                    entrada=texto,
                    respuesta=respuesta,
                    estado_emocional=estado_emo,
                    session_id=_session_id if _session_id > 0 else None,
                )
                # Generar título de sesión si es la primera conversación
                _generar_titulo_sesion_async(texto, respuesta)
            except Exception:
                pass

        # ── XP de confianza por interacción completada ────────────────────────
        try:
            from alisha_trust import agregar_xp as _trust_xp
            estado_trust = _trust_xp("tarea_completada")
            socketio.emit("trust_update", estado_trust)
            # Log cada 5 tareas
            if estado_trust.get("tareas_completadas", 0) % 5 == 0:
                from alisha_trust import log_estado as _trust_log
                _trust_log()
        except Exception:
            pass

        # ── Generar título automático tras 3 mensajes ─────────────────────────
        global _session_msg_count
        _session_msg_count += 1
        if _session_msg_count == 3 and _session_id > 0:
            _generar_titulo_automatico_async(texto, respuesta)

        # ── TTS primero — luego sincronizar el texto con el audio ─────────
        _vision_ctx = False
        if _VISION_OK and _vision:
            snap = _vision.get_last_snapshot()
            _vision_ctx = snap is not None and snap.is_distraction

        _sarcasm = 0.0
        if _BRAIN_OK and _brain:
            try:
                _sarcasm = getattr(_brain, '_last_sarcasm_score', 0.0)
            except Exception:
                pass

        # ── Filtro de limpieza — eliminar TOOL_CALL y texto técnico ─────────
        import re as _re
        respuesta = _re.sub(r'TOOL_CALL:\s*\w+\s*\([^)]*\)', '', respuesta)
        respuesta = _re.sub(r'\[Resultado de [^\]]+\]:[^\n]*\n?', '', respuesta)
        respuesta = _re.sub(r'\[Brain\][^\n]*\n?', '', respuesta)
        respuesta = _re.sub(r'\[WebApp\][^\n]*\n?', '', respuesta)
        respuesta = _re.sub(r'\n{3,}', '\n\n', respuesta).strip()

        # ── Lanzar TTS y esperar a que empiece antes de escribir ─────────────
        _audio_iniciado = threading.Event()

        def _hablar_y_señalar():
            """Habla y señala cuando el audio empieza."""
            try:
                if _AVS_OK and _avs:
                    _audio_iniciado.set()
                    _avs.speak(
                        respuesta,
                        sarcasm_score=_sarcasm,
                        emotional_state=estado_emo,
                        vision_context=_vision_ctx,
                        async_mode=True,
                    )
                else:
                    from tts_engine import speak as _speak_tts
                    _audio_iniciado.set()
                    _speak_tts(respuesta)
            except Exception:
                _audio_iniciado.set()

        threading.Thread(target=_hablar_y_señalar, daemon=True).start()

        # Esperar máximo 1.5s a que el audio empiece
        _audio_iniciado.wait(timeout=1.5)

        # ── Streaming de texto sincronizado con word timestamps ───────────────
        #
        # Estrategia A (precisa): edge-tts genera WordBoundary events con el
        # offset exacto de cada palabra. Los leemos del bridge y emitimos cada
        # palabra en el momento exacto en que el audio la pronuncia.
        #
        # Estrategia B (fallback): si no hay timestamps, usamos duración
        # estimada con pausas inteligentes en puntuación.

        import time as _t

        socketio.emit("respuesta_inicio", {"estado_emocional": estado_emo})

        # Intentar Estrategia A — word timestamps de edge-tts
        _usó_timestamps = False
        try:
            import alisha_bridge as _bridge
            _timestamps = list(_bridge.WORD_TIMESTAMPS)   # copia para no mutar
            _audio_start = _bridge.AUDIO_START_TS

            if _timestamps and _audio_start > 0:
                _usó_timestamps = True
                # Esperar a que el audio realmente empiece (puede haber latencia)
                _ahora = _t.time()
                _espera = _audio_start - _ahora
                if _espera > 0:
                    _t.sleep(_espera)

                # Emitir cada palabra en su timestamp exacto
                _t0 = _bridge.AUDIO_START_TS  # re-leer por si cambió
                for i, entry in enumerate(_timestamps):
                    word    = entry["word"]
                    offset  = entry["offset_s"]

                    # Calcular cuándo debe aparecer esta palabra
                    _target = _t0 + offset
                    _now    = _t.time()
                    _wait   = _target - _now

                    if _wait > 0:
                        _t.sleep(_wait)

                    # Emitir la palabra + espacio
                    socketio.emit("respuesta_chunk", {"chunk": word + " "})

                # Emitir cualquier texto residual que no esté en los timestamps
                # (puntuación, caracteres especiales)
                palabras_ts = {e["word"] for e in _timestamps}
                residual = ""
                for tok in respuesta.split():
                    tok_limpio = tok.strip(".,;:!?¿¡")
                    if tok_limpio not in palabras_ts:
                        residual += tok + " "
                if residual.strip():
                    socketio.emit("respuesta_chunk", {"chunk": residual})

        except Exception:
            _usó_timestamps = False

        # Estrategia B — fallback con pausas inteligentes
        if not _usó_timestamps:
            total_chars = len(respuesta)
            palabras    = len(respuesta.split())
            duracion_audio = max(1.5, (palabras / 150) * 60)
            delay_por_char = duracion_audio / max(total_chars, 1)
            delay_por_char = max(0.01, min(0.06, delay_por_char))

            i = 0
            while i < total_chars:
                char = respuesta[i]
                if char in '.!?':
                    socketio.emit("respuesta_chunk", {"chunk": char})
                    _t.sleep(delay_por_char * 4)   # pausa de respiración
                    i += 1
                elif char == ',':
                    socketio.emit("respuesta_chunk", {"chunk": char})
                    _t.sleep(delay_por_char * 2)   # pausa breve
                    i += 1
                else:
                    chunk = respuesta[i:i + 2]
                    socketio.emit("respuesta_chunk", {"chunk": chunk})
                    _t.sleep(delay_por_char * len(chunk))
                    i += len(chunk)

        socketio.emit("respuesta_fin", {
            "texto": respuesta,
            "estado_emocional": estado_emo,
        })

        # Calcular duración para apagar hablando
        palabras       = len(respuesta.split())
        duracion_audio = max(1.5, (palabras / 150) * 60)

        def _stop_hablando():
            from assistant_state import actualizar_estado
            actualizar_estado(hablando=False)
        threading.Timer(duracion_audio + 1.0, _stop_hablando).start()

    threading.Thread(target=procesar, daemon=True).start()

    # ── Timeout de seguridad — si no responde en 45s, limpiar UI ─────────────
    def _timeout_check():
        import time as _t
        _t.sleep(45)
        # Si todavía está en modo THINKING, algo falló
        try:
            from assistant_state import cargar_estado
            estado = cargar_estado()
            if estado.get("modo") == "THINKING":
                from assistant_state import actualizar_estado
                actualizar_estado(modo="IDLE", hablando=False)
                socketio.emit("pensando", {"activo": False})
                socketio.emit("respuesta", {
                    "texto": "Che, se me trabó una neurona digital. Preguntame de nuevo.",
                    "estado_emocional": "frustración",
                })
                # Gesto de frustración en el modelo 2D
                try:
                    from brain import get_brain
                    get_brain().gestures.trigger_sarcastic_mode()
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_timeout_check, daemon=True).start()


@socketio.on("connect")
def on_connect():
    perfil = _memoria.get("perfil", {})
    emo_estado = _emo.obtener_estado_actual() if _emo else {"estado": "neutral"}
    # Asegurar identidad correcta: usuario siempre es Cami, nunca Alisha
    nombre_usuario = perfil.get("nombre", "") or "Cami"
    if nombre_usuario.lower() == "alisha":
        nombre_usuario = "Cami"
    emit("estado_inicial", {
        "nombre_ia":        _identidad.get("nombre", "IA"),
        "nombre_usuario":   nombre_usuario,
        "estado_emocional": emo_estado.get("estado", "neutral"),
        "session_id":       _session_id if _session_id > 0 else None,
    })
    # Emitir estado de confianza al conectar
    try:
        from alisha_trust import get_estado as _trust_estado
        emit("trust_update", _trust_estado())
    except Exception:
        pass


@socketio.on("disconnect")
def on_disconnect():
    pass  # reconexión automática manejada por socket.io client


# ── Trust System endpoints ────────────────────────────────────────────────────

@app.route("/api/trust", methods=["GET"])
def get_trust():
    """Estado actual del sistema de confianza."""
    try:
        from alisha_trust import get_estado
        return jsonify(get_estado())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/trust/xp", methods=["POST"])
def add_trust_xp():
    """Agrega XP manualmente (para testing o confirmaciones del usuario)."""
    data   = request.json or {}
    evento = data.get("evento", "confirmacion_usuario")
    try:
        from alisha_trust import agregar_xp
        estado = agregar_xp(evento)
        socketio.emit("trust_update", estado)
        return jsonify(estado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Endpoints de Impresión ────────────────────────────────────────────────────

@app.route("/api/imprimir/buscar", methods=["POST"])
def buscar_para_imprimir():
    """Busca y prepara un archivo. NO imprime — solo abre la carpeta."""
    data   = request.json or {}
    tipo   = data.get("tipo", "pdf")
    nombre = data.get("nombre", "")
    try:
        from alisha_print import get_print_manager
        pm = get_print_manager()
        resultado = pm.solicitar_preparacion(tipo=tipo, nombre=nombre if nombre else None)
        if resultado.get("encontrado"):
            socketio.emit("propuesta_accion", {
                "mensaje": resultado["mensaje"],
                "accion_id": "abrir_para_imprimir",
                "contexto": resultado,
                "botones": ["Sí, abrí la carpeta", "No gracias"],
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/imprimir/abrir", methods=["POST"])
def abrir_para_imprimir():
    """Abre el Explorador con el archivo listo. El usuario imprime manualmente."""
    try:
        from alisha_print import get_print_manager
        pm = get_print_manager()
        resultado = pm.abrir_para_usuario()
        socketio.emit("respuesta", {
            "texto": resultado["mensaje"],
            "estado_emocional": "alegría" if resultado["ok"] else "frustración",
        })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/imprimir/confirmar", methods=["POST"])
def confirmar_impresion():
    """Alias seguro → abre carpeta, nunca imprime directamente."""
    try:
        from alisha_print import get_print_manager
        pm = get_print_manager()
        resultado = pm.abrir_para_usuario()
        socketio.emit("respuesta", {
            "texto": resultado["mensaje"],
            "estado_emocional": "alegría" if resultado["ok"] else "frustración",
        })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/imprimir/cancelar", methods=["POST"])
def cancelar_impresion():
    try:
        from alisha_print import get_print_manager
        resultado = get_print_manager().cancelar()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/imprimir/recientes", methods=["GET"])
def listar_imprimibles():
    tipo = request.args.get("tipo", "cualquiera")
    try:
        from alisha_print import get_print_manager
        archivos = get_print_manager().listar_recientes(tipo=tipo)
        return jsonify(archivos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/impresoras", methods=["GET"])
def listar_impresoras():
    try:
        from alisha_print import listar_impresoras as _listar, get_impresora_default
        return jsonify({"impresoras": _listar(), "default": get_impresora_default()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/salud", methods=["GET"])
def get_salud_sistema():
    """Reporte de salud del sistema — CPU y RAM de Alisha."""
    try:
        from alisha_health import get_uso_recursos
        return jsonify(get_uso_recursos())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sugerencia/rechazar", methods=["POST"])
def rechazar_sugerencia():
    """Registra que Cami rechazó una sugerencia — aprendizaje gradual."""
    data      = request.json or {}
    accion_id = data.get("accion_id", "").replace("sugerencia_", "")
    tipo      = data.get("tipo", "")
    try:
        from alisha_sugerencias import get_suggestion_engine
        get_suggestion_engine().registrar_respuesta(accion_id, tipo, acepto=False)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/landing")
def landing_page():
    """Sirve la landing page de Alisha."""
    from flask import send_from_directory
    return send_from_directory("landing", "index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@app.route("/api/generar_imagen", methods=["POST"])
def generar_imagen():
    """
    Genera una imagen con Google Imagen 3 API.
    Retorna la imagen en base64 para mostrar inline en el chat.
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Necesito una descripción para generar la imagen."}), 400

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "GOOGLE_API_KEY no configurada en .env"}), 500

    try:
        import requests as _req
        import base64 as _b64

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"imagen-3.0-generate-001:predict?key={api_key}"
        )
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1}
        }
        resp = _req.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            return jsonify({"error": f"Error de API: {resp.status_code} — {resp.text[:200]}"}), 500

        result = resp.json()
        predictions = result.get("predictions", [])
        if not predictions:
            return jsonify({"error": "La API no devolvió ninguna imagen."}), 500

        imagen_b64 = predictions[0].get("bytesBase64Encoded", "")
        if not imagen_b64:
            return jsonify({"error": "Respuesta vacía de la API."}), 500

        return jsonify({"imagen_base64": imagen_b64, "prompt": prompt})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    _inicializar()
    print("\n🌐 Alisha - Interfaz Web")
    print("=" * 30)
    print("📍 Servidor: http://localhost:5000")
    print("📄 Landing:  http://localhost:5000/landing")
    print("💡 Presiona Ctrl+C para cerrar")
    print()
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)
