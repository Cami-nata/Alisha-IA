"""
Semantic_Layer — traducción semántica y construcción de prompts.
Parte del sistema de Conciencia Situacional de Alisha.
"""

from collections import Counter


# ---------------------------------------------------------------------------
# Categorías semánticas de apps
# ---------------------------------------------------------------------------

_APPS_DISEÑO = {
    "photoshop", "canva", "illustrator", "figma", "inkscape",
    "photoshop.exe", "illustrator.exe", "inkscape.exe",
}

_APPS_CODIGO = {
    "code.exe", "vscode", "pycharm", "sublime", "pycharm64.exe",
    "sublime_text.exe", "sublime text",
}

_APPS_TEXTO_CV = {
    "word", "winword.exe", "libreoffice", "soffice.exe",
}

_APPS_NAVEGADOR = {
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
}

_APPS_TRABAJO = _APPS_DISEÑO | _APPS_CODIGO | _APPS_TEXTO_CV

_PALABRAS_CV = {"cv", "curriculum", "currículum", "resume", "hoja de vida"}

_EDITORES_CODIGO = {
    "code.exe", "vscode", "pycharm", "pycharm64.exe",
    "sublime", "sublime_text.exe", "sublime text",
}

_APPS_EXPLORADOR = {"explorer.exe", "papelera", "recycle bin", "recyclebin"}


# ---------------------------------------------------------------------------
# Helpers de categorización
# ---------------------------------------------------------------------------

def _normalizar(nombre: str) -> str:
    return (nombre or "").lower().strip()


def _es_diseño(app: str) -> bool:
    return _normalizar(app) in _APPS_DISEÑO


def _es_codigo(app: str) -> bool:
    return _normalizar(app) in _APPS_CODIGO


def _es_texto_cv(app: str, titulo: str = "") -> bool:
    app_n = _normalizar(app)
    if app_n not in _APPS_TEXTO_CV:
        return False
    titulo_n = _normalizar(titulo)
    return any(p in titulo_n for p in _PALABRAS_CV)


def _es_navegador(app: str) -> bool:
    return _normalizar(app) in _APPS_NAVEGADOR


def _es_trabajo(app: str, titulo: str = "") -> bool:
    app_n = _normalizar(app)
    if app_n in _APPS_DISEÑO or app_n in _APPS_CODIGO:
        return True
    if app_n in _APPS_TEXTO_CV:
        return True
    return False


def _es_editor_codigo(app: str) -> bool:
    return _normalizar(app) in _EDITORES_CODIGO


def _es_explorador(app: str) -> bool:
    return _normalizar(app) in _APPS_EXPLORADOR


def _hora_es_nocturna(hora_str: str) -> bool:
    """Retorna True si la hora está entre 22:00 y 02:00 (inclusive)."""
    try:
        partes = hora_str.split(":")
        h = int(partes[0])
        return h >= 22 or h <= 2
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Función pura principal
# ---------------------------------------------------------------------------

def construir_prompt(
    sv: dict,
    historial_apps: Counter,
    registro_anterior: dict | None,
) -> str:
    """
    Construye el prompt para el LLM a partir del State_Vector,
    el historial de frecuencia de apps y el registro anterior del Atlas.

    Args:
        sv: State_Vector generado por state_vector.py
        historial_apps: Counter con frecuencia de apps en la sesión actual
        registro_anterior: Registro del Atlas_Memory del día anterior (o None)

    Returns:
        String con el prompt completo listo para enviar al LLM.
    """
    partes: list[str] = []

    app_dominante = sv.get("app_dominante") or ""
    titulo = sv.get("titulo_mas_frecuente") or ""
    bateria = sv.get("bateria")
    hora = sv.get("hora_del_dia") or ""
    apps_unicas = sv.get("apps_unicas") or []

    # 1. Traducción semántica por categoría
    traduccion = _traduccion_semantica(app_dominante, titulo, apps_unicas)
    if traduccion:
        partes.append(traduccion)

    # 2. Comparación temporal si hay registro anterior
    if registro_anterior is not None:
        resumen_anterior = registro_anterior.get("resumen_semantico", "")
        resumen_actual = _resumen_actual(app_dominante, titulo)
        if resumen_anterior:
            partes.append(
                f"Ayer a esta hora Camila estaba haciendo {resumen_anterior}. "
                f"Hoy está haciendo {resumen_actual}. "
                "Si hay un contraste interesante, mencionalo con naturalidad."
            )

    # 3. Empatía nocturna
    if (
        isinstance(bateria, (int, float))
        and bateria <= 20
        and _hora_es_nocturna(hora)
        and _es_trabajo(app_dominante, titulo)
    ):
        partes.append(
            "Camila parece cansada pero esforzándose por terminar algo. Sé empática."
        )

    # 4. Cláusulas de personalidad
    partes.extend(_clausulas_personalidad(app_dominante, historial_apps))

    # 5. Instrucciones obligatorias (siempre al final)
    partes.append(
        "Respondé siempre en voseo rioplatense argentino. "
        "Usá expresiones como 'che', 'mirá vos', 'dale', 'bárbaro'. "
        "Hablá como una amiga sentada al lado, no como un asistente técnico."
    )
    partes.append(
        "Prohibido usar verbos literales como abrir, cliquear, escribir, navegar."
    )
    partes.append(
        "Prohibido el lenguaje técnico. "
        "Prohibido mencionar nombres de aplicaciones o archivos directamente."
    )
    partes.append("Respondé con máximo 2 oraciones.")

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Helpers de construcción del prompt
# ---------------------------------------------------------------------------

def _traduccion_semantica(app: str, titulo: str, apps_unicas: list) -> str:
    """Retorna la traducción semántica correspondiente a la app dominante."""
    if _es_diseño(app):
        return "Camila está siendo creativa"
    if _es_codigo(app):
        return "Camila está en modo técnico"
    if _es_texto_cv(app, titulo):
        return "Camila está trabajando en su perfil profesional"
    if _es_navegador(app):
        # Múltiples pestañas → investigando
        if len(apps_unicas) > 1 or _es_navegador(app):
            return "Camila está investigando o buscando algo"
    return ""


def _resumen_actual(app: str, titulo: str) -> str:
    """Genera un resumen semántico breve del estado actual."""
    if _es_diseño(app):
        return "algo creativo"
    if _es_codigo(app):
        return "algo técnico"
    if _es_texto_cv(app, titulo):
        return "su perfil profesional"
    if _es_navegador(app):
        return "investigando o buscando algo"
    return "algo"


def _clausulas_personalidad(app: str, historial_apps: Counter) -> list[str]:
    """Genera cláusulas de personalidad según el historial de la sesión."""
    clausulas: list[str] = []

    # Curiosidad ante app nueva (antes de verificar otras condiciones)
    if app and app not in historial_apps:
        clausulas.append(
            "Camila está usando algo nuevo. Podés mostrar curiosidad genuina."
        )
        return clausulas  # Si es nueva, no aplican las otras cláusulas de historial

    # VS Code / editor dominante en últimos 5 ciclos
    ultimos_5 = _apps_dominantes_ultimos_n(historial_apps, n=5)
    if any(_es_editor_codigo(a) for a in ultimos_5):
        clausulas.append(
            "A Alisha le gusta el 'olor' del código. "
            "Podés hacer una referencia afectiva a programar."
        )

    # Explorer / papelera frecuente
    if any(_es_explorador(a) for a in historial_apps):
        clausulas.append(
            "Alisha se aburre cuando Camila está en la papelera. "
            "Podés expresar leve tedio con humor."
        )

    return clausulas


def _apps_dominantes_ultimos_n(historial_apps: Counter, n: int) -> list[str]:
    """
    Retorna las apps que aparecen entre las más comunes del historial,
    simulando los últimos N ciclos como las N apps más frecuentes.
    """
    return [app for app, _ in historial_apps.most_common(n)]


# ---------------------------------------------------------------------------
# Función auxiliar para detección de inactividad (Property 11)
# ---------------------------------------------------------------------------

def detectar_inactividad(historial_svs: list[dict]) -> bool:
    """
    Retorna True si los últimos 3 State_Vectors consecutivos tienen
    la misma app_dominante y total_cambios_ventana == 0 en todos.

    Args:
        historial_svs: Lista de State_Vectors (se usan los últimos 3).
    """
    if len(historial_svs) < 3:
        return False
    ultimos = historial_svs[-3:]
    app_ref = ultimos[0].get("app_dominante")
    return all(
        sv.get("app_dominante") == app_ref and sv.get("total_cambios_ventana") == 0
        for sv in ultimos
    )


# ---------------------------------------------------------------------------
# Clase SemanticLayer (encapsula estado para uso en producción)
# ---------------------------------------------------------------------------

class SemanticLayer:
    """
    Encapsula el historial de frecuencia de apps en memoria de sesión.
    Provee métodos de instancia que delegan en las funciones puras.
    """

    def __init__(self) -> None:
        self._historial_apps: Counter = Counter()

    def actualizar_historial(self, sv: dict) -> None:
        """
        Actualiza el Counter de frecuencia de apps con el app_dominante
        del State_Vector dado.

        Args:
            sv: State_Vector generado por state_vector.py
        """
        try:
            app = sv.get("app_dominante")
            if app:
                self._historial_apps[app] += 1
        except Exception:
            pass

    def construir_prompt(
        self,
        sv: dict,
        registro_anterior: dict | None = None,
    ) -> str:
        """
        Construye el prompt usando el historial interno de la sesión.

        Args:
            sv: State_Vector generado por state_vector.py
            registro_anterior: Registro del Atlas_Memory del día anterior (o None)

        Returns:
            String con el prompt completo listo para enviar al LLM.
        """
        return construir_prompt(sv, self._historial_apps, registro_anterior)

    @property
    def historial_apps(self) -> Counter:
        """Expone el historial de apps (solo lectura recomendada)."""
        return Counter(self._historial_apps)
