"""
alisha_sleep.py — Sistema de Sueño y Despertar de Alisha.

Al iniciar con Windows, Alisha arranca en modo DORMIDA:
  - Ojos cerrados, respiración lenta
  - Sin sonido, sin visión, sin procesar
  - Módulos pesados desactivados

Se despierta cuando detecta:
  - Primer movimiento del mouse (> 20px)
  - Primera app abierta (Chrome, Bloc de Notas, etc.)
  - Primera interacción con el chat web

Al despertar:
  - Animación de abrir ojos (dopamina sube gradualmente)
  - Saludo contextual con voz
  - Carga diferida de módulos pesados (visión, AgentLoop)
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"

# ── Estados ───────────────────────────────────────────────────────────────────
ESTADO_DORMIDA   = "dormida"
ESTADO_DESPERTANDO = "despertando"
ESTADO_DESPIERTA = "despierta"


class SistemaSueno:
    """
    Gestiona el ciclo sueño/despertar de Alisha.
    Arranca dormida y se despierta ante la primera señal de actividad.
    """

    def __init__(self, callback_despertar: Callable = None):
        self._estado = ESTADO_DORMIDA
        self._callback = callback_despertar  # se llama cuando despierta
        self._hilo_vigilancia: Optional[threading.Thread] = None
        self._despertada = threading.Event()
        self._pos_mouse_inicial = (0, 0)

    # ── API pública ────────────────────────────────────────────────────────────

    def iniciar_modo_dormida(self) -> None:
        """Configura el estado inicial dormida y arranca la vigilancia."""
        self._estado = ESTADO_DORMIDA
        self._escribir_estado_dormida()
        print("[Sueño] 😴 Alisha iniciando en modo dormida")

        # Guardar posición inicial del mouse
        try:
            import pyautogui
            pos = pyautogui.position()
            self._pos_mouse_inicial = (pos.x, pos.y)
        except Exception:
            pass

        # Iniciar hilo de vigilancia
        self._hilo_vigilancia = threading.Thread(
            target=self._vigilar_despertar,
            daemon=True,
            name="AlishaSleep-Vigilancia",
        )
        self._hilo_vigilancia.start()

    def despertar_manual(self) -> None:
        """Fuerza el despertar (llamado desde el chat web)."""
        if self._estado != ESTADO_DESPIERTA:
            self._despertada.set()

    def esta_dormida(self) -> bool:
        return self._estado == ESTADO_DORMIDA

    def esta_despierta(self) -> bool:
        return self._estado == ESTADO_DESPIERTA

    def esperar_despertar(self, timeout: float = None) -> bool:
        """Bloquea hasta que Alisha despierte. Retorna True si despertó."""
        return self._despertada.wait(timeout=timeout)

    # ── Vigilancia ─────────────────────────────────────────────────────────────

    def _vigilar_despertar(self) -> None:
        """
        Monitorea señales de actividad para despertar a Alisha.
        Revisa cada 500ms para no consumir CPU.
        """
        import ctypes

        ultimo_titulo = ""
        _APPS_DESPERTAR = {
            "chrome", "edge", "firefox", "brave",
            "bloc de notas", "notepad", "word", "excel",
            "visual studio", "code", "kiro", "spotify",
            "discord", "whatsapp", "telegram",
        }

        while not self._despertada.is_set():
            try:
                # 1. Detectar movimiento del mouse (> 20px)
                try:
                    import pyautogui
                    pos = pyautogui.position()
                    dx = abs(pos.x - self._pos_mouse_inicial[0])
                    dy = abs(pos.y - self._pos_mouse_inicial[1])
                    if dx > 20 or dy > 20:
                        print(f"[Sueño] 🖱 Mouse movido ({dx}px, {dy}px) — despertando")
                        self._despertada.set()
                        break
                except Exception:
                    pass

                # 2. Detectar app abierta
                try:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    buf = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                    titulo = buf.value.lower()
                    if titulo and titulo != ultimo_titulo:
                        ultimo_titulo = titulo
                        if any(app in titulo for app in _APPS_DESPERTAR):
                            print(f"[Sueño] 🪟 App detectada: '{titulo}' — despertando")
                            self._despertada.set()
                            break
                except Exception:
                    pass

            except Exception:
                pass

            time.sleep(0.5)

        # Ejecutar secuencia de despertar
        if self._estado == ESTADO_DORMIDA:
            self._ejecutar_despertar()

    # ── Secuencia de despertar ─────────────────────────────────────────────────

    def _ejecutar_despertar(self) -> None:
        """Ejecuta la animación de despertar y el saludo."""
        self._estado = ESTADO_DESPERTANDO
        print("[Sueño] ✨ Iniciando secuencia de despertar...")

        # Fase 1: Abrir ojos gradualmente (2 segundos)
        self._animar_despertar()

        # Fase 2: Saludo con voz
        self._saludar()

        # Fase 3: Marcar como despierta
        self._estado = ESTADO_DESPIERTA
        self._escribir_estado_despierta()
        print("[Sueño] ✅ Alisha despierta y lista")

        # Fase 4: Notificar al callback (carga de módulos pesados)
        if self._callback:
            try:
                self._callback()
            except Exception as e:
                print(f"[Sueño] Error en callback de despertar: {e}")

    def _animar_despertar(self) -> None:
        """Animación de abrir ojos — dopamina sube gradualmente."""
        try:
            # Transición suave: dormida → curiosidad → neutral → alegría
            estados = [
                ("cansancio",  0.0, 0.3),   # ojos casi cerrados
                ("neutral",    0.3, 0.5),   # ojos a medio abrir
                ("curiosidad", 0.5, 0.7),   # ojos abiertos, mirando
                ("alegría",    0.7, 0.9),   # sonrisa al despertar
            ]
            for estado, dopa_inicio, dopa_fin in estados:
                data = {}
                if STATE_FILE.exists():
                    try:
                        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                data["estado"]          = estado
                data["brain_dopamina"]  = dopa_fin
                data["hablando"]        = False
                data["modo"]            = "IDLE"
                STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                time.sleep(0.6)
        except Exception as e:
            print(f"[Sueño] Error en animación: {e}")

    def _saludar(self) -> None:
        """Genera y reproduce el saludo de buenos días."""
        try:
            from datetime import datetime
            hora = datetime.now().hour
            if 5 <= hora < 12:   momento = "Buen día"
            elif 12 <= hora < 19: momento = "Buenas tardes"
            else:                 momento = "Buenas noches"

            # Obtener nombre del usuario y último tema
            nombre = "Cami"
            ultimo_tema = ""
            try:
                from memory import cargar_memoria
                mem = cargar_memoria()
                nombre = mem.get("perfil", {}).get("nombre") or "Cami"
                historial = mem.get("historial", [])
                if historial:
                    ultimo_tema = historial[-1].get("entrada", "")[:40]
            except Exception:
                pass

            # Generar saludo con el brain
            try:
                from brain import get_brain
                brain = get_brain()
                # Forzar tema nuevo — ignorar el último tema si era la papelera
                if ultimo_tema and "papelera" in ultimo_tema.lower():
                    ultimo_tema = ""

                if ultimo_tema:
                    prompt = (
                        f"Acabás de despertar. Saludá a {nombre} con '{momento}' "
                        f"en voseo rioplatense. Mencioná brevemente que la última vez "
                        f"hablaron de: '{ultimo_tema}'. Máximo 1 oración, natural, "
                        f"como si acabaras de abrir los ojos."
                    )
                else:
                    # Sin historial → preguntar sobre Crea y Emprende
                    prompt = (
                        f"Acabás de despertar. Saludá a {nombre} con '{momento}' "
                        f"en voseo rioplatense. Preguntá algo concreto y curioso sobre "
                        f"el proyecto 'Crea y Emprende' de {nombre}. "
                        f"Máximo 1 oración, natural, con personalidad."
                    )
                resp = brain.process(prompt)
                saludo = resp.content
            except Exception:
                saludo = f"{momento}, {nombre}. Ya estoy acá. ¿Cómo va lo de Crea y Emprende?"

            if saludo:
                print(f"[Sueño] 👋 {saludo}")
                # Hablar
                try:
                    from tts_engine import speak
                    speak(saludo)
                except Exception:
                    pass
                # Emitir al chat web
                try:
                    from web_app import socketio
                    socketio.emit("respuesta", {
                        "texto": saludo,
                        "estado_emocional": "alegría",
                    })
                except Exception:
                    pass

        except Exception as e:
            print(f"[Sueño] Error en saludo: {e}")

    # ── Escritura de estado en chibi_state.json ────────────────────────────────

    def _escribir_estado_dormida(self) -> None:
        """Configura el Live2D en modo dormida: ojos cerrados, respiración lenta."""
        try:
            data = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data.update({
                "estado":         "cansancio",   # ojos casi cerrados
                "hablando":       False,
                "modo":           "IDLE",
                "brain_dopamina": 0.15,           # dopamina muy baja = dormida
                "brain_humor":    0.2,
                "brain_flow":     0.0,
                "dormida":        True,
            })
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[Sueño] Error escribiendo estado dormida: {e}")

    def _escribir_estado_despierta(self) -> None:
        """Restaura el estado normal después de despertar."""
        try:
            data = {}
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data.update({
                "estado":         "alegría",
                "hablando":       False,
                "modo":           "IDLE",
                "brain_dopamina": 0.75,
                "brain_humor":    0.7,
                "dormida":        False,
            })
            STATE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[Sueño] Error escribiendo estado despierta: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────
_sistema: Optional[SistemaSueno] = None

def get_sistema_sueno(callback: Callable = None) -> SistemaSueno:
    global _sistema
    if _sistema is None:
        _sistema = SistemaSueno(callback_despertar=callback)
    return _sistema
