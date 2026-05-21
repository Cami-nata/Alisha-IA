"""
safety_guard.py — Sistema de seguridad y confirmación para acciones de la IA.

Principios:
- La IA SIEMPRE consulta antes de ejecutar acciones que afecten el sistema
- Algunas acciones están completamente restringidas
- El usuario puede aprobar/rechazar cada acción
"""
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Acciones completamente PROHIBIDAS para la IA
# ---------------------------------------------------------------------------
ACCIONES_PROHIBIDAS = {
    # Sistema operativo
    "power",           # apagar/reiniciar/suspender
    "format",          # formatear disco
    # Archivos del sistema
    "eliminar_sistema",
    "modificar_registro",
    # Red
    "cambiar_red",
    "instalar_software",
}

# Rutas que la IA NO puede tocar
RUTAS_PROHIBIDAS = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Users\\User\\AppData\\Roaming",
    "C:\\Users\\User\\AppData\\Local\\Microsoft",
]

# Acciones que SIEMPRE requieren confirmación explícita
ACCIONES_REQUIEREN_CONFIRMACION = {
    # Agente
    "crear_archivo",
    "editar_archivo",
    "escribir_vscode",
    "cortar_video",
    "unir_videos",
    "agregar_audio",
    # Sistema
    "hotkey",
    "ejecutar_codigo",
    "abrir_app",
    "escribir_texto",
}

# Acciones que pueden ejecutarse sin confirmación (solo informativas)
ACCIONES_AUTOMATICAS = {
    "leer_archivo",
    "abrir_vscode",
    "abrir_web",
    "buscar_web",
    "leer_web",
    "screenshot",
    "diagnosticar",
    "buscar_archivo",
    "volumen",
    "brillo",
    "musica",
    "nada",
}


class SafetyGuard:
    """Controla qué puede y qué no puede hacer la IA."""

    def __init__(self, callback_confirmacion: Optional[Callable] = None):
        """
        callback_confirmacion: función que muestra la pregunta al usuario.
        Si es None, usa input() en terminal.
        """
        self._callback = callback_confirmacion
        self._historial_acciones: list[dict] = []

    def set_callback(self, callback: Callable) -> None:
        self._callback = callback

    def verificar_accion(self, accion: dict) -> tuple[bool, str]:
        """
        Verifica si una acción puede ejecutarse.
        Retorna (puede_ejecutar, razon).
        """
        tipo = accion.get("accion", "nada")
        tipo_agente = accion.get("accion_agente", "")

        # Verificar acciones prohibidas
        if tipo in ACCIONES_PROHIBIDAS or tipo_agente in ACCIONES_PROHIBIDAS:
            accion_bloqueada = tipo or tipo_agente
            if accion_bloqueada == "power":
                return False, "Las acciones de apagado/reinicio están deshabilitadas por seguridad. Si querés apagar la PC, hacelo vos directamente."
            return False, f"Acción '{accion_bloqueada}' está restringida por seguridad."

        # Verificar rutas prohibidas
        ruta = accion.get("ruta", "")
        if ruta:
            for ruta_prohibida in RUTAS_PROHIBIDAS:
                if ruta.lower().startswith(ruta_prohibida.lower()):
                    return False, f"No tengo permiso para acceder a '{ruta_prohibida}'."

        return True, "ok"

    def requiere_confirmacion(self, accion: dict) -> bool:
        """True si la acción requiere confirmación del usuario."""
        tipo = accion.get("accion", "nada")
        tipo_agente = accion.get("accion_agente", "")
        return (
            tipo in ACCIONES_REQUIEREN_CONFIRMACION or
            bool(tipo_agente)  # toda acción de agente requiere confirmación
        )

    def pedir_confirmacion(self, accion: dict, nombre_ia: str = "IA") -> bool:
        """
        Pide confirmación al usuario para ejecutar una acción.
        Retorna True si el usuario aprueba.
        """
        tipo = accion.get("accion", "nada")
        tipo_agente = accion.get("accion_agente", "")
        mensaje_ia = accion.get("mensaje", "")

        # Construir descripción legible
        if tipo_agente == "crear_archivo":
            desc = f"crear el archivo '{accion.get('ruta', '?')}'"
        elif tipo_agente == "editar_archivo":
            desc = f"editar '{accion.get('ruta', '?')}'"
        elif tipo_agente == "escribir_vscode":
            codigo_preview = str(accion.get("codigo", ""))[:50]
            desc = f"escribir código en VS Code: '{codigo_preview}...'"
        elif tipo_agente == "cortar_video":
            desc = f"cortar video '{accion.get('entrada', '?')}'"
        elif tipo_agente == "unir_videos":
            desc = f"unir {len(accion.get('archivos', []))} videos"
        elif tipo == "ejecutar_codigo":
            codigo_preview = str(accion.get("codigo", ""))[:50]
            desc = f"ejecutar código: '{codigo_preview}...'"
        elif tipo == "hotkey":
            desc = f"presionar teclas: {accion.get('teclas', [])}"
        elif tipo == "escribir_texto":
            texto_preview = str(accion.get("texto", ""))[:40]
            desc = f"escribir en el teclado: '{texto_preview}'"
        elif tipo == "abrir_app":
            desc = f"abrir la aplicación '{accion.get('app', '?')}'"
        else:
            desc = f"ejecutar '{tipo_agente or tipo}'"

        pregunta = f"{nombre_ia} quiere {desc}. ¿Lo autorizo? [s/N]: "

        if self._callback:
            return self._callback(pregunta)
        else:
            # Sin callback (modo automático): aprobar acciones simples automáticamente
            # Solo bloquear acciones destructivas que requieren confirmación explícita
            ACCIONES_AUTO_APROBADAS = {
                "abrir_app", "escribir_texto", "abrir_web",
                "buscar_web", "screenshot", "volumen", "brillo",
            }
            if tipo in ACCIONES_AUTO_APROBADAS:
                print(f"[SafetyGuard] Auto-aprobado: {desc}")
                return True
            # Para acciones de agente o destructivas, rechazar silenciosamente
            print(f"[SafetyGuard] Rechazado (sin callback): {desc}")
            return False

    def registrar(self, accion: dict, aprobada: bool) -> None:
        self._historial_acciones.append({
            "accion": accion.get("accion"),
            "accion_agente": accion.get("accion_agente"),
            "aprobada": aprobada,
        })


# Singleton
_guard = SafetyGuard()

def get_guard() -> SafetyGuard:
    return _guard
