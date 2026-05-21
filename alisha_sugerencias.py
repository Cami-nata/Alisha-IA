"""
alisha_sugerencias.py — Sistema de Sugerencias Inteligentes Proactivas.

Alisha observa la pantalla y sugiere ayuda específica según la actividad.
NUNCA ejecuta nada sola — siempre espera confirmación.

Aprendizaje de rechazos: si Cami dice "No" muchas veces a un tipo de
sugerencia, Alisha deja de sugerirla por un tiempo.

Flujo:
  1. VisionEngine detecta actividad (Canva, Word, YouTube, etc.)
  2. SuggestionEngine genera sugerencia contextual
  3. Se emite al chat con botones Aceptar/Rechazar
  4. Si acepta → ejecuta con natural_mouse.py + confirmación
  5. Si rechaza → registra rechazo, reduce frecuencia de ese tipo
"""
from __future__ import annotations

import json
import random
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import DATA_DIR
STATE_FILE      = DATA_DIR / "chibi_state.json"
RECHAZOS_FILE   = DATA_DIR / "alisha_rechazos.json"

# ── Configuración ──────────────────────────────────────────────────────────────
MIN_INTERVALO_SUGERENCIA = 5 * 60   # mínimo 5 min entre sugerencias
MAX_RECHAZOS_ANTES_PAUSA = 3        # tras 3 rechazos del mismo tipo → pausa
PAUSA_TRAS_RECHAZOS      = 30 * 60  # 30 min de pausa tras muchos rechazos


# ══════════════════════════════════════════════════════════════════════════════
# MAPA DE ACTIVIDADES → SUGERENCIAS
# ══════════════════════════════════════════════════════════════════════════════

# Cada entrada: (palabras_clave_en_titulo, tipo_sugerencia, acciones_posibles)
_ACTIVIDAD_SUGERENCIAS = [
    # Diseño
    {
        "keywords": ["canva", "figma", "photoshop", "illustrator", "design"],
        "tipo": "diseño",
        "sugerencias": [
            ("buscar_inspiracion", "Vi que estás diseñando. ¿Querés que busque referencias o paletas de colores para lo que estás haciendo?"),
            ("guardar_exportar",   "¿Querés que te recuerde exportar el archivo cuando termines?"),
        ],
        "accion_facil": True,
    },
    # Código
    {
        "keywords": ["vscode", "code", "pycharm", "github", "terminal", "powershell", "kiro"],
        "tipo": "codigo",
        "sugerencias": [
            ("buscar_error",    "Vi que estás programando. Si te trabaste con algo, puedo buscar la solución."),
            ("documentar",      "¿Querés que te ayude a documentar lo que estás escribiendo?"),
        ],
        "accion_facil": True,
    },
    # Documentos / tareas escolares
    {
        "keywords": ["word", "docs", "libreoffice", "writer", "documento", "sesion", "tarea", "informe"],
        "tipo": "documento",
        "sugerencias": [
            ("mejorar_texto",   "Estás escribiendo un documento. ¿Querés que revise la redacción o te sugiera mejoras?"),
            ("buscar_info",     "¿Necesitás información extra para completar lo que estás escribiendo?"),
            ("guardar_recordar","¿Querés que te recuerde guardar el archivo cada 10 minutos?"),
        ],
        "accion_facil": True,
    },
    # YouTube / videos educativos
    {
        "keywords": ["youtube", "emprendimiento", "tutorial", "curso", "aprender", "clase"],
        "tipo": "aprendizaje",
        "sugerencias": [
            ("tomar_notas",     "Estás viendo algo interesante. ¿Querés que abra el Bloc de Notas para que anotes los puntos clave?"),
            ("buscar_mas",      "¿Querés que busque más recursos sobre este tema?"),
        ],
        "accion_facil": True,
    },
    # WhatsApp / mensajes
    {
        "keywords": ["whatsapp", "telegram", "discord", "mensaje"],
        "tipo": "comunicacion",
        "sugerencias": [
            ("descargar_archivo", "Vi que hay archivos en los mensajes. ¿Querés que los busque en Descargas?"),
        ],
        "accion_facil": False,  # requiere más cuidado
    },
    # Excel / planillas
    {
        "keywords": ["excel", "sheets", "planilla", "tabla", "datos"],
        "tipo": "datos",
        "sugerencias": [
            ("analizar_datos",  "Estás trabajando con datos. ¿Querés que te ayude a organizar o analizar algo?"),
            ("crear_grafico",   "¿Necesitás crear un gráfico o resumen de los datos?"),
        ],
        "accion_facil": True,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO DE RECHAZOS (persistente)
# ══════════════════════════════════════════════════════════════════════════════

class RechazosManager:
    """Registra y aprende de los rechazos de Cami."""

    def __init__(self):
        self._data: dict = self._cargar()
        self._lock = threading.Lock()

    def _cargar(self) -> dict:
        try:
            if RECHAZOS_FILE.exists():
                return json.loads(RECHAZOS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _guardar(self) -> None:
        try:
            RECHAZOS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def registrar_rechazo(self, tipo: str, accion_id: str) -> None:
        key = f"{tipo}:{accion_id}"
        with self._lock:
            entry = self._data.get(key, {"count": 0, "ultima": None, "pausado_hasta": None})
            entry["count"] += 1
            entry["ultima"] = datetime.now().isoformat()
            if entry["count"] >= MAX_RECHAZOS_ANTES_PAUSA:
                pausa_hasta = datetime.now() + timedelta(seconds=PAUSA_TRAS_RECHAZOS)
                entry["pausado_hasta"] = pausa_hasta.isoformat()
                print(f"[Sugerencias] Pausando '{key}' por {PAUSA_TRAS_RECHAZOS//60} min (muchos rechazos)")
            self._data[key] = entry
            self._guardar()

    def registrar_aceptacion(self, tipo: str, accion_id: str) -> None:
        """Si acepta, resetear el contador de rechazos."""
        key = f"{tipo}:{accion_id}"
        with self._lock:
            if key in self._data:
                self._data[key]["count"] = max(0, self._data[key]["count"] - 1)
                self._data[key]["pausado_hasta"] = None
                self._guardar()

    def puede_sugerir(self, tipo: str, accion_id: str) -> bool:
        key = f"{tipo}:{accion_id}"
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return True
            pausado_hasta = entry.get("pausado_hasta")
            if pausado_hasta:
                try:
                    if datetime.now() < datetime.fromisoformat(pausado_hasta):
                        return False
                    else:
                        # Pausa expiró — resetear
                        entry["pausado_hasta"] = None
                        entry["count"] = 0
                        self._data[key] = entry
                        self._guardar()
                except Exception:
                    pass
            return True


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR DE SUGERENCIAS
# ══════════════════════════════════════════════════════════════════════════════

class SuggestionEngine:
    """
    Analiza la actividad actual y genera sugerencias contextuales.
    Se conecta al VisionEngine existente sin modificarlo.
    """

    def __init__(self):
        self._rechazos    = RechazosManager()
        self._ultima_sug  = 0.0
        self._ultima_app  = ""
        self._lock        = threading.Lock()
        self._running     = False

    def start(self) -> None:
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="SuggestionEngine")
        t.start()
        print("[Sugerencias] ✓ Motor de sugerencias iniciado")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        time.sleep(90)  # esperar 90s al arranque
        while self._running:
            try:
                self._evaluar_y_sugerir()
            except Exception as e:
                print(f"[Sugerencias] Error: {e}")
            time.sleep(60)  # evaluar cada 60 segundos

    def _evaluar_y_sugerir(self) -> None:
        # Throttle: no sugerir si ya lo hizo hace menos de MIN_INTERVALO
        if time.time() - self._ultima_sug < MIN_INTERVALO_SUGERENCIA:
            return

        # Verificar semáforo global
        try:
            from alisha_silencio import puede_hablar_proactivo
            if not puede_hablar_proactivo("sugerencias"):
                return
        except Exception:
            pass

        # No sugerir si Alisha está hablando
        try:
            if STATE_FILE.exists():
                estado = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                if estado.get("hablando") or estado.get("modo") == "THINKING":
                    return
        except Exception:
            pass

        # Obtener ventana activa
        titulo = self._get_titulo_ventana()
        if not titulo or titulo == self._ultima_app:
            return  # misma app, no repetir

        # Buscar actividad que coincida
        actividad = self._detectar_actividad(titulo)
        if not actividad:
            return

        # Elegir sugerencia disponible (no rechazada)
        sugerencia = self._elegir_sugerencia(actividad)
        if not sugerencia:
            return

        accion_id, mensaje = sugerencia
        self._ultima_sug = time.time()
        self._ultima_app = titulo

        print(f"[Sugerencias] 💡 {actividad['tipo']}: {mensaje[:60]}...")
        # Registrar en semáforo global
        try:
            from alisha_silencio import registrar_habla_proactivo
            registrar_habla_proactivo("sugerencias")
        except Exception:
            pass
        self._emitir_sugerencia(actividad, accion_id, mensaje)

    def _get_titulo_ventana(self) -> str:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            buf  = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            return buf.value.strip()
        except Exception:
            return ""

    def _detectar_actividad(self, titulo: str) -> Optional[dict]:
        t = titulo.lower()
        for act in _ACTIVIDAD_SUGERENCIAS:
            if any(kw in t for kw in act["keywords"]):
                return act
        return None

    def _elegir_sugerencia(self, actividad: dict) -> Optional[tuple]:
        """Elige una sugerencia disponible (no pausada por rechazos)."""
        disponibles = [
            s for s in actividad["sugerencias"]
            if self._rechazos.puede_sugerir(actividad["tipo"], s[0])
        ]
        if not disponibles:
            return None
        return random.choice(disponibles)

    def _emitir_sugerencia(self, actividad: dict, accion_id: str, mensaje: str) -> None:
        """Emite la sugerencia al chat con botones de confirmación."""
        try:
            from web_app import socketio, _memory_db, _session_id, _MEMORY_DB_OK

            # Emitir como propuesta con botones
            socketio.emit("propuesta_accion", {
                "mensaje":   mensaje,
                "accion_id": f"sugerencia_{accion_id}",
                "contexto": {
                    "tipo":      actividad["tipo"],
                    "accion_id": accion_id,
                    "mensaje":   mensaje,
                    "accion_facil": actividad.get("accion_facil", True),
                },
                "botones": ["Dale, ayudame", "No gracias"],
                "fuente": "sugerencia_proactiva",
            })

            # También hablar por voz (versión corta)
            try:
                from audio_visual_sync import get_audio_visual_sync
                avs = get_audio_visual_sync()
                avs.speak(mensaje, sarcasm_score=0.0,
                          emotional_state="curiosidad", async_mode=True)
            except Exception:
                pass

            # Guardar en el hilo activo
            if _MEMORY_DB_OK and _memory_db and _session_id > 0:
                _memory_db.save_conversation(
                    entrada="[Alisha sugiere]",
                    respuesta=mensaje,
                    estado_emocional="curiosidad",
                    session_id=_session_id,
                )
        except Exception as e:
            print(f"[Sugerencias] Error emitiendo: {e}")

    def registrar_respuesta(self, accion_id: str, tipo: str, acepto: bool) -> None:
        """Registra si Cami aceptó o rechazó la sugerencia."""
        if acepto:
            self._rechazos.registrar_aceptacion(tipo, accion_id)
        else:
            self._rechazos.registrar_rechazo(tipo, accion_id)
            print(f"[Sugerencias] Rechazo registrado: {tipo}:{accion_id}")


# ══════════════════════════════════════════════════════════════════════════════
# EJECUTOR DE SUGERENCIAS ACEPTADAS
# ══════════════════════════════════════════════════════════════════════════════

def ejecutar_sugerencia(accion_id: str, contexto: dict) -> dict:
    """
    Ejecuta la acción sugerida tras confirmación de Cami.
    Usa natural_mouse.py para acciones que requieren control del PC.
    Siempre retorna un mensaje de resultado.
    """
    tipo = contexto.get("tipo", "")

    acciones = {
        "buscar_inspiracion": _buscar_inspiracion,
        "buscar_error":       _buscar_error,
        "buscar_info":        _buscar_info,
        "buscar_mas":         _buscar_mas,
        "tomar_notas":        _abrir_bloc_notas,
        "mejorar_texto":      _mejorar_texto,
        "analizar_datos":     _analizar_datos,
        "guardar_recordar":   _recordatorio_guardado,
        "descargar_archivo":  _abrir_descargas,
        "documentar":         _documentar_codigo,
        "crear_grafico":      _buscar_info_grafico,
    }

    fn = acciones.get(accion_id)
    if not fn:
        return {"ok": False, "mensaje": f"No sé cómo hacer '{accion_id}' todavía."}

    try:
        return fn(contexto)
    except Exception as e:
        return {"ok": False, "mensaje": f"Ups, algo falló: {e}"}


# ── Implementaciones de acciones ──────────────────────────────────────────────

def _buscar_inspiracion(ctx: dict) -> dict:
    import webbrowser
    titulo = ctx.get("titulo_ventana", "diseño")
    webbrowser.open(f"https://www.pinterest.com/search/pins/?q={titulo.replace(' ', '+')}")
    return {"ok": True, "mensaje": "Abrí Pinterest con búsqueda de inspiración. ¡A ver qué encontramos!"}

def _buscar_error(ctx: dict) -> dict:
    titulo = ctx.get("titulo_ventana", "")
    import webbrowser
    webbrowser.open(f"https://stackoverflow.com/search?q={titulo.replace(' ', '+')}")
    return {"ok": True, "mensaje": "Abrí Stack Overflow. Si me contás el error específico, te busco la solución exacta."}

def _buscar_info(ctx: dict) -> dict:
    titulo = ctx.get("titulo_ventana", "")
    import webbrowser
    webbrowser.open(f"https://www.google.com/search?q={titulo.replace(' ', '+')}")
    return {"ok": True, "mensaje": "Abrí Google con el tema. ¿Querés que te resuma lo que encuentre?"}

def _buscar_mas(ctx: dict) -> dict:
    return _buscar_info(ctx)

def _abrir_bloc_notas(ctx: dict) -> dict:
    try:
        import subprocess
        subprocess.Popen(["notepad.exe"],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return {"ok": True, "mensaje": "Abrí el Bloc de Notas. Anotá lo que necesites, yo te ayudo a organizar después."}
    except Exception as e:
        return {"ok": False, "mensaje": f"No pude abrir el Bloc de Notas: {e}"}

def _mejorar_texto(ctx: dict) -> dict:
    try:
        from brain import get_brain
        brain = get_brain()
        resp = brain.process(
            "Cami está escribiendo un documento. Dále 3 consejos cortos de redacción "
            "en voseo rioplatense, máximo 2 oraciones cada uno."
        )
        return {"ok": True, "mensaje": resp.content}
    except Exception:
        return {"ok": True, "mensaje": "Acordate de usar párrafos cortos, conectores claros y revisar la ortografía al final."}

def _analizar_datos(ctx: dict) -> dict:
    return {"ok": True, "mensaje": "Contame qué datos tenés y qué necesitás analizar. Te ayudo a pensar la estructura."}

def _recordatorio_guardado(ctx: dict) -> dict:
    # Programar recordatorio cada 10 minutos
    def _recordar():
        time.sleep(600)
        try:
            from web_app import socketio
            socketio.emit("respuesta", {
                "texto": "Che, ¿ya guardaste el documento? No sea que se pierda algo.",
                "estado_emocional": "curiosidad",
            })
        except Exception:
            pass
    threading.Thread(target=_recordar, daemon=True).start()
    return {"ok": True, "mensaje": "Dale, te aviso en 10 minutos para que guardes. ¡A seguir!"}

def _abrir_descargas(ctx: dict) -> dict:
    try:
        import subprocess
        downloads = Path.home() / "Downloads"
        subprocess.Popen(["explorer", str(downloads)],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return {"ok": True, "mensaje": "Abrí la carpeta de Descargas. Los archivos de WhatsApp deberían estar ahí."}
    except Exception as e:
        return {"ok": False, "mensaje": f"No pude abrir Descargas: {e}"}

def _documentar_codigo(ctx: dict) -> dict:
    return {"ok": True, "mensaje": "Pegame el código que querés documentar en el chat y te genero los comentarios."}

def _buscar_info_grafico(ctx: dict) -> dict:
    return {"ok": True, "mensaje": "Contame qué datos querés graficar y te explico cómo hacerlo en Excel o te genero el código."}


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine: Optional[SuggestionEngine] = None

def get_suggestion_engine() -> SuggestionEngine:
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine

def iniciar_sugerencias() -> None:
    get_suggestion_engine().start()
