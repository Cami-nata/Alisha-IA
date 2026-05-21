"""
atlas_memory.py — Memoria de largo plazo comparativa (Atlas).
Parte del sistema de Conciencia Situacional de Alisha.

Lee/escribe la clave `atlas_situacional` en `ia_recuerdos.json`
sin tocar las claves `recuerdos` ni `temas`.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

from semantic_layer import _traduccion_semantica

from config import DATA_DIR
MEMORY_FILE = DATA_DIR / "ia_recuerdos.json"
_ATLAS_KEY = "atlas_situacional"
_MAX_DIAS = 7


class AtlasMemory:
    """Memoria de largo plazo comparativa — extiende ia_recuerdos.json."""

    def __init__(self, memory_file: Path = MEMORY_FILE) -> None:
        self._file = memory_file
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Persistencia interna
    # ------------------------------------------------------------------

    def _leer(self) -> list[dict]:
        """Lee la lista atlas_situacional del archivo. Graceful degradation."""
        try:
            if not self._file.exists():
                return []
            data = json.loads(self._file.read_text(encoding="utf-8"))
            return list(data.get(_ATLAS_KEY, []))
        except Exception:
            return []

    def _escribir(self, registros: list[dict]) -> None:
        """Escribe la lista atlas_situacional preservando el resto del archivo."""
        try:
            # Leer el contenido existente para no pisar otras claves
            if self._file.exists():
                try:
                    data = json.loads(self._file.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            else:
                data = {}

            data[_ATLAS_KEY] = registros
            self._file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def guardar_ciclo(self, sv: dict) -> None:
        """
        Agrega un registro al atlas a partir del State_Vector dado.

        Campos guardados: timestamp, hora_franja, apps_unicas,
        app_dominante, ritmo_escritura_promedio, resumen_semantico.
        """
        try:
            app_dominante = sv.get("app_dominante") or ""
            titulo = sv.get("titulo_mas_frecuente") or ""
            apps_unicas = sv.get("apps_unicas") or []

            resumen = _traduccion_semantica(app_dominante, titulo, apps_unicas)
            if not resumen:
                resumen = "Camila estaba trabajando en algo"

            ahora = datetime.now()
            registro = {
                "timestamp": ahora.isoformat(timespec="seconds"),
                "hora_franja": ahora.strftime("%H:%M"),
                "apps_unicas": list(apps_unicas),
                "app_dominante": app_dominante,
                "ritmo_escritura_promedio": sv.get("ritmo_escritura_promedio", 0),
                "resumen_semantico": resumen,
            }

            with self._lock:
                registros = self._leer()
                registros.append(registro)
                self._escribir(registros)
        except Exception:
            pass

    def buscar_franja_horaria(self, hora: datetime) -> dict | None:
        """
        Busca un registro del día anterior en la franja ±30 minutos.
        Usa caché en memoria para no leer disco en cada interacción.
        """
        # Caché: clave = fecha+hora redondeada a 30min
        cache_key = hora.strftime("%Y-%m-%d-%H") + str(hora.minute // 30)
        if hasattr(self, "_cache") and cache_key in self._cache:
            return self._cache[cache_key]

        if not hasattr(self, "_cache"):
            self._cache = {}

        try:
            ayer = hora - timedelta(days=1)
            ayer_fecha = ayer.date()
            ventana = timedelta(minutes=30)

            with self._lock:
                registros = self._leer()

            candidatos = []
            for r in registros:
                try:
                    ts = datetime.fromisoformat(r["timestamp"])
                    if ts.date() != ayer_fecha:
                        continue
                    ts_ref = hora.replace(year=ts.year, month=ts.month, day=ts.day,
                                          second=0, microsecond=0)
                    ts_cmp = ts.replace(second=0, microsecond=0)
                    diff = abs((ts_cmp - ts_ref).total_seconds())
                    if diff <= ventana.total_seconds():
                        candidatos.append((diff, r))
                except Exception:
                    continue

            if not candidatos:
                return None
            candidatos.sort(key=lambda x: x[0])
            return candidatos[0][1]
        except Exception:
            return None

    def limpiar_antiguos(self) -> None:
        """Elimina registros con timestamp de más de 7 días de antigüedad."""
        try:
            # Comparar por fecha (sin hora) para evitar problemas de microsegundos
            # en el límite exacto de 7 días.
            limite_fecha = (datetime.now() - timedelta(days=_MAX_DIAS)).date()
            with self._lock:
                registros = self._leer()
                nuevos = []
                for r in registros:
                    try:
                        ts = datetime.fromisoformat(r["timestamp"])
                        if ts.date() >= limite_fecha:
                            nuevos.append(r)
                    except Exception:
                        # Si el timestamp es inválido, descartar el registro
                        pass
                self._escribir(nuevos)
        except Exception:
            pass
