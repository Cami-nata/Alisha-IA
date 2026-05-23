"""
proactive_notifier.py — Módulo central de notificaciones proactivas de Alisha.

Evalúa triggers situacionales y emite notificaciones proactivas en voseo rioplatense
cuando detecta situaciones que merecen atención, sin que Camila tenga que preguntar.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from enum import Enum

from semantic_layer import _traduccion_semantica


# ---------------------------------------------------------------------------
# NotificationType
# ---------------------------------------------------------------------------

class NotificationType(str, Enum):
    TASK_REMINDER   = "task_reminder"
    NIGHT_ALERT     = "night_alert"
    BREAK_REMINDER  = "break_reminder"
    STRESS_DETECTOR = "stress_detector"
    FOCUS_MOTIVATOR = "focus_motivator"
    CONTEXT_SHIFT   = "context_shift"


# ---------------------------------------------------------------------------
# SilenceGuard
# ---------------------------------------------------------------------------

class SilenceGuard:
    """
    Impide que Alisha hable si ya lo hizo en los últimos VENTANA_MINUTOS minutos.
    """

    VENTANA_MINUTOS: int = 20  # 20 minutos entre notificaciones proactivas

    def __init__(self) -> None:
        self._ultima_emision: datetime | None = None

    def puede_emitir(self) -> bool:
        """
        Retorna True si han pasado >= VENTANA_MINUTOS desde la última emisión,
        o si nunca se emitió en esta sesión.
        """
        try:
            if self._ultima_emision is None:
                return True
            delta = datetime.now() - self._ultima_emision
            return delta >= timedelta(minutes=self.VENTANA_MINUTOS)
        except Exception:
            return True  # fail-silent: si algo falla, permitir emisión

    def registrar_emision(self) -> None:
        """Actualiza el timestamp de la última emisión al momento actual."""
        try:
            self._ultima_emision = datetime.now()
        except Exception:
            pass  # fail-silent


# ---------------------------------------------------------------------------
# AntiRepetitionGuard
# ---------------------------------------------------------------------------

class AntiRepetitionGuard:
    """
    Impide repetir el mismo tipo de notificación dentro de los últimos N emitidos.
    Usa un deque circular de tamaño `ventana` (default 3).
    Estado en memoria de sesión; se reinicia al arrancar Alisha.
    """

    def __init__(self, ventana: int = 3) -> None:
        self._historial: deque[str] = deque(maxlen=ventana)

    def puede_emitir(self, tipo: str) -> bool:
        """
        Retorna True si `tipo` NO está en los últimos `ventana` tipos emitidos.
        """
        try:
            return tipo not in self._historial
        except Exception:
            return True  # fail-silent

    def registrar_emision(self, tipo: str) -> None:
        """Agrega `tipo` al historial circular."""
        try:
            self._historial.append(tipo)
        except Exception:
            pass  # fail-silent

    @property
    def historial(self) -> list[str]:
        """Copia del historial actual (para tests e inspección)."""
        try:
            return list(self._historial)
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Funciones de evaluación de triggers
# ---------------------------------------------------------------------------

def evaluar_task_reminder(recordatorios: list[dict]) -> dict | None:
    """
    Retorna el recordatorio con fecha más próxima dentro de los próximos 2 días.

    Acepta campos de fecha: "fecha", "date", "vencimiento", "deadline".
    Ignora silenciosamente recordatorios sin fecha parseable.
    Retorna None si la lista está vacía o ninguno está en rango.
    """
    try:
        ahora = datetime.now() - timedelta(seconds=1)  # tolerancia para truncado de segundos
        limite = datetime.now() + timedelta(days=2)
        _CAMPOS_FECHA = ("fecha", "date", "vencimiento", "deadline")

        candidatos: list[tuple[datetime, dict]] = []
        for rec in recordatorios:
            try:
                fecha_str = None
                for campo in _CAMPOS_FECHA:
                    if campo in rec and rec[campo]:
                        fecha_str = str(rec[campo])
                        break
                if fecha_str is None:
                    continue
                # Intentar parsear con y sin hora
                fecha_dt: datetime | None = None
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                    try:
                        fecha_dt = datetime.strptime(fecha_str[:len(fmt)], fmt)
                        break
                    except ValueError:
                        continue
                if fecha_dt is None:
                    # Último intento con fromisoformat
                    try:
                        fecha_dt = datetime.fromisoformat(fecha_str)
                    except Exception:
                        continue
                if ahora <= fecha_dt <= limite:
                    candidatos.append((fecha_dt, rec))
            except Exception:
                continue  # fail-silent por recordatorio

        if not candidatos:
            return None
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]
    except Exception:
        return None


def evaluar_night_alert(sv: dict) -> bool:
    """
    Retorna True si hora_del_dia >= "23:00".
    Retorna False si el campo no existe o tiene formato inválido.
    """
    try:
        hora_str = sv.get("hora_del_dia")
        if not hora_str:
            return False
        partes = str(hora_str).split(":")
        hora = int(partes[0])
        minuto = int(partes[1]) if len(partes) > 1 else 0
        return hora >= 23 or (hora == 23 and minuto >= 0)
    except Exception:
        return False


def evaluar_break_reminder(ultima_inactividad: datetime | None) -> bool:
    """
    Retorna True si han pasado >= 90 minutos desde ultima_inactividad.
    Retorna False si ultima_inactividad es None.
    """
    try:
        if ultima_inactividad is None:
            return False
        delta = datetime.now() - ultima_inactividad
        return delta >= timedelta(minutes=90)
    except Exception:
        return False


def evaluar_stress_detector(sv: dict) -> bool:
    """
    Retorna True si:
      cambios_ventana_por_minuto > 3
      AND hora_del_dia >= "22:00"
      AND (bateria <= 20 OR bateria is None / no existe)
    Retorna False si falta cualquier condición.
    """
    try:
        # Condición 1: cambios de ventana
        cambios = sv.get("cambios_ventana_por_minuto")
        if cambios is None or float(cambios) <= 3:
            return False

        # Condición 2: hora >= 22:00
        hora_str = sv.get("hora_del_dia")
        if not hora_str:
            return False
        partes = str(hora_str).split(":")
        hora = int(partes[0])
        if hora < 22:
            return False

        # Condición 3: batería <= 20 o no disponible
        bateria = sv.get("bateria")
        if bateria is not None and float(bateria) > 20:
            return False

        return True
    except Exception:
        return False


def evaluar_focus_motivator(historial_svs: list[dict]) -> bool:
    """
    Retorna True si los últimos 3 SVs tienen la misma app_dominante
    y ritmo_escritura_promedio > 20 en todos.
    Retorna False si hay menos de 3 SVs en el historial.
    """
    try:
        if len(historial_svs) < 3:
            return False
        ultimos = historial_svs[-3:]
        app_ref = ultimos[0].get("app_dominante")
        if app_ref is None:
            return False
        for sv in ultimos:
            if sv.get("app_dominante") != app_ref:
                return False
            ritmo = sv.get("ritmo_escritura_promedio")
            if ritmo is None or float(ritmo) <= 20:
                return False
        return True
    except Exception:
        return False


def evaluar_context_shift(sv: dict, registro_anterior: dict | None) -> bool:
    """
    Retorna True si registro_anterior no es None Y el resumen_semantico
    del registro anterior difiere del resumen semántico del sv actual.
    Retorna False si registro_anterior es None o los resúmenes son iguales.
    """
    try:
        if registro_anterior is None:
            return False
        resumen_anterior = registro_anterior.get("resumen_semantico", "")
        # Obtener resumen del sv actual usando _traduccion_semantica
        app_dominante = sv.get("app_dominante") or ""
        titulo = sv.get("titulo_mas_frecuente") or ""
        apps_unicas = sv.get("apps_unicas") or []
        resumen_actual = _traduccion_semantica(app_dominante, titulo, apps_unicas)
        return resumen_anterior != resumen_actual
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Bloque de estilo obligatorio (incluido en todos los prompts)
# ---------------------------------------------------------------------------

_BLOQUE_ESTILO = (
    "Respondé en voseo rioplatense argentino. "
    "Usá expresiones como 'che', 'mirá vos', 'dale'. "
    "Hablá como una amiga sentada al lado.\n"
    "Máximo 2 oraciones. "
    "Prohibido mencionar datos técnicos: horas exactas, minutos, "
    "nombres de aplicaciones, porcentajes de batería.\n"
    "Hablá del significado y del estado emocional, nunca del evento técnico que lo disparó."
)


# ---------------------------------------------------------------------------
# Constructores de prompts (Tarea 4)
# ---------------------------------------------------------------------------

def prompt_task_reminder(recordatorio: dict) -> str:
    """Prompt para recordatorio de tarea/entrega."""
    titulo = recordatorio.get("titulo") or recordatorio.get("title") or "una entrega"
    descripcion = recordatorio.get("descripcion") or ""
    contexto = f"Título: {titulo}"
    if descripcion:
        contexto += f". Descripción: {descripcion}"
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        f"Sabés que Camila tiene una entrega próxima importante: {contexto}. "
        "Hablá del peso emocional de tener algo importante que se acerca, "
        "de la presión de la entrega, sin mencionar la fecha exacta ni el nombre literal de la tarea."
    )


def prompt_night_alert() -> str:
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        "Notás que Camila lleva mucho tiempo trabajando y el cuerpo ya pide descanso. "
        "Expresá preocupación genuina por su bienestar. "
        "Hablá del cansancio, no del horario. "
        "No menciones la hora exacta ni uses la palabra 'tarde'."
    )


def prompt_break_reminder() -> str:
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        "Notás que Camila lleva un buen rato sin alejarse de la pantalla. "
        "Sugerí que se tome un momento para estirarse o mirar a otro lado, "
        "sin mencionar cuántos minutos pasaron ni usar la palabra 'descanso'."
    )


def prompt_stress_detector() -> str:
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        "Notás que Camila parece dispersa o agotada. "
        "Expresá preocupación genuina con calidez, sin diagnosticar ni enumerar síntomas. "
        "No menciones señales técnicas ni datos del sistema."
    )


def prompt_focus_motivator() -> str:
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        "Notás que Camila está en un estado de flujo profundo. "
        "Expresá admiración genuina y aliento con humor suave. "
        "No menciones el nombre de la aplicación ni la cantidad de tiempo que lleva concentrada."
    )


def prompt_context_shift(resumen_ayer: str, resumen_hoy: str) -> str:
    return (
        f"{_BLOQUE_ESTILO}\n\n"
        "Recordás lo que Camila hacía ayer a esta hora. "
        f"Ayer: {resumen_ayer}. Hoy: {resumen_hoy}. "
        "Comentá el contraste con curiosidad genuina, como si fuera algo que te llamó la atención. "
        "No menciones datos técnicos ni nombres de aplicaciones."
    )


# ---------------------------------------------------------------------------
# truncar_a_2_oraciones (Tarea 5)
# ---------------------------------------------------------------------------

import re as _re


def truncar_a_2_oraciones(texto: str) -> str:
    """
    Retorna las primeras 2 oraciones si hay más de 2.
    Retorna el texto sin modificar si hay 2 o menos.
    Maneja puntuación española: '.', '!', '?', '...'
    """
    try:
        if not texto or not texto.strip():
            return texto
        # Dividir por terminadores de oración, conservando el terminador
        partes = _re.split(r'(?<=[.!?])\s+', texto.strip())
        # Filtrar partes vacías
        partes = [p for p in partes if p.strip()]
        if len(partes) <= 2:
            return texto
        return " ".join(partes[:2])
    except Exception:
        return texto


# ---------------------------------------------------------------------------
# _llamar_llm_proactivo (Tarea 5)
# ---------------------------------------------------------------------------

import json as _json
import requests as _requests


def _llamar_llm_proactivo(prompt: str) -> str | None:
    """
    Llama al LLM. Intenta Ollama primero, luego brain (Groq) como fallback.
    Retorna el texto generado o None en caso de error total.
    """
    # Intento 1: Ollama local (rápido si está disponible)
    try:
        payload = {
            "model": "llama3.1",
            "prompt": prompt,
            "stream": False,
        }
        response = _requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=8,  # timeout reducido para no bloquear
        )
        response.raise_for_status()
        texto = response.json().get("response", "").strip()
        if texto:
            return texto
    except Exception:
        pass

    # Fallback: brain (Groq/Mistral) — siempre disponible
    try:
        from brain import get_brain
        brain = get_brain()
        resp = brain.process(prompt)
        if resp and resp.content and resp.content.strip():
            return resp.content.strip()
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# ProactiveNotifier (Tarea 6)
# ---------------------------------------------------------------------------

import json as _json_mod
import os as _os
from typing import Callable


class ProactiveNotifier:
    """
    Orquestador central de notificaciones proactivas.
    Evalúa triggers en orden de prioridad y emite una notificación si corresponde.
    """

    # Orden de prioridad de triggers
    _PRIORIDAD = [
        NotificationType.TASK_REMINDER,
        NotificationType.STRESS_DETECTOR,
        NotificationType.NIGHT_ALERT,
        NotificationType.BREAK_REMINDER,
        NotificationType.FOCUS_MOTIVATOR,
        NotificationType.CONTEXT_SHIFT,
    ]

    def __init__(self) -> None:
        self._silence_guard = SilenceGuard()
        self._anti_rep_guard = AntiRepetitionGuard(ventana=5)
        self._ultima_inactividad: datetime | None = None

    def evaluar(
        self,
        sv: dict,
        atlas,
        historial_svs: list[dict],
        callback: Callable[[str], None],
    ) -> bool:
        """
        Evalúa todos los triggers en orden de prioridad.
        Retorna True si se emitió una notificación, False si no.
        Todo envuelto en try/except fail-silent.
        """
        try:
            # 1. SilenceGuard propio
            if not self._silence_guard.puede_emitir():
                return False

            # 2. Semáforo global de silencio
            try:
                from alisha_silencio import puede_hablar_proactivo
                if not puede_hablar_proactivo("proactive_notifier"):
                    return False
            except Exception:
                pass

            # 2. Leer ia_recuerdos.json
            recordatorios: list[dict] = []
            registro_anterior: dict | None = None
            try:
                ruta = _os.path.join(_os.path.dirname(__file__), "ia_recuerdos.json")
                with open(ruta, "r", encoding="utf-8") as f:
                    datos = _json_mod.load(f)
                recordatorios = datos.get("recordatorios", []) or []
            except Exception:
                pass

            # Obtener registro anterior del atlas si está disponible
            try:
                if atlas is not None and hasattr(atlas, "buscar_franja_horaria"):
                    registro_anterior = atlas.buscar_franja_horaria()
            except Exception:
                pass

            # 3. Evaluar triggers en orden de prioridad
            for tipo in self._PRIORIDAD:
                try:
                    activo = False

                    if tipo == NotificationType.TASK_REMINDER:
                        rec = evaluar_task_reminder(recordatorios)
                        activo = rec is not None
                    elif tipo == NotificationType.STRESS_DETECTOR:
                        activo = evaluar_stress_detector(sv)
                    elif tipo == NotificationType.NIGHT_ALERT:
                        activo = evaluar_night_alert(sv)
                    elif tipo == NotificationType.BREAK_REMINDER:
                        activo = evaluar_break_reminder(self._ultima_inactividad)
                    elif tipo == NotificationType.FOCUS_MOTIVATOR:
                        activo = evaluar_focus_motivator(historial_svs)
                    elif tipo == NotificationType.CONTEXT_SHIFT:
                        activo = evaluar_context_shift(sv, registro_anterior)

                    if not activo:
                        continue

                    # 3b. AntiRepetitionGuard
                    if not self._anti_rep_guard.puede_emitir(tipo.value):
                        continue

                    # 4. Construir prompt
                    if tipo == NotificationType.TASK_REMINDER:
                        rec = evaluar_task_reminder(recordatorios)
                        prompt = prompt_task_reminder(rec)
                    elif tipo == NotificationType.STRESS_DETECTOR:
                        prompt = prompt_stress_detector()
                    elif tipo == NotificationType.NIGHT_ALERT:
                        prompt = prompt_night_alert()
                    elif tipo == NotificationType.BREAK_REMINDER:
                        prompt = prompt_break_reminder()
                    elif tipo == NotificationType.FOCUS_MOTIVATOR:
                        prompt = prompt_focus_motivator()
                    elif tipo == NotificationType.CONTEXT_SHIFT:
                        resumen_ayer = (registro_anterior or {}).get("resumen_semantico", "")
                        app_dominante = sv.get("app_dominante") or ""
                        titulo = sv.get("titulo_mas_frecuente") or ""
                        apps_unicas = sv.get("apps_unicas") or []
                        try:
                            from semantic_layer import _traduccion_semantica
                            resumen_hoy = _traduccion_semantica(app_dominante, titulo, apps_unicas)
                        except Exception:
                            resumen_hoy = app_dominante
                        prompt = prompt_context_shift(resumen_ayer, resumen_hoy)
                    else:
                        continue

                    # 5. Llamar LLM
                    texto = _llamar_llm_proactivo(prompt)

                    # 6. Si LLM retorna texto: truncar, callback, registrar
                    if texto:
                        texto_truncado = truncar_a_2_oraciones(texto)
                        callback(texto_truncado)
                        self._silence_guard.registrar_emision()
                        self._anti_rep_guard.registrar_emision(tipo.value)
                        # Registrar en semáforo global
                        try:
                            from alisha_silencio import registrar_habla_proactivo
                            registrar_habla_proactivo("proactive_notifier")
                        except Exception:
                            pass
                        return True

                    # 7. Si LLM falla: retornar False
                    return False

                except Exception:
                    continue  # fail-silent por trigger

            # 8. Ningún trigger pasó
            return False

        except Exception:
            return False  # fail-silent global

    def actualizar_inactividad(self, sv: dict) -> None:
        """
        Actualiza _ultima_inactividad si actividad_detectada es False
        o ritmo_escritura_promedio == 0.
        """
        try:
            actividad = sv.get("actividad_detectada", True)
            ritmo = sv.get("ritmo_escritura_promedio", 1)
            if actividad is False or ritmo == 0:
                self._ultima_inactividad = datetime.now()
        except Exception:
            pass  # fail-silent
