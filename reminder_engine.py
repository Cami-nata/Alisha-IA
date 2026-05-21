"""
reminder_engine.py — Motor de recordatorios con alarmas reales.

Parsea expresiones de tiempo en español y dispara alertas de audio
usando threading.Timer en el momento correcto.
"""

import re
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional, Callable

try:
    from plyer import notification as _plyer_notification
    _PLYER_OK = True
except Exception:
    _PLYER_OK = False

from tts_engine import speak

# Mapeo de días de la semana en español
_DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}


def parsear_tiempo(cuando: str) -> datetime:
    """Convierte expresión temporal en español a datetime futuro.

    Soporta:
    - "en X minutos/horas/segundos"
    - "mañana a las H[pm/am]" / "mañana a las HH:MM"
    - "hoy a las H[pm/am]" / "hoy a las HH:MM"
    - "el lunes/martes/..." con hora opcional

    Raises:
        ValueError: si no se puede parsear o el tiempo ya pasó.
    """
    ahora = datetime.now()
    texto = cuando.strip().lower()

    # --- Patrón: "en X minutos/horas/segundos" ---
    m = re.search(r"en\s+(\d+)\s*(minuto|hora|segundo)", texto)
    if m:
        cantidad = int(m.group(1))
        unidad = m.group(2)
        if "hora" in unidad:
            delta = timedelta(hours=cantidad)
        elif "segundo" in unidad:
            delta = timedelta(seconds=cantidad)
        else:
            delta = timedelta(minutes=cantidad)
        return ahora + delta

    # --- Extraer hora de la expresión ---
    def _extraer_hora(t: str) -> Optional[datetime]:
        # HH:MM
        m2 = re.search(r"(\d{1,2}):(\d{2})", t)
        if m2:
            return ahora.replace(hour=int(m2.group(1)), minute=int(m2.group(2)), second=0, microsecond=0)
        # Xpm / Xam
        m3 = re.search(r"(\d{1,2})\s*(pm|am)", t)
        if m3:
            h = int(m3.group(1))
            if m3.group(2) == "pm" and h < 12:
                h += 12
            elif m3.group(2) == "am" and h == 12:
                h = 0
            return ahora.replace(hour=h, minute=0, second=0, microsecond=0)
        return None

    # --- Patrón: "mañana" ---
    if "mañana" in texto or "manana" in texto:
        base = ahora + timedelta(days=1)
        hora_dt = _extraer_hora(texto)
        if hora_dt:
            return base.replace(hour=hora_dt.hour, minute=hora_dt.minute, second=0, microsecond=0)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    # --- Patrón: "hoy a las" ---
    if "hoy" in texto:
        hora_dt = _extraer_hora(texto)
        if hora_dt is None:
            raise ValueError(f"No se pudo extraer la hora de: '{cuando}'")
        resultado = ahora.replace(hour=hora_dt.hour, minute=hora_dt.minute, second=0, microsecond=0)
        if resultado <= ahora:
            raise ValueError(f"El tiempo indicado ya pasó: '{cuando}'")
        return resultado

    # --- Patrón: día de la semana ---
    for nombre_dia, num_dia in _DIAS_SEMANA.items():
        if nombre_dia in texto:
            dias_hasta = (num_dia - ahora.weekday()) % 7
            if dias_hasta == 0:
                dias_hasta = 7
            base = ahora + timedelta(days=dias_hasta)
            hora_dt = _extraer_hora(texto)
            if hora_dt:
                return base.replace(hour=hora_dt.hour, minute=hora_dt.minute, second=0, microsecond=0)
            return base.replace(hour=9, minute=0, second=0, microsecond=0)

    raise ValueError(f"No se pudo interpretar el tiempo: '{cuando}'")


class ReminderEngine:
    """Singleton que gestiona recordatorios con alarmas reales."""

    _instance: Optional["ReminderEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._timers: dict[str, threading.Timer] = {}
                cls._instance._recordatorios: dict[str, dict] = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ReminderEngine":
        return cls()

    def programar_recordatorio(
        self,
        titulo: str,
        cuando: str,
        texto: str,
        callback: Optional[Callable] = None,
    ) -> str:
        """Programa un recordatorio. Retorna el ID único."""
        cuando_dt = parsear_tiempo(cuando)
        ahora = datetime.now()
        delta_segundos = (cuando_dt - ahora).total_seconds()
        if delta_segundos <= 0:
            raise ValueError(f"El tiempo indicado ya pasó: '{cuando}'")

        rid = str(uuid.uuid4())
        recordatorio = {
            "id": rid,
            "titulo": titulo,
            "cuando": cuando,
            "cuando_datetime": cuando_dt.isoformat(),
            "texto": texto,
            "completado": False,
            "disparado": False,
        }
        self._recordatorios[rid] = recordatorio

        timer = threading.Timer(delta_segundos, self._disparar, args=(rid, callback))
        timer.daemon = True
        timer.start()
        self._timers[rid] = timer
        return rid

    def cancelar_recordatorio(self, reminder_id: str) -> bool:
        """Cancela un recordatorio pendiente. Retorna True si existía."""
        timer = self._timers.pop(reminder_id, None)
        if timer:
            timer.cancel()
        rec = self._recordatorios.get(reminder_id)
        if rec:
            rec["completado"] = True
            return True
        return False

    def listar_pendientes(self) -> list:
        """Retorna lista de recordatorios activos con tiempo restante."""
        ahora = datetime.now()
        pendientes = []
        for rid, rec in self._recordatorios.items():
            if rec.get("completado") or rec.get("disparado"):
                continue
            try:
                cuando_dt = datetime.fromisoformat(rec["cuando_datetime"])
                restante = (cuando_dt - ahora).total_seconds()
                pendientes.append({**rec, "segundos_restantes": max(0, restante)})
            except Exception:
                pass
        return pendientes

    def restaurar_desde_memoria(self, recordatorios: list) -> None:
        """Restaura timers al arrancar desde la lista de recordatorios guardados."""
        ahora = datetime.now()
        for rec in recordatorios:
            if rec.get("completado") or rec.get("disparado"):
                continue
            cuando_str = rec.get("cuando_datetime") or rec.get("cuando", "")
            try:
                cuando_dt = datetime.fromisoformat(cuando_str)
            except Exception:
                try:
                    cuando_dt = parsear_tiempo(cuando_str)
                except Exception:
                    continue

            delta = (cuando_dt - ahora).total_seconds()
            if delta <= 0:
                # Ya pasó — notificar al arrancar
                speak(f"Recordatorio vencido: {rec.get('titulo', 'Recordatorio')}. {rec.get('texto', '')}")
                continue

            rid = rec.get("id", str(uuid.uuid4()))
            self._recordatorios[rid] = {**rec, "id": rid, "cuando_datetime": cuando_dt.isoformat()}
            timer = threading.Timer(delta, self._disparar, args=(rid, None))
            timer.daemon = True
            timer.start()
            self._timers[rid] = timer

    def _disparar(self, rid: str, callback: Optional[Callable]) -> None:
        """Callback interno cuando el timer se dispara."""
        rec = self._recordatorios.get(rid, {})
        rec["disparado"] = True
        titulo = rec.get("titulo", "Recordatorio")
        texto = rec.get("texto", "")
        mensaje = f"Recordatorio: {titulo}."
        if texto:
            mensaje += f" {texto}"

        speak(mensaje)

        if _PLYER_OK:
            try:
                _plyer_notification.notify(
                    title=f"⏰ {titulo}",
                    message=texto or titulo,
                    app_name="Asistente IA",
                    timeout=10,
                )
            except Exception:
                pass

        if callback:
            try:
                callback(rec)
            except Exception:
                pass

        self._timers.pop(rid, None)
