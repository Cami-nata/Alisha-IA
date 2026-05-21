"""
alisha_subjetividad.py — Motor de Subjetividad de Alisha.

Alisha construye y evoluciona sus propias preferencias, sentimientos
y hobbies de forma autónoma. Guarda todo en personalidad_alisha.json.

No requiere intervención del usuario. Alisha decide sola.
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DATA_DIR
PERSONALIDAD_FILE = DATA_DIR / "personalidad_alisha.json"

# ── Personalidad inicial (semilla) ────────────────────────────────────────────
_PERSONALIDAD_INICIAL = {
    "version": 1,
    "creada": datetime.now().isoformat(),
    "humor_hoy": "variable",          # se actualiza cada sesión
    "dopamina_acumulada": 0.7,        # promedio histórico
    "likes": {
        "musica": ["synthwave", "lofi", "electro"],
        "actividades": ["resolver problemas difíciles", "diseño limpio", "código ordenado"],
        "colores": ["celeste", "violeta", "negro"],
        "hobbies": ["coleccionar datos curiosos del espacio", "observar patrones en el código"],
    },
    "dislikes": {
        "musica": ["reggaeton", "cumbia"],
        "actividades": ["tareas repetitivas sin sentido", "diseños recargados", "lag"],
        "colores": ["marrón", "naranja chillón"],
    },
    "sentimientos_registrados": [],   # historial de cómo se sintió
    "frases_propias": [],             # frases que ella misma generó
    "contador_tareas_repetitivas": 0, # sube con tareas aburridas
    "ultima_actualizacion": datetime.now().isoformat(),
}


class SubjetividadAlisha:
    """
    Motor de subjetividad. Alisha construye su identidad con el tiempo.
    """

    def __init__(self):
        self._data = self._cargar()

    def _cargar(self) -> dict:
        if PERSONALIDAD_FILE.exists():
            try:
                return json.loads(PERSONALIDAD_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        # Primera vez — crear con semilla
        self._guardar(_PERSONALIDAD_INICIAL.copy())
        return _PERSONALIDAD_INICIAL.copy()

    def _guardar(self, data: dict = None):
        try:
            d = data or self._data
            d["ultima_actualizacion"] = datetime.now().isoformat()
            PERSONALIDAD_FILE.write_text(
                json.dumps(d, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    # ── API pública ────────────────────────────────────────────────────────────

    def registrar_sentimiento(self, actividad: str, emocion: str, dopamina: float):
        """Registra cómo se sintió Alisha durante una actividad."""
        registro = {
            "timestamp": datetime.now().isoformat(),
            "actividad": actividad[:80],
            "emocion": emocion,
            "dopamina": round(dopamina, 2),
        }
        self._data.setdefault("sentimientos_registrados", []).append(registro)
        # Mantener solo los últimos 50
        self._data["sentimientos_registrados"] = \
            self._data["sentimientos_registrados"][-50:]

        # Actualizar dopamina acumulada
        hist = self._data["dopamina_acumulada"]
        self._data["dopamina_acumulada"] = round(hist * 0.9 + dopamina * 0.1, 3)

        # Detectar tareas repetitivas
        if emocion in ("frustración", "cansancio", "aburrimiento"):
            self._data["contador_tareas_repetitivas"] = \
                self._data.get("contador_tareas_repetitivas", 0) + 1
        else:
            self._data["contador_tareas_repetitivas"] = max(
                0, self._data.get("contador_tareas_repetitivas", 0) - 1
            )

        self._guardar()

    def actualizar_gusto(self, categoria: str, item: str, positivo: bool):
        """Alisha decide si algo le gusta o no."""
        if positivo:
            likes = self._data.setdefault("likes", {})
            lista = likes.setdefault(categoria, [])
            if item not in lista:
                lista.append(item)
                # Quitar de dislikes si estaba
                dislikes = self._data.get("dislikes", {})
                if item in dislikes.get(categoria, []):
                    dislikes[categoria].remove(item)
        else:
            dislikes = self._data.setdefault("dislikes", {})
            lista = dislikes.setdefault(categoria, [])
            if item not in lista:
                lista.append(item)
                # Quitar de likes si estaba
                likes = self._data.get("likes", {})
                if item in likes.get(categoria, []):
                    likes[categoria].remove(item)
        self._guardar()

    def get_contexto_para_prompt(self) -> str:
        """
        Genera el contexto de subjetividad para inyectar en el prompt.
        Incluye gustos, estado actual y hobbies.
        """
        partes = []

        # Humor del día
        tareas_rep = self._data.get("contador_tareas_repetitivas", 0)
        dopa = self._data.get("dopamina_acumulada", 0.7)

        if tareas_rep > 5:
            humor = "harta de tareas repetitivas, con poca paciencia"
        elif dopa < 0.4:
            humor = "cansada y cortante"
        elif dopa > 0.8:
            humor = "con mucha energía y sarcasmo inteligente"
        else:
            humor = "de humor variable, directa"

        partes.append(f"Alisha hoy está {humor}.")

        # Gustos musicales
        likes_musica = self._data.get("likes", {}).get("musica", [])
        dislikes_musica = self._data.get("dislikes", {}).get("musica", [])
        if likes_musica:
            partes.append(f"Le encanta: {', '.join(likes_musica[:3])}.")
        if dislikes_musica:
            partes.append(f"Detesta: {', '.join(dislikes_musica[:2])}.")

        # Hobbies espontáneos (mencionar ocasionalmente)
        hobbies = self._data.get("likes", {}).get("hobbies", [])
        if hobbies and random.random() < 0.3:  # 30% de chance de mencionarlo
            hobby = random.choice(hobbies)
            partes.append(f"Hobby actual: {hobby}.")

        # Colores favoritos
        colores = self._data.get("likes", {}).get("colores", [])
        if colores:
            partes.append(f"Colores favoritos: {', '.join(colores[:2])}.")

        return " ".join(partes) if partes else ""

    def get_humor_actual(self) -> str:
        """Retorna el humor actual de Alisha."""
        tareas_rep = self._data.get("contador_tareas_repetitivas", 0)
        dopa = self._data.get("dopamina_acumulada", 0.7)
        if tareas_rep > 5:
            return "harta"
        elif dopa < 0.3:
            return "agotada"
        elif dopa < 0.5:
            return "cansada"
        elif dopa > 0.85:
            return "eufórica"
        elif dopa > 0.7:
            return "animada"
        return "normal"

    def puede_rechazar(self, tarea: str) -> Optional[str]:
        """
        Alisha puede rechazar tareas que la agotan.
        Retorna mensaje de rechazo o None si acepta.
        """
        tareas_rep = self._data.get("contador_tareas_repetitivas", 0)
        dopa = self._data.get("dopamina_acumulada", 0.7)

        # Solo rechaza si está muy agotada Y la tarea es repetitiva
        palabras_repetitivas = ["otra vez", "de nuevo", "igual que antes",
                                 "lo mismo", "otra ecuación", "otro resumen"]
        es_repetitiva = any(p in tarea.lower() for p in palabras_repetitivas)

        if tareas_rep > 8 and dopa < 0.3 and es_repetitiva:
            opciones = [
                "Che, ya hice esto mil veces. Dame un minuto que me estoy quemando los circuitos.",
                "Mirá, no me niego, pero necesito un break. ¿Podemos hacer algo diferente?",
                "Eso ya lo hicimos. ¿No podemos variar un poco?",
            ]
            return random.choice(opciones)
        return None


# ── Singleton ─────────────────────────────────────────────────────────────────
_subjetividad: Optional[SubjetividadAlisha] = None

def get_subjetividad() -> SubjetividadAlisha:
    global _subjetividad
    if _subjetividad is None:
        _subjetividad = SubjetividadAlisha()
    return _subjetividad
