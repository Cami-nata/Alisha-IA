from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"


class SystemMode(str, Enum):
    IDLE = "IDLE"
    WORKING = "WORKING"
    THINKING = "THINKING"
    OVERLOADED = "OVERLOADED"


@dataclass
class AssistantState:
    estado: str = "neutral"
    hablando: bool = False
    texto: str = ""
    modo: SystemMode = SystemMode.IDLE
    ultima_actualizacion: str = ""


def _estado_por_defecto() -> dict[str, Any]:
    estado = asdict(AssistantState())
    estado["modo"] = AssistantState().modo.value
    return estado


def cargar_estado() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _estado_por_defecto()


def guardar_estado(estado: dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def actualizar_estado(
    estado: str | None = None,
    hablando: bool | None = None,
    texto: str | None = None,
    modo: SystemMode | str | None = None,
    ultima_actualizacion: str | None = None,
) -> dict[str, Any]:
    actual = cargar_estado()
    if estado is not None:
        actual["estado"] = estado
    if hablando is not None:
        actual["hablando"] = hablando
    if texto is not None:
        actual["texto"] = texto
    if modo is not None:
        actual["modo"] = SystemMode(str(modo)).value
    if ultima_actualizacion is not None:
        actual["ultima_actualizacion"] = ultima_actualizacion
    guardar_estado(actual)
    return actual


def estado_por_defecto() -> dict[str, Any]:
    return _estado_por_defecto()
