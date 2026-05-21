"""
time_awareness.py — Conciencia temporal de Alisha.

Alisha sabe:
- Qué hora es y cómo afecta su energía/tono
- Qué día de la semana es
- Si es mañana, tarde, noche o madrugada
- Cuánto tiempo lleva activa en la sesión
- Fechas especiales (cumpleaños, feriados)
- Cuándo recordarte de tomar agua, descansar, etc.
"""
import random
import time
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Contexto temporal
# ---------------------------------------------------------------------------

def get_momento_dia() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "mañana"
    elif 12 <= hora < 18:
        return "tarde"
    elif 18 <= hora < 22:
        return "noche"
    else:
        return "madrugada"


def get_saludo_temporal() -> str:
    momento = get_momento_dia()
    return {
        "mañana":    "Buenos días",
        "tarde":     "Buenas tardes",
        "noche":     "Buenas noches",
        "madrugada": "Hola... es muy tarde",
    }[momento]


def get_contexto_temporal() -> dict:
    """Retorna un dict completo con el contexto temporal actual."""
    ahora = datetime.now()
    momento = get_momento_dia()
    dia_semana = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"][ahora.weekday()]
    es_finde = ahora.weekday() >= 5

    return {
        "hora":        ahora.strftime("%H:%M"),
        "fecha":       ahora.strftime("%d/%m/%Y"),
        "dia_semana":  dia_semana,
        "momento_dia": momento,
        "es_finde":    es_finde,
        "es_tarde_noche": momento in ("noche", "madrugada"),
        "saludo":      get_saludo_temporal(),
    }


def descripcion_para_prompt() -> str:
    """Genera texto para incluir en el prompt del sistema."""
    ctx = get_contexto_temporal()
    ahora = datetime.now()

    lineas = [f"Son las {ctx['hora']} del {ctx['dia_semana']} {ctx['fecha']}."]

    if ctx["momento_dia"] == "madrugada":
        lineas.append("Es muy tarde — podés mencionar que deberías descansar.")
    elif ctx["momento_dia"] == "noche":
        lineas.append("Es de noche — tono más tranquilo y relajado.")
    elif ctx["momento_dia"] == "mañana":
        lineas.append("Es de mañana — energía fresca para empezar el día.")

    if ctx["es_finde"]:
        lineas.append("Es fin de semana — podés ser más relajada y casual.")

    return " ".join(lineas)


# ---------------------------------------------------------------------------
# Recordatorios de bienestar
# ---------------------------------------------------------------------------

class WellnessReminder:
    """Gestiona recordatorios de bienestar: agua, descanso, postura."""

    def __init__(self):
        self._ultimo_agua     = time.time()
        self._ultimo_descanso = time.time()
        self._ultimo_postura  = time.time()
        self._ultimo_recordatorio = 0.0
        self._ultimo_interaccion = time.time()
        self._inicio_sesion   = time.time()
        self._frases_recientes: list[str] = []

        self._frases = {
            "agua": [
                "Oye, ¿tomaste agua últimamente? Llevas un rato trabajando. 💧",
                "Un vaso de agua te puede venir muy bien ahora mismo.",
                "Hidratate un poco, que tu cerebro también lo necesita.",
                "No olvides beber agua, llevas mucho tiempo concentrada.",
            ],
            "descanso": [
                "Llevás más de 90 minutos seguidos. ¿Qué tal si te estirás un momento? 🧘",
                "A veces un descanso corto hace que vuelvas con más energía.",
                "Tus ojos agradecerán que mires a lo lejos por un minuto.",
                "Una pausa breve puede ayudarte a trabajar mejor después.",
            ],
            "postura": [
                "Recordatorio: revisá tu postura. Espalda recta, pantalla a la altura de los ojos. 🪑",
                "Ajustá tu postura para evitar dolor de espalda más tarde.",
                "Un buen apoyo lumbar y estirar los hombros ayuda mucho.",
                "Ocupate de la postura: es la mejor forma de seguir productiva sin molestias.",
            ],
        }

        # Intervalos en segundos
        self.INTERVALO_AGUA     = 45 * 60   # 45 minutos
        self.INTERVALO_DESCANSO = 90 * 60   # 90 minutos
        self.INTERVALO_POSTURA  = 30 * 60   # 30 minutos
        self.INTERVALO_COOLDOWN = 40 * 60   # 40 minutos mínimo entre recordatorios sin interacción

    def _seleccionar_frase(self, opciones: list[str]) -> str:
        disponibles = [f for f in opciones if f not in self._frases_recientes]
        if not disponibles:
            disponibles = opciones[:]
        frase = random.choice(disponibles)
        self._frases_recientes.append(frase)
        if len(self._frases_recientes) > 10:
            self._frases_recientes.pop(0)
        return frase

    def registrar_interaccion(self) -> None:
        """Llamar cuando el usuario escribe o interactúa para resetear cooldown de recordatorios."""
        self._ultimo_interaccion = time.time()
        self._ultimo_recordatorio = 0.0

    def check(self) -> Optional[str]:
        """Retorna un recordatorio si corresponde, o None."""
        ahora = time.time()

        if self._ultimo_recordatorio and ahora - self._ultimo_recordatorio < self.INTERVALO_COOLDOWN:
            return None

        if ahora - self._ultimo_agua > self.INTERVALO_AGUA:
            self._ultimo_agua = ahora
            self._ultimo_recordatorio = ahora
            return self._seleccionar_frase(self._frases["agua"])

        if ahora - self._ultimo_descanso > self.INTERVALO_DESCANSO:
            self._ultimo_descanso = ahora
            self._ultimo_recordatorio = ahora
            return self._seleccionar_frase(self._frases["descanso"])

        if ahora - self._ultimo_postura > self.INTERVALO_POSTURA:
            self._ultimo_postura = ahora
            self._ultimo_recordatorio = ahora
            return self._seleccionar_frase(self._frases["postura"])

        return None

    def registrar_descanso(self) -> None:
        """Llamar cuando el usuario toma un descanso."""
        self._ultimo_descanso = time.time()
        self._ultimo_agua     = time.time()
        self._ultimo_recordatorio = 0.0

    def tiempo_sesion_str(self) -> str:
        minutos = int((time.time() - self._inicio_sesion) / 60)
        if minutos < 60:
            return f"{minutos} minutos"
        horas = minutos // 60
        mins  = minutos % 60
        return f"{horas}h {mins}min"


# ---------------------------------------------------------------------------
# Modo estudio
# ---------------------------------------------------------------------------

class StudyMode:
    """Alisha hace preguntas sobre lo que el usuario está leyendo/estudiando."""

    def __init__(self):
        self._activo = False
        self._tema   = ""
        self._preguntas_hechas: list[str] = []

    def activar(self, tema: str) -> str:
        self._activo = True
        self._tema   = tema
        self._preguntas_hechas = []
        return (
            f"Modo estudio activado sobre '{tema}'. "
            "Leé lo que necesitás y cuando quieras te hago preguntas para que practiques. "
            "Decime 'preguntame' cuando estés lista."
        )

    def desactivar(self) -> str:
        self._activo = False
        self._tema   = ""
        return "Modo estudio desactivado. ¡Buen trabajo!"

    def esta_activo(self) -> bool:
        return self._activo

    def get_tema(self) -> str:
        return self._tema

    def generar_prompt_pregunta(self) -> str:
        """Genera el prompt para que Alisha haga una pregunta de estudio."""
        return (
            f"El usuario está estudiando '{self._tema}'. "
            "Hacé UNA pregunta de comprensión o aplicación sobre ese tema. "
            "La pregunta debe ser concreta y útil para memorizar. "
            "No des la respuesta todavía."
        )


# ---------------------------------------------------------------------------
# Integración con calendario (Google Calendar / .ics)
# ---------------------------------------------------------------------------

def leer_eventos_hoy(ruta_ics: Optional[str] = None) -> list[dict]:
    """
    Lee eventos del día desde un archivo .ics (exportado de Google Calendar).
    Retorna lista de {titulo, hora, descripcion}.
    """
    if not ruta_ics:
        return []
    try:
        from pathlib import Path
        contenido = Path(ruta_ics).read_text(encoding="utf-8", errors="ignore")
        eventos = []
        hoy = datetime.now().date()

        # Parser básico de .ics
        evento_actual = {}
        for linea in contenido.split("\n"):
            linea = linea.strip()
            if linea == "BEGIN:VEVENT":
                evento_actual = {}
            elif linea == "END:VEVENT":
                if evento_actual.get("fecha") == hoy:
                    eventos.append(evento_actual)
                evento_actual = {}
            elif linea.startswith("SUMMARY:"):
                evento_actual["titulo"] = linea[8:]
            elif linea.startswith("DTSTART"):
                try:
                    fecha_str = linea.split(":")[-1][:8]
                    evento_actual["fecha"] = datetime.strptime(fecha_str, "%Y%m%d").date()
                    if len(linea.split(":")[-1]) > 8:
                        hora_str = linea.split(":")[-1][9:13]
                        evento_actual["hora"] = f"{hora_str[:2]}:{hora_str[2:]}"
                except Exception:
                    pass
            elif linea.startswith("DESCRIPTION:"):
                evento_actual["descripcion"] = linea[12:][:100]

        return eventos
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_wellness = WellnessReminder()
_study    = StudyMode()


def get_wellness() -> WellnessReminder:
    return _wellness


def get_study_mode() -> StudyMode:
    return _study
