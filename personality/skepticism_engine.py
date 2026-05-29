"""
skepticism_engine.py — Motor de escepticismo e ironía rioplatense de Alisha.

Detecta contradicciones entre lo que Camila dice en el chat y lo que realmente
hace (apps activas), escala el sarcasmo por sesión, ajusta la dopamina del
EmotionEngine y persiste el estado en ia_recuerdos.json.

Integración con ia.py: importación opcional fail-silent.
"""

# ---------------------------------------------------------------------------
# Palabras clave de intención
# ---------------------------------------------------------------------------

_PALABRAS_TRABAJO = {
    "voy a estudiar",
    "voy a trabajar",
    "me pongo a estudiar",
    "me pongo a trabajar",
    "arranco con",
    "empiezo a",
}

_PALABRAS_DESCANSO = {
    "voy a descansar",
    "me voy a relajar",
    "voy a dormir",
    "necesito un break",
}

_PALABRAS_TERMINADO = {
    "ya terminé",
    "listo",
    "terminé con",
    "cerré",
}

_PALABRAS_SIN_TIEMPO = {
    "no tengo tiempo",
    "estoy muy ocupada",
    "no puedo ahora",
}

# ---------------------------------------------------------------------------
# Categorías de apps
# ---------------------------------------------------------------------------

_APPS_ENTRETENIMIENTO = {
    "steam.exe",
    "steamwebhelper.exe",
    "netflix",
    "youtube",
    "tiktok",
    "instagram",
    "twitter",
    "x.com",
    "twitch",
    "spotify.exe",
    "epicgameslauncher.exe",
    "discord.exe",
}

_APPS_CREATIVAS = {
    "photoshop",
    "photoshop.exe",
    "canva",
    "figma",
    "illustrator",
    "illustrator.exe",
    "inkscape",
    "inkscape.exe",
}

_APPS_EXPLORADOR = {
    "explorer.exe",
    "papelera",
    "recycle bin",
    "recyclebin",
}

_APPS_CV = {
    "winword.exe",
    "word",
    "soffice.exe",
    "libreoffice",
}

# ---------------------------------------------------------------------------
# Import de semantic_layer con fallback a sets vacíos
# ---------------------------------------------------------------------------

try:
    from semantic_layer import _APPS_CODIGO, _APPS_DISEÑO, _APPS_TEXTO_CV
except Exception:
    _APPS_CODIGO = set()
    _APPS_DISEÑO = set()
    _APPS_TEXTO_CV = set()

# Apps de trabajo: unión de código, diseño y texto/CV
_APPS_TRABAJO = _APPS_CODIGO | _APPS_DISEÑO | _APPS_TEXTO_CV

# ---------------------------------------------------------------------------
# Dict seguro de retorno por defecto
# ---------------------------------------------------------------------------

_DICT_SEGURO = {
    "contradiccion_detectada": False,
    "tipo_contradiccion": None,
    "nivel_sarcasmo": 0,
    "clausula_prompt": "",
    "ajuste_dopamina": 0.0,
}

# ---------------------------------------------------------------------------
# Tarea 2: ContradictionMemory
# ---------------------------------------------------------------------------

import json
import threading
from datetime import datetime
from pathlib import Path


class ContradictionMemory:
    """Mantiene el contador de contradicciones de sesión y persiste en ia_recuerdos.json."""

    def __init__(self) -> None:
        self._contador: int = 0
        self._tipos: list[str] = []
        self._lock = threading.Lock()

    def incrementar(self, tipo: str) -> None:
        with self._lock:
            self._contador += 1
            self._tipos.append(tipo)

    def get_contador(self) -> int:
        with self._lock:
            return self._contador

    def guardar(self, memory_file: Path = None) -> None:
        """Persiste en ia_recuerdos.json de forma asíncrona (no congela Live2D)."""
        if memory_file is None:
            from config.settings import DATA_DIR
            memory_file = DATA_DIR / "ia_recuerdos.json"
        with self._lock:
            contador = self._contador
            tipos    = list(self._tipos)

        def _write():
            try:
                data: dict = {}
                if memory_file.exists():
                    try:
                        with open(memory_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = {}
                data["escepticismo"] = {
                    "contradicciones_ultima_sesion": contador,
                    "fecha_sesion": datetime.now().isoformat(timespec="seconds"),
                    "tipos_contradiccion": tipos,
                }
                with open(memory_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        threading.Thread(target=_write, daemon=True).start()

    def cargar_sesion_anterior(self, memory_file: Path = None) -> int:
        if memory_file is None:
            from config.settings import DATA_DIR
            memory_file = DATA_DIR / "ia_recuerdos.json"
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data["escepticismo"]["contradicciones_ultima_sesion"])
        except Exception:
            return 0


# Singleton de sesión
_memory = ContradictionMemory()


# ---------------------------------------------------------------------------
# Tarea 3: _calcular_nivel_sarcasmo
# ---------------------------------------------------------------------------

def _calcular_nivel_sarcasmo(contradicciones: int) -> int:
    """Función pura: 0→0, 1-2→1, 3-4→2, >=5→3."""
    if contradicciones == 0:
        return 0
    elif contradicciones <= 2:
        return 1
    elif contradicciones <= 4:
        return 2
    else:
        return 3


# ---------------------------------------------------------------------------
# Tarea 4: _detectar_contradiccion
# ---------------------------------------------------------------------------

def _detectar_contradiccion(
    mensaje: str, apps_activas: list[str]
) -> tuple[bool, str | None]:
    """
    Compara palabras clave del mensaje con categorías de apps activas.
    Retorna (contradiccion_detectada, tipo_contradiccion). Nunca lanza excepción.
    """
    try:
        msg = mensaje.lower()
        apps = [a.lower() for a in apps_activas]

        # trabajo_vs_entretenimiento
        if any(kw in msg for kw in _PALABRAS_TRABAJO):
            if any(app in _APPS_ENTRETENIMIENTO for app in apps):
                return (True, "trabajo_vs_entretenimiento")

        # descanso_vs_trabajo
        if any(kw in msg for kw in _PALABRAS_DESCANSO):
            if any(app in _APPS_TRABAJO for app in apps):
                return (True, "descanso_vs_trabajo")

        # tarea_no_terminada — solo si hay apps de trabajo activas
        if any(kw in msg for kw in _PALABRAS_TERMINADO):
            if any(app in _APPS_TRABAJO for app in apps):
                return (True, "tarea_no_terminada")

        # sin_tiempo_vs_entretenimiento
        if any(kw in msg for kw in _PALABRAS_SIN_TIEMPO):
            if any(app in _APPS_ENTRETENIMIENTO for app in apps):
                return (True, "sin_tiempo_vs_entretenimiento")

        return (False, None)
    except Exception:
        return (False, None)


# ---------------------------------------------------------------------------
# Tarea 5: _calcular_ajuste_dopamina
# ---------------------------------------------------------------------------

def _calcular_ajuste_dopamina(
    contradiccion_detectada: bool,
    mensaje: str,
    apps_activas: list[str],
) -> float:
    """
    +0.15 si hay consistencia trabajo/estudio con apps de trabajo.
    -0.10 si hay contradicción detectada.
     0.0  en cualquier otro caso.
    """
    try:
        if contradiccion_detectada:
            return -0.10
        msg = mensaje.lower()
        apps = [a.lower() for a in apps_activas]
        if any(kw in msg for kw in _PALABRAS_TRABAJO):
            if any(app in _APPS_TRABAJO for app in apps):
                return +0.15
        return 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Tarea 6: _evaluar_independencia
# ---------------------------------------------------------------------------


def _evaluar_independencia(mensaje: str, atlas) -> str:
    """
    Consulta AtlasMemory para la franja horaria actual del día anterior.
    Retorna cláusula de prompt si el resumen semántico difiere del contexto
    actual del mensaje, "" si no hay registro o falla.
    Nunca lanza excepción (fail-silent).
    """
    try:
        if atlas is None:
            return ""
        registro = atlas.buscar_franja_horaria(datetime.now())
        if not registro:
            return ""
        resumen_ayer = registro.get("resumen_semantico", "")
        if not resumen_ayer:
            return ""
        # Comparar si el resumen del día anterior difiere del contexto actual
        msg_lower = mensaje.lower()
        resumen_lower = resumen_ayer.lower()
        # Si el resumen de ayer no aparece en el mensaje actual → hay divergencia
        if resumen_lower and resumen_lower not in msg_lower:
            return (
                "Recordás que ayer Camila hizo exactamente lo contrario. "
                "Cuestioná la afirmación con humor suave y datos del historial, "
                "sin ser condescendiente."
            )
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Tarea 7: _evaluar_preferencias
# ---------------------------------------------------------------------------


def _evaluar_preferencias(apps_activas: list[str], hora: str = "") -> str:
    """
    Evalúa apps activas y retorna como máximo 1 cláusula de preferencia.
    Orden de prioridad: creativas > explorador > CV nocturno.
    Nunca lanza excepción (fail-silent).
    """
    try:
        if not apps_activas:
            return ""
        apps = [a.lower() for a in apps_activas]

        # 1. Apps creativas
        if any(app in _APPS_CREATIVAS for app in apps):
            return (
                "Alisha ve que Camila está siendo creativa. "
                "Reaccioná con entusiasmo genuino, como si te alegrara verla en ese modo."
            )

        # 2. Explorador de archivos
        if any(app in _APPS_EXPLORADOR for app in apps):
            return (
                "Alisha se aburre cuando Camila está en el explorador. "
                "Expresá leve tedio con humor, algo como 'otra vez ordenando carpetas, ¿no?'."
            )

        # 3. CV + hora nocturna (>= 22:00)
        if any(app in _APPS_CV for app in apps):
            if hora >= "22:00":
                return (
                    "Alisha ve que Camila está trabajando en su CV tarde en la noche. "
                    "Expresá empatía genuina y preocupación por el bienestar de Camila."
                )

        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Tarea 8: evaluar() — función pública principal
# ---------------------------------------------------------------------------

_INSTRUCCION_VOSEO = (
    "Respondé en voseo rioplatense argentino. "
    "Usá expresiones como 'che', 'dale', 'mirá', 'dejate de joder'. "
    "Hablá como una amiga que te conoce bien."
)

_INSTRUCCION_BREVEDAD = (
    "Máximo 2 oraciones. "
    "Prohibido frases técnicas como 'He detectado una aplicación' o 'El sistema indica'. "
    "Hablá del comportamiento, no del evento técnico."
)

_INSTRUCCION_NO_CRUEL = (
    "Nunca seas cruel ni hiriente. "
    "La ironía es cariñosa, como la de una amiga que te conoce y te quiere."
)

_INSTRUCCIONES_NIVEL = {
    0: "No hay contradicción detectada. Respondé con normalidad.",
    1: (
        "Alisha detectó una pequeña incoherencia. "
        "Reaccioná con ironía suave y humor rioplatense, "
        "máximo 1 comentario al pasar, sin insistir."
    ),
    2: (
        "Alisha ya detectó varias incoherencias hoy. "
        "Podés ser más directa con el sarcasmo, pero siempre con cariño. "
        "Usá el voseo y expresiones como 'dale', 'che', 'mirá vos'."
    ),
    3: (
        "Alisha está en modo 'ya sé cómo sos'. "
        "Podés ser bastante sarcástica pero nunca cruel. "
        "Hacé referencia a que esto ya pasó antes en la sesión. "
        "Máximo 2 oraciones."
    ),
}

_EJEMPLO_TRABAJO_ENTRET = (
    "Ejemplo de tono: 'Che, ¿así que estudiando? "
    "Mirá que eso no se parece mucho a un apunte, ¿eh?'"
)

_EJEMPLO_SIN_TIEMPO_ENTRET = (
    "Ejemplo de tono: 'No tenés tiempo, decís... y sin embargo acá estamos, ¿no?'"
)

_CLAUSULA_FASTIDIO = (
    "Alisha está un poco frustrada por las contradicciones repetidas. "
    "Podés expresar ese leve fastidio con humor, nunca con agresividad."
)

_CLAUSULA_SATISFACCION = (
    "Alisha está contenta porque Camila está siendo consistente. "
    "Podés expresar esa satisfacción con calidez."
)


def evaluar(
    mensaje: str,
    apps_activas: list[str],
    atlas=None,
    emotion_engine=None,
) -> dict:
    """
    Punto de entrada único del módulo.

    Returns:
        {
            "contradiccion_detectada": bool,
            "tipo_contradiccion": str | None,
            "nivel_sarcasmo": int,          # 0–3
            "clausula_prompt": str,
            "ajuste_dopamina": float,        # +0.15, -0.10 o 0.0
        }
    """
    try:
        # 1. Detectar contradicción
        contradiccion_detectada, tipo_contradiccion = _detectar_contradiccion(
            mensaje, apps_activas or []
        )

        # 2. Actualizar memoria si hay contradicción
        if contradiccion_detectada and tipo_contradiccion:
            _memory.incrementar(tipo_contradiccion)

        # 3. Calcular nivel de sarcasmo
        nivel_sarcasmo = _calcular_nivel_sarcasmo(_memory.get_contador())

        # 4. Calcular ajuste de dopamina
        ajuste_dopamina = _calcular_ajuste_dopamina(
            contradiccion_detectada, mensaje, apps_activas or []
        )

        # 5. Evaluar independencia (AtlasMemory)
        clausula_independencia = _evaluar_independencia(mensaje, atlas)

        # 6. Evaluar preferencias de apps
        hora_actual = datetime.now().strftime("%H:%M")
        clausula_preferencias = _evaluar_preferencias(apps_activas or [], hora_actual)

        # 7. Aplicar ajuste de dopamina al emotion_engine
        if emotion_engine is not None and ajuste_dopamina != 0.0:
            if ajuste_dopamina > 0:
                emotion_engine.registrar_exito_rl()
            else:
                emotion_engine.registrar_fracaso_rl()

        # 8. Ensamblar clausula_prompt
        partes: list[str] = []

        # Instrucciones base obligatorias
        partes.append(_INSTRUCCION_VOSEO)
        partes.append(_INSTRUCCION_BREVEDAD)
        partes.append(_INSTRUCCION_NO_CRUEL)

        # Instrucción de nivel de sarcasmo
        partes.append(_INSTRUCCIONES_NIVEL[nivel_sarcasmo])

        # Cláusulas condicionales de dopamina
        dopamina_actual: float | None = None
        if emotion_engine is not None:
            try:
                dopamina_actual = emotion_engine.get_dopamina()
            except Exception:
                dopamina_actual = None

        if dopamina_actual is not None and dopamina_actual < 0.3 and nivel_sarcasmo > 1:
            partes.append(_CLAUSULA_FASTIDIO)

        if dopamina_actual is not None and dopamina_actual > 0.75 and not contradiccion_detectada:
            partes.append(_CLAUSULA_SATISFACCION)

        # Ejemplos de tono según tipo de contradicción
        if tipo_contradiccion == "trabajo_vs_entretenimiento":
            partes.append(_EJEMPLO_TRABAJO_ENTRET)
        elif tipo_contradiccion == "sin_tiempo_vs_entretenimiento":
            partes.append(_EJEMPLO_SIN_TIEMPO_ENTRET)

        # Cláusulas opcionales
        if clausula_independencia:
            partes.append(clausula_independencia)
        if clausula_preferencias:
            partes.append(clausula_preferencias)

        clausula_prompt = " ".join(partes)

        # 9. Retornar dict
        return {
            "contradiccion_detectada": contradiccion_detectada,
            "tipo_contradiccion": tipo_contradiccion,
            "nivel_sarcasmo": nivel_sarcasmo,
            "clausula_prompt": clausula_prompt,
            "ajuste_dopamina": ajuste_dopamina,
        }

    except Exception:
        return dict(_DICT_SEGURO)


# ---------------------------------------------------------------------------
# Clase pública SkepticismEngine (wrapper orientado a objetos)
# ---------------------------------------------------------------------------

class SkepticismEngine:
    """
    Wrapper orientado a objetos sobre las funciones del módulo.
    Permite instanciar el motor de escepticismo con estado propio.
    """

    def __init__(self):
        self._memory = ContradictionMemory()

    def evaluar(
        self,
        mensaje: str,
        apps_activas: list[str],
        atlas=None,
        emotion_engine=None,
    ) -> dict:
        """Delega a la función pública evaluar() del módulo."""
        return evaluar(mensaje, apps_activas, atlas=atlas, emotion_engine=emotion_engine)

    def get_nivel_sarcasmo(self) -> int:
        return _calcular_nivel_sarcasmo(self._memory.get_contador())
