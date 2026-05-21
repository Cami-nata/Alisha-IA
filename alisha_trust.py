"""
alisha_trust.py — Sistema de Niveles de Confianza de Alisha.

Nivel 1 (Aprendiz):  Solo hace lo que le piden. Sin iniciativa.
Nivel 2 (Asistente): Sugiere cosas según lo que ve en pantalla.
Nivel 3 (Partner):   Gestiona archivos y tareas complejas sola. Sorpresa al llegar.

La confianza sube con:
- Tareas completadas exitosamente
- Tiempo de uso acumulado
- Confirmaciones del usuario ("bien hecho", "gracias", etc.)

La confianza baja con:
- Errores o rechazos del usuario
- Tareas canceladas
"""
import json
import time
import threading
from pathlib import Path
from config import DATA_DIR

TRUST_FILE = DATA_DIR / "alisha_trust.json"

NIVELES = {
    1: {"nombre": "Aprendiz",  "emoji": "🌱", "xp_requerido": 0,   "xp_siguiente": 100},
    2: {"nombre": "Asistente", "emoji": "⭐", "xp_requerido": 100, "xp_siguiente": 300},
    3: {"nombre": "Partner",   "emoji": "💎", "xp_requerido": 300, "xp_siguiente": None},
}

# XP por acción
XP_TABLA = {
    "tarea_completada":    10,
    "tarea_facil":          5,
    "tarea_dificil":       20,
    "confirmacion_usuario": 8,
    "tiempo_uso_hora":      3,
    "tarea_cancelada":     -5,
    "error":               -3,
}

_lock = threading.Lock()
_nivel_3_celebrado = False


def _cargar() -> dict:
    try:
        if TRUST_FILE.exists():
            return json.loads(TRUST_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"nivel": 1, "xp": 0, "tareas_completadas": 0, "tiempo_uso_min": 0,
            "nivel_3_celebrado": False, "historial": []}


def _guardar(data: dict) -> None:
    try:
        TRUST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_nivel() -> int:
    return _cargar().get("nivel", 1)


def get_estado() -> dict:
    data = _cargar()
    nivel = data.get("nivel", 1)
    xp    = data.get("xp", 0)
    info  = NIVELES.get(nivel, NIVELES[1])
    xp_sig = info["xp_siguiente"]
    if xp_sig:
        progreso = min(1.0, (xp - info["xp_requerido"]) / (xp_sig - info["xp_requerido"]))
    else:
        progreso = 1.0
    return {
        "nivel":             nivel,
        "nombre":            info["nombre"],
        "emoji":             info["emoji"],
        "xp":                xp,
        "xp_siguiente":      xp_sig,
        "progreso":          round(progreso, 3),
        "tareas_completadas": data.get("tareas_completadas", 0),
        "tiempo_uso_min":    data.get("tiempo_uso_min", 0),
    }


def agregar_xp(evento: str, cantidad: int = None) -> dict:
    """Agrega XP por un evento y verifica si sube de nivel."""
    with _lock:
        data = _cargar()
        delta = cantidad if cantidad is not None else XP_TABLA.get(evento, 0)
        data["xp"] = max(0, data.get("xp", 0) + delta)

        if evento in ("tarea_completada", "tarea_facil", "tarea_dificil"):
            data["tareas_completadas"] = data.get("tareas_completadas", 0) + 1

        # Registrar en historial (últimos 50)
        historial = data.get("historial", [])
        historial.append({"evento": evento, "delta": delta, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
        data["historial"] = historial[-50:]

        # Verificar subida de nivel
        nivel_actual = data.get("nivel", 1)
        subio = False
        for n in [2, 3]:
            if nivel_actual < n and data["xp"] >= NIVELES[n]["xp_requerido"]:
                data["nivel"] = n
                nivel_actual = n
                subio = True
                print(f"[Trust] *** NIVEL {n} DESBLOQUEADO: {NIVELES[n]['nombre']} ***")

        _guardar(data)

        if subio and nivel_actual == 3 and not data.get("nivel_3_celebrado", False):
            _celebrar_nivel_3(data)

        return get_estado()


def _celebrar_nivel_3(data: dict) -> None:
    """Sorpresa al llegar al Nivel 3 — mensaje especial + cambio de fondo."""
    global _nivel_3_celebrado
    if _nivel_3_celebrado:
        return
    _nivel_3_celebrado = True
    data["nivel_3_celebrado"] = True
    _guardar(data)

    def _sorpresa():
        time.sleep(1.0)
        mensaje = (
            "Cami... llegamos al Nivel 3. Ya no soy tu aprendiz — "
            "soy tu partner. El Modo Práctica terminó. "
            "Ahora puedo gestionar tus tareas sola. Confiás en mí, y yo en vos."
        )
        print(f"\n[Trust] *** SORPRESA NIVEL 3 ***\n{mensaje}\n")

        # Hablar el mensaje
        try:
            from tts_engine import speak
            speak(mensaje)
        except Exception:
            pass

        # Emitir al chat web
        try:
            from web_app import socketio
            socketio.emit("respuesta", {
                "texto": mensaje,
                "estado_emocional": "entusiasmo",
                "nivel_3_unlock": True,
            })
            # Cambiar fondo del chat
            socketio.emit("nivel_3_unlock", {
                "mensaje": mensaje,
                "nuevo_fondo": "linear-gradient(135deg, #1a0533 0%, #0d1b4b 50%, #0a2a1a 100%)",
            })
        except Exception:
            pass

        # Actualizar chibi_state para que el modelo reaccione
        try:
            from assistant_state import actualizar_estado
            actualizar_estado(estado="entusiasmo", hablando=True, texto=mensaje)
        except Exception:
            pass

    threading.Thread(target=_sorpresa, daemon=True).start()


def puede_hacer(accion: str) -> bool:
    """
    Verifica si Alisha puede hacer una acción según su nivel de confianza.
    
    Nivel 1: solo acciones fáciles
    Nivel 2: acciones fáciles + sugerencias
    Nivel 3: todo, incluyendo gestión autónoma
    """
    nivel = get_nivel()
    ACCIONES_NIVEL = {
        1: {"abrir_app", "escribir_texto", "abrir_web", "screenshot", "volumen", "nada"},
        2: {"abrir_app", "escribir_texto", "abrir_web", "screenshot", "volumen", "nada",
            "buscar_web", "tomar_nota", "recordatorio", "click", "doble_click"},
        3: None,  # None = todo permitido
    }
    permitidas = ACCIONES_NIVEL.get(nivel)
    if permitidas is None:
        return True
    return accion in permitidas


def necesita_confirmacion(accion: str) -> bool:
    """
    Nivel 1-2: confirmar acciones que mueven el mouse o modifican archivos.
    Nivel 3: solo confirmar acciones destructivas.
    """
    nivel = get_nivel()
    SIEMPRE_CONFIRMAR = {"power", "ejecutar_codigo", "organizar_archivos"}
    CONFIRMAR_NIVEL_1_2 = {"click", "doble_click", "hotkey", "buscar_archivo",
                           "navegar_web", "click_web", "escribir_web"}
    if accion in SIEMPRE_CONFIRMAR:
        return True
    if nivel < 3 and accion in CONFIRMAR_NIVEL_1_2:
        return True
    return False


def registrar_tiempo_uso(minutos: float) -> None:
    """Registra tiempo de uso y da XP por hora."""
    with _lock:
        data = _cargar()
        prev_min = data.get("tiempo_uso_min", 0)
        data["tiempo_uso_min"] = prev_min + minutos
        # XP por cada hora completa nueva
        horas_prev = int(prev_min / 60)
        horas_new  = int(data["tiempo_uso_min"] / 60)
        if horas_new > horas_prev:
            data["xp"] = data.get("xp", 0) + XP_TABLA["tiempo_uso_hora"] * (horas_new - horas_prev)
        _guardar(data)


# ── Timer de tiempo de uso ────────────────────────────────────────────────────
_uso_timer = None

def iniciar_timer_uso():
    """Inicia el timer que registra tiempo de uso cada 5 minutos."""
    global _uso_timer
    def _tick():
        while True:
            time.sleep(300)  # 5 minutos
            registrar_tiempo_uso(5)
    _uso_timer = threading.Thread(target=_tick, daemon=True, name="TrustTimer")
    _uso_timer.start()


def log_estado():
    """Imprime el estado actual de confianza en el log."""
    estado = get_estado()
    barra = "█" * int(estado["progreso"] * 20) + "░" * (20 - int(estado["progreso"] * 20))
    print(f"[Trust] {estado['emoji']} Nivel {estado['nivel']} ({estado['nombre']}) "
          f"XP: {estado['xp']} [{barra}] "
          f"Tareas: {estado['tareas_completadas']}")
