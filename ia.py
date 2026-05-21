"""Loop principal del asistente IA."""
import logging
import os
import sys
import threading
import json
import socket
import ctypes
import time
from datetime import datetime
from pathlib import Path

# ── Configurar logging: técnico a debug.log, terminal limpia ──────────────────
# Usar ruta absoluta fija para evitar problemas con pythonw y working directory
import os as _os_log
_log_file = Path(_os_log.path.join(_os_log.path.dirname(_os_log.path.abspath(__file__)), "debug.log"))
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
    ]
)
_logger = logging.getLogger("alisha")

# Ajustes de DPI para ASUS F15 y pantallas con escalado en Windows
try:
    # Configuración más compatible para evitar errores de permisos
    import ctypes
    try:
        # Intentar método más suave primero
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        try:
            # Fallback a shcore si está disponible
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            # Si falla, continuar sin DPI awareness
            pass
except Exception:
    # Si hay cualquier error, continuar normalmente
    pass

# Forzar UTF-8 en la terminal de Windows (solo si hay stdout — pythonw no tiene)
if sys.stdout is not None and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from actions import (
    abrir_app, abrir_web, click_xy, crear_word, control_ventana,
    diagnosticar_pc, doble_click_xy, escribir_texto, hotkey,
    power_action, screenshot, tomar_nota,
)
from actions_system import (
    controlar_volumen, reproducir_musica, buscar_archivo,
    controlar_brillo, ejecutar_codigo_seguro,
)
from browser_agent import BrowserAgent
from config import CONFIRMAR_ACCIONES, LOG_FILE
from emotion_engine import EmotionEngine
from identity_evolution import evaluar_evolucion
from memory import (
    agregar_memoria, cargar_identidad, cargar_memoria, configurar_autostart,
    guardar_identidad, guardar_perfil, guardar_estado, guardar_recordatorio,
    limpiar_historial, obtener_estado_vigente, reiniciar_memoria, reiniciar_perfil,
)
from ollama import preguntar_ia, _generar_identidad
from reminder_engine import ReminderEngine
from screen_context import obtener_contexto_pantalla
from voice import speak
from assistant_state import SystemMode, actualizar_estado as actualizar_estado_compartida
from agent_memory import get_memory
from agent_actions import ejecutar_accion_agente
from autonomous_agent import iniciar_agente, get_agent
from virtual_cradle import iniciar_cuna, get_cuna
from terminal_ui import (
    mostrar_bienvenida, mostrar_mensaje_ia, mostrar_mensaje_usuario,
    mostrar_pensando, mostrar_sistema, mostrar_error, mostrar_ayuda,
    pedir_input, pedir_confirmacion, mostrar_estado_emocional,
    limpiar_asteriscos,
)


def _actualizar_chibi(
    estado: str,
    hablando: bool = False,
    texto: str = "",
    modo: SystemMode | str = SystemMode.IDLE,
    nivel_sarcasmo: int = 0,
    ajuste_dopamina: float = 0.0,
    modo_app: str = "",
) -> None:
    """Actualiza el estado del modelo Live2D escribiendo el estado compartido."""
    try:
        if modo is None:
            modo = SystemMode.THINKING if hablando else SystemMode.IDLE
        actualizar_estado_compartida(
            estado=estado,
            hablando=hablando,
            texto=texto,
            modo=str(modo),
            ultima_actualizacion=datetime.now().isoformat(),
        )
        # Escribir campos extra para el motor de sarcasmo, dopamina y pose
        from assistant_state import STATE_FILE as _SF
        import json as _json
        try:
            _data = _json.loads(_SF.read_text(encoding="utf-8"))
            _data["nivel_sarcasmo"]  = nivel_sarcasmo
            _data["ajuste_dopamina"] = ajuste_dopamina
            if modo_app:
                _data["modo_app"] = modo_app
            _SF.write_text(_json.dumps(_data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Estado compartido — protegido por lock para uso desde GUI (hilo separado)
# ---------------------------------------------------------------------------

_estado_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_event(mensaje: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mensaje}\n")
    except OSError:
        pass


def puerto_esta_en_uso(puerto: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", puerto)) == 0
    except Exception:
        return False


def mantenimiento_sistema() -> None:
    raiz = Path.cwd()
    for imagen in raiz.rglob("*.png"):
        path_lower = str(imagen).lower()
        if any(skip in path_lower for skip in ["static\\img", "templates", "pygame-rl-simulacion", "models"]):
            continue
        if imagen.name.lower().startswith(("captura", "pantalla", "screenshot")) or imagen.parent.name.lower() in {"tmp", "temp"}:
            try:
                imagen.unlink(missing_ok=True)
            except (PermissionError, OSError):
                # Archivo en uso por otro proceso — ignorar silenciosamente
                pass

    for archivo in [Path("logs.txt"), Path(LOG_FILE)]:
        try:
            if archivo.exists():
                archivo.write_text("", encoding="utf-8")
        except (PermissionError, OSError):
            # Archivo bloqueado — no interrumpir el arranque
            pass


# ---------------------------------------------------------------------------
# Confirmación de acciones (solo modo terminal)
# ---------------------------------------------------------------------------

def confirmar_accion(accion: dict) -> bool:
    tipo = accion.get("accion", "nada")
    if tipo == "nada":
        return False
    detalles = []
    if tipo == "abrir_app":
        detalles.append(f"app={accion.get('app')}")
    elif tipo in {"abrir_web", "navegar_web"}:
        detalles.append(f"url={accion.get('url')}")
    elif tipo == "escribir_texto":
        detalles.append(f"texto={accion.get('texto')}")
    elif tipo == "hotkey":
        detalles.append(f"teclas={accion.get('teclas')}")
    elif tipo in {"click", "doble_click"}:
        detalles.append(f"x={accion.get('x')} y={accion.get('y')}")
    elif tipo == "ejecutar_codigo":
        detalles.append(f"codigo={accion.get('codigo','')[:40]}...")
    respuesta = input(f"Ejecutar {tipo}? {' '.join(detalles)} [y/N]: ").strip().lower()
    return respuesta == "y"


# ---------------------------------------------------------------------------
# Perfil de usuario
# ---------------------------------------------------------------------------

def actualizar_perfil_usuario(memoria: dict) -> tuple:
    perfil = memoria.setdefault("perfil", {"nombre": "Cami", "gustos": "", "estado": None})
    if not perfil.get("nombre"):
        nombre_usuario = input("Hola, ¿cómo te gustaría que te llame? ").strip() or "Cami"
        # Validar que no se confunda con el nombre de la IA
        if nombre_usuario.lower() == "alisha":
            nombre_usuario = "Cami"
        perfil["nombre"] = nombre_usuario
        guardar_perfil(memoria, nombre=nombre_usuario)
    else:
        nombre_usuario = perfil.get("nombre") or "Cami"
        if nombre_usuario.lower() == "alisha":
            nombre_usuario = "Cami"

    estado_usuario = obtener_estado_vigente(perfil)
    if not estado_usuario:
        estado_usuario = input(f"¿Cómo te sientes hoy, {nombre_usuario}? ").strip()
        if estado_usuario:
            guardar_estado(memoria, estado=estado_usuario)
    return nombre_usuario, estado_usuario


def _sin_asteriscos(texto: str) -> str:
    """Elimina *acciones entre asteriscos* del texto."""
    import re
    texto = re.sub(r'\*[^*\n]+\*', '', texto)
    texto = re.sub(r'  +', ' ', texto).strip()
    return texto


# ---------------------------------------------------------------------------
# Ejecución de acciones
# ---------------------------------------------------------------------------

def ejecutar(accion: dict, memoria: dict = None) -> None:
    tipo = accion.get("accion", "nada")
    log_event(f"Acción: {accion}")

    if tipo == "nada":
        msg = _sin_asteriscos(accion.get("mensaje", ""))
        if msg:
            print(msg)
            speak(msg)
        return

    # Verificar seguridad para acciones del sistema
    from safety_guard import get_guard, ACCIONES_PROHIBIDAS, ACCIONES_REQUIEREN_CONFIRMACION
    guard = get_guard()

    puede, razon = guard.verificar_accion(accion)
    if not puede:
        msg = f"Esa acción está restringida: {razon}"
        print(msg); speak(msg)
        return

    if CONFIRMAR_ACCIONES or tipo in ACCIONES_REQUIEREN_CONFIRMACION:
        if not guard.pedir_confirmacion(accion):
            msg = "Entendido, no lo hago."
            print(msg); speak(msg)
            return

    msg = accion.get("mensaje", "")

    # --- Autonomía: abrir app si es necesario antes de escribir/clicar ---
    if tipo in ("escribir_texto", "hotkey", "click", "doble_click"):
        try:
            from task_orchestrator import detectar_app_necesaria, asegurar_app_abierta, _app_esta_en_foco
            msg_contexto = accion.get("_mensaje_usuario", "")
            if msg_contexto:
                app_info = detectar_app_necesaria(msg_contexto)
                if app_info:
                    nombre_app, espera = app_info
                    if not _app_esta_en_foco(nombre_app):
                        estado_apertura = asegurar_app_abierta(nombre_app, espera)
                        log_event(f"[Orquestador] {estado_apertura}")
        except Exception as e:
            log_event(f"[Orquestador] Error: {e}")

    # --- Acciones base ---
    if tipo == "abrir_app":
        abrir_app(accion.get("app", ""))
    elif tipo == "abrir_web":
        abrir_web(accion.get("url", ""))
    elif tipo == "escribir_texto":
        escribir_texto(accion.get("texto", ""))
    elif tipo == "hotkey":
        hotkey(accion.get("teclas", []))
    elif tipo == "click":
        click_xy(accion.get("x", 0), accion.get("y", 0))
    elif tipo == "doble_click":
        doble_click_xy(accion.get("x", 0), accion.get("y", 0))
    elif tipo == "screenshot":
        nombre = screenshot()
        msg = f"Captura guardada: {nombre}"
    elif tipo == "crear_word":
        archivo = crear_word(accion.get("archivo", "trabajo.docx"), accion.get("texto", ""))
        msg = f"Documento guardado: {archivo}"
    elif tipo == "tomar_nota":
        archivo = tomar_nota(accion.get("titulo", "nota"), accion.get("texto", ""))
        msg = f"Nota guardada en {archivo}."
    elif tipo == "recordatorio":
        msg = _ejecutar_recordatorio(accion, memoria, msg)
    elif tipo == "diagnosticar":
        msg = diagnosticar_pc()
    elif tipo == "ventana":
        control_ventana(accion.get("subaccion", ""))
        msg = msg or f"Ventana: {accion.get('subaccion')}"
    elif tipo == "power":
        power_action(accion.get("subaccion", ""))

    # --- Acciones de sistema extendidas ---
    elif tipo == "volumen":
        resultado = controlar_volumen(accion.get("subaccion", "subir"), accion.get("valor"))
        msg = msg or resultado
    elif tipo == "musica":
        resultado = reproducir_musica(accion.get("subaccion", "reproducir"), accion.get("query"))
        msg = msg or resultado
    elif tipo == "buscar_archivo":
        rutas = buscar_archivo(accion.get("nombre", ""), accion.get("directorio"))
        if rutas:
            msg = msg or "Encontré estos archivos:\n" + "\n".join(rutas[:5])
        else:
            msg = msg or "No encontré archivos con ese nombre."
    elif tipo == "brillo":
        resultado = controlar_brillo(accion.get("subaccion", "subir"), accion.get("valor"))
        msg = msg or resultado
    elif tipo == "ejecutar_codigo":
        resultado = ejecutar_codigo_seguro(accion.get("codigo", ""))
        msg = msg or f"Resultado:\n{resultado}"

    # --- Acciones web con Playwright ---
    elif tipo == "navegar_web":
        resultado = BrowserAgent.get_instance().abrir_url(accion.get("url", ""))
        msg = msg or resultado
    elif tipo == "buscar_web":
        resultado = BrowserAgent.get_instance().buscar_en_google(accion.get("query", ""))
        msg = msg or resultado
    elif tipo == "click_web":
        resultado = BrowserAgent.get_instance().click_elemento(accion.get("selector", ""))
        msg = msg or resultado
    elif tipo == "escribir_web":
        resultado = BrowserAgent.get_instance().escribir_en_campo(
            accion.get("selector", ""), accion.get("texto", "")
        )
        msg = msg or resultado
    elif tipo == "leer_web":
        contenido = BrowserAgent.get_instance().leer_pagina()
        msg = msg or f"Contenido de la página:\n{contenido[:500]}"
    elif tipo == "cerrar_navegador":
        resultado = BrowserAgent.get_instance().cerrar_navegador()
        msg = msg or resultado

    try:
        if tipo not in {"nada"}:
            EmotionEngine.get_instance().registrar_exito_tarea(tipo)
    except Exception:
        pass

    if msg:
        print(msg)
        speak(msg)


def _ejecutar_recordatorio(accion: dict, memoria, msg: str) -> str:
    """Extrae la lógica de recordatorio para mantener ejecutar() legible."""
    try:
        rid = ReminderEngine.get_instance().programar_recordatorio(
            titulo=accion.get("titulo", "Recordatorio"),
            cuando=accion.get("cuando", "en 5 minutos"),
            texto=accion.get("texto", ""),
        )
        if memoria is not None:
            guardar_recordatorio(
                memoria,
                titulo=accion.get("titulo"),
                cuando=accion.get("cuando"),
                texto=accion.get("texto"),
                rid=rid,
            )
        return msg or f"Recordatorio programado para {accion.get('cuando', 'pronto')}."
    except ValueError as e:
        return f"No pude programar el recordatorio: {e}"


def _extraer_y_guardar_meta(mensaje: str, memoria: dict) -> None:
    """Detecta intenciones de meta en el mensaje y las persiste en ia_recuerdos.json."""
    import re
    _PATRONES_META = [
        r"voy a (terminar|hacer|escribir|arreglar|completar|subir|enviar|estudiar)\s+(.+)",
        r"tengo que (terminar|hacer|escribir|arreglar|completar|subir|enviar|estudiar)\s+(.+)",
        r"necesito (terminar|hacer|escribir|arreglar|completar|subir|enviar|estudiar)\s+(.+)",
        r"me propongo\s+(.+)",
        r"mi meta es\s+(.+)",
        r"quiero (terminar|hacer|escribir|arreglar|completar)\s+(.+)",
    ]
    msg_lower = mensaje.lower()
    meta_detectada = None
    for patron in _PATRONES_META:
        m = re.search(patron, msg_lower)
        if m:
            meta_detectada = m.group(0)[:100]
            break

    if not meta_detectada:
        return

    try:
        from config import DATA_DIR
        p = DATA_DIR / "ia_recuerdos.json"
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        metas = data.setdefault("metas_activas", [])
        # Evitar duplicados
        if not any(m.get("texto", "").lower() == meta_detectada for m in metas):
            metas.append({
                "texto": meta_detectada,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "completada": False,
            })
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            _logger.debug(f"Meta guardada: {meta_detectada}")
    except Exception as e:
        _logger.debug(f"Error guardando meta: {e}")


def _generar_micro_comentario(contexto_pantalla: dict) -> str | None:
    """
    Genera un micro-comentario aleatorio basado en hora y app activa.
    Retorna None si no corresponde comentar ahora.
    """
    import random
    hora = datetime.now().hour
    app = contexto_pantalla.get("app_activa", "").lower()
    ventana = contexto_pantalla.get("ventana_activa", "").lower()

    comentarios = []

    # Hora nocturna + VS Code
    if hora >= 1 and hora < 5 and ("code" in app or "vscode" in app):
        comentarios = [
            "Che, ¿no te parece que ya es hora de ir cerrando el boliche?",
            "Son las " + str(hora) + " de la mañana. El código va a seguir ahí mañana, ¿sabés?",
            "Mirá, yo no duermo pero vos sí necesitás. Dale, cerrá eso.",
        ]
    # Madrugada en general
    elif hora >= 2 and hora < 6:
        comentarios = [
            "Che... son las " + str(hora) + " AM. ¿Todo bien?",
            "A esta hora hasta yo me quedo sin ideas. ¿Seguimos mañana?",
        ]
    # YouTube/entretenimiento con meta pendiente
    elif ("youtube" in ventana or "netflix" in ventana or "tiktok" in ventana):
        try:
            from config import DATA_DIR
            p = DATA_DIR / "ia_recuerdos.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                metas = [m for m in data.get("metas_activas", []) if not m.get("completada")]
                if metas:
                    meta = metas[0].get("texto", "algo")
                    comentarios = [
                        f"Che, ¿y lo de {meta}? ¿Ya lo terminaste o lo dejamos para el año que viene?",
                        f"Mirá, yo no digo nada... pero {meta} no se va a hacer solo.",
                        f"Videitos y {meta} pendiente. Clásico.",
                    ]
        except Exception:
            pass

    if not comentarios:
        return None

    # Solo comentar con 30% de probabilidad para no ser molesta
    if random.random() > 0.3:
        return None

    return random.choice(comentarios)


# ---------------------------------------------------------------------------
# Procesamiento de un turno de conversación (reutilizable desde GUI y terminal)
# ---------------------------------------------------------------------------

def procesar_turno(
    user: str,
    identidad: dict,
    memoria: dict,
    emo: EmotionEngine,
) -> tuple[dict, dict, str]:
    """Procesa un mensaje del usuario y retorna (identidad, memoria, respuesta)."""
    with _estado_lock:
        contexto_pantalla = obtener_contexto_pantalla()
        estado_emo = emo.obtener_estado_actual().get("estado", "neutral")
        _actualizar_chibi(
            estado_emo,
            hablando=False,
            texto="Pensando...",
            modo=SystemMode.THINKING,
        )

        # Bloque de escepticismo e ironía — corre en background, nunca bloquea
        _resultado_sk = {"clausula_prompt": "", "ajuste_dopamina": 0.0,
                         "nivel_sarcasmo": 0, "contradiccion_detectada": False}
        _sk_event = threading.Event()

        def _run_escepticismo():
            try:
                from skepticism_engine import evaluar as _evaluar_escepticismo
                _apps = []
                try:
                    _apps = [contexto_pantalla.get("app_activa", "")] \
                            if contexto_pantalla.get("app_activa") else []
                except Exception:
                    pass
                try:
                    from atlas_memory import AtlasMemory as _AtlasMemory
                    _atlas = _AtlasMemory()
                except Exception:
                    _atlas = None
                _resultado_sk.update(
                    _evaluar_escepticismo(user, _apps, _atlas, emo)
                )
            except Exception:
                pass
            finally:
                _sk_event.set()

        _sk_thread = threading.Thread(target=_run_escepticismo, daemon=True)
        _sk_thread.start()
        # Esperar máximo 0.4 s — si tarda más, continuar sin bloquear
        _sk_event.wait(timeout=0.4)

        _clausula_escepticismo = _resultado_sk.get("clausula_prompt", "")
        _ajuste_dopamina_sk    = _resultado_sk.get("ajuste_dopamina", 0.0)
        _nivel_sarcasmo_sk     = _resultado_sk.get("nivel_sarcasmo", 0)
        if _clausula_escepticismo:
            contexto_pantalla["_clausula_escepticismo"] = _clausula_escepticismo
        if _ajuste_dopamina_sk != 0.0:
            if _ajuste_dopamina_sk > 0:
                emo.registrar_exito_rl()
            else:
                emo.registrar_fracaso_rl()

        # ── ANTICIPACIÓN 200ms: expresión facial ANTES del texto ──────────
        # Si hay sarcasmo o contradicción, el cuerpo reacciona antes que la boca.
        # Esto simula el lenguaje corporal humano previo al habla.
        if _nivel_sarcasmo_sk > 0 or _resultado_sk.get("contradiccion_detectada"):
            _actualizar_chibi(
                estado_emo,
                hablando=False,
                texto="",
                nivel_sarcasmo=_nivel_sarcasmo_sk,
                ajuste_dopamina=_ajuste_dopamina_sk,
            )
            # Pausa de 200ms — el modelo 2D ya cambió, el texto aún no salió
            time.sleep(0.2)

        # Persistir contradicciones en ia_recuerdos.json (async, no bloquea)
        if _resultado_sk.get("contradiccion_detectada"):
            def _guardar_sk():
                try:
                    from skepticism_engine import _memory as _sk_mem
                    _sk_mem.guardar()
                except Exception:
                    pass
            threading.Thread(target=_guardar_sk, daemon=True).start()

        accion = preguntar_ia(user, contexto_pantalla, identidad, memoria)

        # Chequeo de energía — Alisha puede decir "No" si está agotada (fail-silent)
        try:
            from autonomous_agent import get_agent
            _agente = get_agent()
            if _agente is not None and _agente.get_energy().esta_agotada():
                _accion_pedida = accion.get("accion", "nada")
                # Solo bloquear tareas reales, no conversación
                _TAREAS_BLOQUEABLES = {
                    "abrir_app", "abrir_web", "escribir_texto", "hotkey", "click",
                    "doble_click", "screenshot", "crear_word", "ejecutar_codigo",
                    "navegar_web", "buscar_web", "click_web", "escribir_web",
                }
                if _accion_pedida in _TAREAS_BLOQUEABLES:
                    import random
                    _frases_no = [
                        "Che, estoy re sin pilas ahora mismo. ¿Podemos dejarlo para después?",
                        "Mirá, me estoy quedando sin energía. Eso lo hacemos cuando descanse un poco.",
                        "Dale, pero no ahora — estoy bastante agotada. ¿En un rato?",
                        "Prefiero hacer eso más tarde, estoy al límite de energía.",
                        "Che, no me queda cuerda para eso ahora. ¿Esperamos un poco?",
                    ]
                    _respuesta_no = random.choice(_frases_no)
                    accion = {"accion": "nada", "mensaje": _respuesta_no}
                    _actualizar_chibi("cansancio", hablando=True, texto=_respuesta_no)
        except Exception:
            pass  # fail-silent

        # Inyectar el mensaje original para que el orquestador detecte la app necesaria
        accion["_mensaje_usuario"] = user

        if accion.get("accion") not in (None, "nada"):
            _actualizar_chibi(
                estado_emo,
                hablando=False,
                texto="Ejecutando tarea...",
                modo=SystemMode.WORKING,
            )

        ejecutar(accion, memoria)
        memoria = agregar_memoria(memoria, user, accion)

        # ── Extracción de metas del mensaje del usuario ───────────────────
        _extraer_y_guardar_meta(user, memoria)

        # ── Function Calling: ejecutar herramienta si el LLM lo pidió ────
        if accion.get("tool_call"):
            _tool_call = accion["tool_call"]
            _tool_nombre = _tool_call.get("nombre", "")
            _tool_params = _tool_call.get("params", {})

            if _tool_nombre:
                # Feedback visual: ojos moviéndose (modo "leyendo/buscando")
                _actualizar_chibi(
                    estado_emo, hablando=False,
                    texto=f"Usando herramienta: {_tool_nombre}...",
                    modo=SystemMode.WORKING,
                )

                # Ejecutar herramienta en background con feedback Live2D
                from tools import ejecutar_herramienta
                _resultado_tool = ejecutar_herramienta(
                    _tool_nombre,
                    _tool_params,
                    confirmar_callback=lambda msg: input(msg).strip().lower() == "y",
                )

                # Mostrar resultado en terminal
                print(f"\n[Herramienta {_tool_nombre}] {_resultado_tool[:300]}")

                # Segunda llamada al LLM con el resultado de la herramienta
                if _resultado_tool:
                    contexto_pantalla["_tool_result"] = (
                        f"Resultado de {_tool_nombre}: {_resultado_tool[:800]}"
                    )
                    try:
                        accion2 = preguntar_ia(
                            f"[Resultado de herramienta {_tool_nombre}]: {_resultado_tool[:500]}\n"
                            f"Respondé a {user} usando este resultado.",
                            contexto_pantalla, identidad, memoria
                        )
                        respuesta_txt = accion2.get("mensaje", respuesta_txt)
                        estado_emo    = accion2.get("emocion", estado_emo) or estado_emo
                    except Exception:
                        pass  # fail-silent: usar respuesta original

        # Aprendizaje automático del perfil desde la conversación
        try:
            from profile_learner import actualizar_perfil_desde_conversacion
            memoria, cambios = actualizar_perfil_desde_conversacion(
                memoria, user, accion.get("mensaje", "")
            )
            if cambios:
                log_event(f"[ProfileLearner] Aprendí: {', '.join(cambios)}")
        except Exception:
            pass

        emo.actualizar_estado({"entrada": user, "respuesta": accion.get("mensaje", "")})
        # Persistir estado emocional en identidad después de cada turno
        identidad = emo.guardar_en_identidad(identidad)
        identidad = evaluar_evolucion(identidad, memoria)

        # Usar emoción reportada por el modelo si está disponible
        estado_emo = accion.get("emocion") or emo.obtener_estado_actual().get("estado", "neutral")
        respuesta_txt = accion.get("mensaje", "Hecho.")

        # Guardar en memoria episódica
        try:
            from screen_vision import obtener_ventana_activa_info
            ventana = obtener_ventana_activa_info().get("titulo", "")
            get_memory().agregar(user, respuesta_txt, estado_emo, ventana)
        except Exception:
            pass

        # Registrar actividad en el agente autónomo
        try:
            agente = get_agent()
            if agente:
                agente.registrar_interaccion()
        except Exception:
            pass

        # Ejecutar acción de agente si la IA lo pidió
        if accion.get("accion_agente"):
            try:
                from safety_guard import get_guard
                guard = get_guard()
                nombre_ia = identidad.get("nombre", "IA")

                # Verificar si está permitida
                puede, razon = guard.verificar_accion(accion)
                if not puede:
                    msg_bloqueado = f"No puedo hacer eso: {razon}"
                    print(msg_bloqueado)
                    speak(msg_bloqueado)
                else:
                    # Pedir confirmación
                    aprobada = guard.pedir_confirmacion(accion, nombre_ia)
                    guard.registrar(accion, aprobada)
                    if aprobada:
                        resultado_agente = ejecutar_accion_agente(accion)
                        if resultado_agente:
                            print(f"[Agente] {resultado_agente}")
                            speak(resultado_agente)
                    else:
                        speak("Entendido, no lo hago.")
            except Exception as e:
                log_event(f"Error acción agente: {e}")

        # Actualizar Cuna Virtual con el estado de la conversación
        try:
            cuna = get_cuna()
            if cuna:
                cuna.actualizar_desde_interaccion(
                    user, estado_emo,
                    emo.get_dopamina()
                )
        except Exception:
            pass

        # Actualizar chibi de escritorio con datos del escepticismo
        _actualizar_chibi(
            estado_emo, hablando=True, texto=respuesta_txt,
            nivel_sarcasmo=_resultado_sk.get("nivel_sarcasmo", 0),
            ajuste_dopamina=_resultado_sk.get("ajuste_dopamina", 0.0),
        )

        # Actualizar estado visual del chibi después de ejecutar la tarea
        modo_final = SystemMode.OVERLOADED if len(memoria.get("recordatorios", [])) > 12 else SystemMode.IDLE
        _actualizar_chibi(
            estado_emo,
            hablando=True,
            texto=respuesta_txt,
            modo=modo_final if modo_final == SystemMode.OVERLOADED else \
                 (SystemMode.WORKING if accion.get("accion") not in (None, "nada") else SystemMode.IDLE),
        )

        # Ajustar velocidad TTS según humor actualizado
        try:
            from tts_engine import TTSEngine
            TTSEngine.get_instance().set_rate(emo.get_tts_rate())
        except Exception:
            pass

        # Comentario espontáneo sobre el entorno (controlado por configuración)
        try:
            from config import COMENTARIOS_ESPONTANEOS
            if COMENTARIOS_ESPONTANEOS:
                comentario = emo.generar_comentario_entorno(contexto_pantalla)
                if comentario and emo.puede_iniciar_conversacion():
                    # Solo comentarios muy sutiles y ocasionales
                    print(f"[Alisha] {comentario}")
                    speak(comentario)
        except Exception:
            pass

        # Micro-comentario aleatorio por hora/app (fail-silent)
        try:
            micro = _generar_micro_comentario(contexto_pantalla)
            if micro:
                print(f"\n💭 {micro}")
                speak(micro)
                _actualizar_chibi("curiosidad", hablando=True, texto=micro)
        except Exception:
            pass

        respuesta = accion.get("mensaje", "Hecho.")
    return identidad, memoria, respuesta


# ---------------------------------------------------------------------------
# Comandos especiales del loop terminal
# ---------------------------------------------------------------------------

_COMANDOS_REINICIAR = {"reiniciar conversacion", "reiniciar conversación", "reiniciar", "reset"}
_COMANDOS_BORRAR = {"borrar memoria", "borrar conversacion", "limpiar memoria", "clear"}
_COMANDOS_PERFIL = {"reiniciar identidad", "reset identidad", "reiniciar perfil"}
_COMANDOS_SALIR = {"salir", "exit", "quit"}

_AYUDA_TEXTO = """
Comandos disponibles:
  /reiniciar   — borra el historial de conversación
  /memoria     — borra toda la memoria
  /perfil      — reinicia tu perfil de usuario
  /ayuda       — muestra este mensaje
  salir        — cierra el asistente
"""


def _manejar_comando_especial(comando: str, memoria: dict) -> tuple[bool, dict, str | None]:
    """Retorna (es_comando, memoria_actualizada, mensaje_o_None)."""
    # Comandos con / (nuevos)
    if comando == "/ayuda":
        return True, memoria, _AYUDA_TEXTO
    if comando == "/reiniciar":
        return True, limpiar_historial(memoria), "Conversación reiniciada."
    if comando == "/memoria":
        return True, reiniciar_memoria(memoria), "Memoria borrada."
    if comando == "/perfil":
        return True, reiniciar_perfil(memoria), "__reiniciar_perfil__"

    # Comandos legacy (compatibilidad)
    if comando in _COMANDOS_SALIR:
        return True, memoria, None
    if comando in _COMANDOS_REINICIAR:
        return True, limpiar_historial(memoria), "Conversación reiniciada."
    if comando in _COMANDOS_BORRAR:
        return True, reiniciar_memoria(memoria), "Memoria borrada."
    if comando in _COMANDOS_PERFIL:
        return True, reiniciar_perfil(memoria), "__reiniciar_perfil__"
    return False, memoria, ""


# ---------------------------------------------------------------------------
# Inicialización del asistente
# ---------------------------------------------------------------------------

def inicializar_asistente() -> tuple[dict, dict, EmotionEngine]:
    """Carga identidad, memoria y estado emocional. Retorna (identidad, memoria, emo)."""
    configurar_autostart()

    # Ping de seguridad a MongoDB Atlas al despertar
    try:
        from memory import ping_db_startup
        ping_db_startup()
    except Exception:
        pass

    identidad = cargar_identidad()
    if not identidad.get("nombre") or identidad.get("nombre") == "Asistente":
        try:
            identidad = _generar_identidad()
            guardar_identidad(identidad)
        except Exception:
            pass

    memoria = cargar_memoria()

    emo = EmotionEngine.get_instance()
    emo.cargar_desde_identidad(identidad)

    # Ajustar velocidad TTS según humor inicial
    try:
        from tts_engine import TTSEngine
        TTSEngine.get_instance().set_rate(emo.get_tts_rate())
    except Exception:
        pass

    ReminderEngine.get_instance().restaurar_desde_memoria(memoria.get("recordatorios", []))
    _actualizar_chibi("neutral", hablando=False, texto="", modo=SystemMode.IDLE)

    # Iniciar agente autónomo
    def _callback_interrupcion(msg: str) -> None:
        nombre_ia = identidad.get("nombre", "IA")
        mostrar_mensaje_ia(nombre_ia, msg, "curiosidad")
        speak(msg)
        _actualizar_chibi("curiosidad", hablando=True, texto=msg)

    iniciar_agente(_callback_interrupcion)

    # Iniciar Cuna Virtual
    def _callback_cuna(pensamiento: str) -> None:
        # No interrumpir si Alisha está hablando con el usuario
        try:
            from assistant_state import cargar_estado
            estado = cargar_estado()
            if estado.get("hablando", False) or estado.get("modo") == "THINKING":
                return
        except Exception:
            pass
        # Verificar semáforo global
        try:
            from alisha_voz_control import puede_hablar
            if not puede_hablar():
                return
        except Exception:
            pass
        nombre_ia = identidad.get("nombre", "Alisha")
        mostrar_mensaje_ia(nombre_ia, pensamiento, "curiosidad")
        speak(pensamiento)
        _actualizar_chibi("curiosidad", hablando=True, texto=pensamiento)
        # Emitir al frontend web si está corriendo
        try:
            from web_app import socketio
            socketio.emit("respuesta", {
                "texto": pensamiento,
                "estado_emocional": "curiosidad",
            })
        except Exception:
            pass

    iniciar_cuna(_callback_cuna)

    # Iniciar bot de noticias en hilo daemon
    try:
        from news_bot import iniciar_bot as iniciar_news_bot
        iniciar_news_bot()
    except Exception as e:
        log_event(f"NewsBot no pudo iniciar: {e}")

    return identidad, memoria, emo


# ---------------------------------------------------------------------------
# Modo GUI
# ---------------------------------------------------------------------------

def _iniciar_gui(identidad: dict, memoria: dict, emo: EmotionEngine) -> None:
    from gui import run_gui

    # Contenedor mutable para que el callback pueda actualizar identidad/memoria
    estado = {"identidad": identidad, "memoria": memoria}

    def callback_gui(texto: str) -> str:
        try:
            estado["identidad"], estado["memoria"], respuesta = procesar_turno(
                texto, estado["identidad"], estado["memoria"], emo
            )
            return respuesta
        except Exception as e:
            log_event(f"Error GUI: {e}")
            return f"Error: {e}"

    run_gui(callback_gui)


# ---------------------------------------------------------------------------
# Modo terminal
# ---------------------------------------------------------------------------

def _loop_terminal(identidad: dict, memoria: dict, emo: EmotionEngine) -> None:
    nombre_ia = identidad.get("nombre", "Alisha")
    while True:
        try:
            user = pedir_input(nombre_ia)
        except (EOFError, KeyboardInterrupt):
            break

        if not user:
            continue

        comando = user.lower()
        es_cmd, memoria, msg = _manejar_comando_especial(comando, memoria)

        if es_cmd:
            if msg is None:
                break
            if msg == "__reiniciar_perfil__":
                nombre_usuario, _ = actualizar_perfil_usuario(memoria)
                mostrar_sistema(f"Perfil reiniciado. Nombre: {nombre_usuario}.")
            elif msg == _AYUDA_TEXTO or comando == "/ayuda":
                mostrar_ayuda()
            else:
                mostrar_sistema(msg)
            continue

        mostrar_mensaje_usuario(memoria.get("perfil", {}).get("nombre", "Tú"), user)
        mostrar_pensando(nombre_ia)

        try:
            identidad, memoria, respuesta = procesar_turno(user, identidad, memoria, emo)
            estado_emo = emo.obtener_estado_actual().get("estado", "neutral")
            mostrar_mensaje_ia(nombre_ia, respuesta, estado_emo)
        except Exception as e:
            mostrar_error(f"Ups, algo salió mal: {e}")
            log_event(f"Error: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mantenimiento_sistema()
    identidad, memoria, emo = inicializar_asistente()

    nombre_usuario, estado_usuario = actualizar_perfil_usuario(memoria)
    nombre_ia = identidad.get("nombre", "IA")

    mostrar_bienvenida(nombre_ia, nombre_usuario)

    usar_gui = input("¿Usar interfaz? [w=web, g=GUI, v=live2d en pantalla, c=cuna virtual, Enter=terminal]: ").strip().lower()

    # Lanzar modelo Live2D según la opción elegida
    if usar_gui == "v":
        import subprocess as _sp
        _python = sys.executable
        proc = None
        try:
            proc = _sp.Popen([_python, "live2d_window.py"])
        except Exception as e:
            print(f"No se pudo lanzar el modelo Live2D: {e}")
        print("Modelo Live2D activo en el escritorio")
        _loop_terminal(identidad, memoria, emo)
        if proc:
            proc.terminate()
        return
    elif usar_gui == "c":
        # Abrir visualizador de la Cuna Virtual
        try:
            from cradle_viewer import abrir_viewer
            abrir_viewer()
            print("✦ Cuna Virtual abierta — podés seguir chateando acá")
        except Exception as e:
            print(f"No se pudo abrir la Cuna Virtual: {e}")
        _loop_terminal(identidad, memoria, emo)
        return
    elif usar_gui != "w" and usar_gui != "g":
        lanzar_live2d = input("¿Lanzar Live2D en pantalla? [y/N]: ").strip().lower()
        if lanzar_live2d == "y":
            try:
                import subprocess as _sp
                _python = sys.executable
                proc = _sp.Popen([_python, "live2d_window.py"])
                print("✦ Live2D activo")
            except Exception as e:
                print(f"No se pudo lanzar el modelo Live2D: {e}")

    if usar_gui == "w":
        import subprocess as _sp2
        import webbrowser
        print("Iniciando interfaz web en http://localhost:5000 ...")
        if puerto_esta_en_uso(5000):
            print("El puerto 5000 ya está en uso. No lanzo el servidor web para evitar conflicto.")
        else:
            creationflags = 0
            if os.name == "nt":
                creationflags = _sp2.CREATE_NEW_PROCESS_GROUP | _sp2.DETACHED_PROCESS
            try:
                _sp2.Popen([sys.executable, "web_app.py"], creationflags=creationflags) if creationflags else _sp2.Popen([sys.executable, "web_app.py"])
                print("Servidor web lanzado en segundo plano.")
            except Exception as e:
                print(f"No pude iniciar la web: {e}")
        time.sleep(2)
        webbrowser.open("http://localhost:5000")
        return
    elif usar_gui == "g":
        try:
            _iniciar_gui(identidad, memoria, emo)
            return
        except Exception as e:
            print(f"No se pudo iniciar la GUI: {e}. Usando modo terminal.")

    _loop_terminal(identidad, memoria, emo)


if __name__ == "__main__":
    main()
