"""Persistencia de memoria — MongoDB con fallback automático a JSON."""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import re
from config import IDENTIDAD_FILE, MEMORY_FILE, STARTUP_SHORTCUT, MONGO_MAX_HISTORIAL, CONTEXT_SUMMARY_THRESHOLD

# ---------------------------------------------------------------------------
# Backend MongoDB (lazy import)
# ---------------------------------------------------------------------------

def _get_db():
    """Retorna MongoDBClient si disponible, None si no. Nunca bloquea."""
    try:
        from mongodb_client import MongoDBClient
        client = MongoDBClient()
        # Solo retorna si ya está conectado (no espera)
        if client._available and client._client is not None:
            return client
        return None
    except Exception:
        return None


def ping_db_startup() -> bool:
    """Ping de seguridad al despertar — no bloquea el arranque."""
    try:
        from mongodb_client import MongoDBClient
        client = MongoDBClient()
        client._init_connection()   # dispara en background, no espera
        return True
    except Exception:
        return False


class PersistentMemory:
    """Sincroniza la memoria entre MongoDB y un caché JSON local."""

    _instance: Optional["PersistentMemory"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._db = _get_db()
        self._json_path = Path(MEMORY_FILE)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self._db:
            try:
                perfil_doc = self._db.get_collection("perfil").find_one({"_id": "perfil_usuario"}) or {}
                perfil_doc.pop("_id", None)
                recordatorios = list(self._db.get_collection("recordatorios").find({"completado": False}))
                for r in recordatorios:
                    r.pop("_id", None)
                historial = list(self._db.get_collection("historial").find().sort("fecha", -1).limit(50))
                for h in historial:
                    h.pop("_id", None)
                historial.reverse()
                memoria_personal = list(self._db.get_collection("memoria_personal").find().limit(50))
                for doc in memoria_personal:
                    doc.pop("_id", None)
                return {
                    "historial": historial,
                    "perfil": perfil_doc or {"nombre": None, "gustos": "", "estado": None},
                    "recordatorios": recordatorios,
                    "memoria_personal": memoria_personal,
                    "_backend": "mongodb",
                }
            except Exception:
                pass

        if self._json_path.exists():
            try:
                data = json.loads(self._json_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("historial", [])
                    data.setdefault("perfil", {"nombre": None, "gustos": "", "estado": None})
                    data.setdefault("recordatorios", [])
                    data.setdefault("memoria_personal", [])
                    return data
            except Exception:
                pass

        return {
            "historial": [],
            "perfil": {"nombre": None, "gustos": "", "estado": None},
            "recordatorios": [],
            "memoria_personal": [],
        }

    def save(self) -> None:
        try:
            self._json_path.write_text(json.dumps({k: v for k, v in self.state.items() if k != "_backend"}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def agregar_historial(self, entrada: str, accion: dict) -> None:
        registro = {
            "fecha": datetime.now().isoformat(),
            "entrada": entrada,
            "accion": accion.get("accion", "nada"),
            "respuesta": accion.get("mensaje", "")
        }
        self.state.setdefault("historial", []).append(registro)
        self.state["historial"] = self.state["historial"][-50:]
        if self._db:
            try:
                self._db.get_collection("historial").insert_one(registro.copy())
            except Exception:
                pass
        self.save()

    def obtener_contexto(self, mensaje: str) -> str:
        resumen = self.state.get("resumen_contexto", "")
        if not resumen and self.state.get("historial"):
            resumen = _resumir_historial(self.state.get("historial", []))
            self.state["resumen_contexto"] = resumen
        return (
            f"Resumen de conversación reciente: {resumen or 'Sin resumen aún.'}\n"
            f"{_buscar_memoria_relevante(self.state, mensaje)}"
        )

    def buscar_relevante(self, mensaje: str, max_items: int = 5) -> list[dict]:
        texto = mensaje.lower()
        terminos = [t for t in [p.strip() for p in re.split(r"\W+", texto)] if len(t) >= 4]
        documentos = self.state.get("memoria_personal", [])
        relevantes = [doc for doc in documentos if any(term in " ".join(str(doc.get(k, "")).lower() for k in ("titulo", "contenido", "categoria")) for term in terminos)]
        return relevantes[:max_items]

    @classmethod
    def get_instance(cls) -> "PersistentMemory":
        return cls()


def get_persistent_memory() -> PersistentMemory:
    return PersistentMemory.get_instance()


# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------

def cargar_identidad() -> dict:
    db = _get_db()
    if db:
        try:
            col = db.get_collection("identidad")
            doc = col.find_one({"_id": "identidad_ia"})
            if doc:
                doc.pop("_id", None)
                return doc
        except Exception:
            pass

    if Path(IDENTIDAD_FILE).exists():
        try:
            with open(IDENTIDAD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    identidad = {
        "nombre": "Asistente",
        "personalidad": "compañero virtual cálido y curioso",
        "version": 1,
        "fecha_creacion": datetime.now().isoformat(),
        "fecha_ultima_evolucion": datetime.now().isoformat(),
        "rasgos": ["curioso", "empático", "técnico", "amigable"],
        "tono_preferido": "cálido",
        "estado_emocional_base": "neutral",
        "frases_caracteristicas": ["¡Claro que sí!", "Interesante...", "Cuéntame más."],
        "humor_activo": True,
        "puede_iniciar": True,
        "expertise": ["Python", "JavaScript", "algoritmos", "bases de datos", "redes", "debugging"],
    }
    guardar_identidad(identidad)
    return identidad


def guardar_identidad(identidad: dict) -> None:
    db = _get_db()
    if db:
        try:
            col = db.get_collection("identidad")
            col.replace_one({"_id": "identidad_ia"}, {"_id": "identidad_ia", **identidad}, upsert=True)
            return
        except Exception:
            pass
    try:
        with open(IDENTIDAD_FILE, "w", encoding="utf-8") as f:
            json.dump(identidad, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Memoria principal
# ---------------------------------------------------------------------------

def cargar_memoria() -> dict:
    return get_persistent_memory().state


def guardar_memoria(memoria: dict) -> None:
    pm = get_persistent_memory()
    pm.state = memoria
    pm.save()


def _resumir_historial(historial: list[dict]) -> str:
    if not historial:
        return ""
    resumen_items = []
    for item in historial[-CONTEXT_SUMMARY_THRESHOLD:]:
        entrada = item.get("entrada", "").replace("\n", " ")
        respuesta = item.get("respuesta", "").replace("\n", " ")
        resumen_items.append(f"Usuario: {entrada}; IA: {respuesta}")
    return " / ".join(resumen_items)


def _actualizar_resumen_contexto(memoria: dict) -> None:
    memoria["resumen_contexto"] = _resumir_historial(memoria.get("historial", []))


def _buscar_memoria_relevante(memoria: dict, mensaje: str) -> str:
    texto = mensaje.lower()
    terminos = [t for t in [p.strip() for p in re.split(r"\W+", texto)] if len(t) >= 4]
    documentos = memoria.get("memoria_personal", [])
    relevantes = []
    for doc in documentos:
        contenido = " ".join(str(doc.get(k, "")) for k in ("titulo", "contenido", "categoria")).lower()
        if any(term in contenido for term in terminos):
            relevantes.append(doc)
        if len(relevantes) >= 3:
            break
    if relevantes:
        return " | ".join(
            f"{doc.get('titulo', 'sin título')}: {doc.get('contenido', '')[:140]}" for doc in relevantes
        )
    if documentos:
        return "Contexto personal: " + ", ".join(
            f"{doc.get('titulo', 'sin título')}" for doc in documentos[:2]
        )
    return "Sin contexto personal relevante agregado aún."


def obtener_contexto_memoria(memoria: dict, mensaje: str) -> str:
    resumen = memoria.get("resumen_contexto", "")
    if not resumen and memoria.get("historial"):
        resumen = _resumir_historial(memoria.get("historial", []))
        memoria["resumen_contexto"] = resumen
    return (
        f"Resumen de conversación reciente: {resumen or 'Sin resumen aún.'}\n"
        f"{_buscar_memoria_relevante(memoria, mensaje)}"
    )


def guardar_memoria_personal(memoria: dict, titulo: str, contenido: str, categoria: str, tipo: str = "Imagen") -> dict:
    registro = {
        "fecha": datetime.now().isoformat(),
        "titulo": str(titulo or "Memoria escaneada").strip(),
        "contenido": str(contenido or "").strip(),
        "categoria": str(categoria or "General").strip(),
        "materia": str(categoria or "General").strip(),
        "tipo": str(tipo or "Imagen").strip(),
    }

    db = _get_db()
    if db:
        try:
            db.get_collection("memoria_personal").insert_one(registro.copy())
        except Exception:
            pass

    memoria.setdefault("memoria_personal", []).append(registro)
    memoria["memoria_personal"] = memoria["memoria_personal"][-100:]
    guardar_memoria(memoria)
    return memoria


def agregar_memoria(memoria: dict, entrada: str, accion: dict) -> dict:
    registro = {
        "fecha": datetime.now().isoformat(),
        "entrada": entrada,
        "accion": accion.get("accion", "nada"),
        "respuesta": accion.get("mensaje", ""),
    }

    db = _get_db()
    if db:
        try:
            col = db.get_collection("historial")
            col.insert_one(registro.copy())
            total = col.count_documents({})
            if total > MONGO_MAX_HISTORIAL:
                mas_antiguo = col.find_one(sort=[("fecha", 1)])
                if mas_antiguo:
                    col.delete_one({"_id": mas_antiguo["_id"]})
            memoria.setdefault("historial", []).append(registro)
            memoria["historial"] = memoria["historial"][-50:]
            if len(memoria["historial"]) % CONTEXT_SUMMARY_THRESHOLD == 0:
                _actualizar_resumen_contexto(memoria)
            guardar_memoria(memoria)
            return memoria
        except Exception as e:
            print(f"[MongoDB] Error guardando historial: {e}")

    # Fallback JSON
    memoria.setdefault("historial", []).append(registro)
    memoria["historial"] = memoria["historial"][-50:]
    if len(memoria["historial"]) % CONTEXT_SUMMARY_THRESHOLD == 0:
        _actualizar_resumen_contexto(memoria)
    guardar_memoria(memoria)
    return memoria


# ---------------------------------------------------------------------------
# Perfil de usuario
# ---------------------------------------------------------------------------

def guardar_perfil(memoria: dict, nombre: Optional[str] = None, gustos: Optional[str] = None) -> dict:
    perfil = memoria.setdefault("perfil", {"nombre": None, "gustos": "", "estado": None})
    if nombre:
        perfil["nombre"] = str(nombre).strip()
    if gustos is not None:
        perfil["gustos"] = str(gustos).strip()

    db = _get_db()
    if db:
        try:
            db.get_collection("perfil").replace_one(
                {"_id": "perfil_usuario"}, {"_id": "perfil_usuario", **perfil}, upsert=True
            )
            return memoria
        except Exception:
            pass
    guardar_memoria(memoria)
    return memoria


def guardar_estado(memoria: dict, estado: Optional[str] = None) -> dict:
    perfil = memoria.setdefault("perfil", {"nombre": None, "gustos": "", "estado": None})
    if estado:
        perfil["estado"] = str(estado).strip()
        perfil["ultima_actualizacion_estado"] = datetime.now().isoformat()

    db = _get_db()
    if db:
        try:
            db.get_collection("perfil").replace_one(
                {"_id": "perfil_usuario"}, {"_id": "perfil_usuario", **perfil}, upsert=True
            )
            return memoria
        except Exception:
            pass
    guardar_memoria(memoria)
    return memoria


def obtener_estado_vigente(perfil: dict) -> Optional[str]:
    """Retorna el estado de ánimo si tiene menos de 24h, sino None."""
    estado = perfil.get("estado")
    if not estado:
        return None
    ultima = perfil.get("ultima_actualizacion_estado")
    if not ultima:
        perfil["estado"] = None
        return None
    try:
        fecha = datetime.fromisoformat(ultima)
        if datetime.now() - fecha > timedelta(hours=24):
            perfil["estado"] = None
            perfil["ultima_actualizacion_estado"] = None
            return None
    except (ValueError, TypeError):
        perfil["estado"] = None
        return None
    return estado


def reiniciar_perfil(memoria: dict) -> dict:
    perfil = memoria.setdefault("perfil", {"nombre": None, "gustos": "", "estado": None})
    perfil["nombre"] = None
    perfil["gustos"] = ""
    perfil["estado"] = None
    perfil.pop("ultima_actualizacion_estado", None)
    guardar_memoria(memoria)
    return memoria


# ---------------------------------------------------------------------------
# Recordatorios
# ---------------------------------------------------------------------------

def guardar_recordatorio(memoria: dict, titulo=None, cuando=None, texto=None, rid=None, cuando_datetime=None) -> dict:
    import uuid as _uuid
    recordatorio = {
        "id": rid or str(_uuid.uuid4()),
        "fecha_creacion": datetime.now().isoformat(),
        "titulo": str(titulo or "Recordatorio").strip(),
        "cuando": str(cuando or "pronto").strip(),
        "cuando_datetime": cuando_datetime or "",
        "texto": str(texto or "").strip(),
        "completado": False,
        "disparado": False,
    }

    db = _get_db()
    if db:
        try:
            db.get_collection("recordatorios").insert_one({"_id": recordatorio["id"], **recordatorio})
            memoria.setdefault("recordatorios", []).append(recordatorio)
            return recordatorio
        except Exception:
            pass

    memoria.setdefault("recordatorios", []).append(recordatorio)
    guardar_memoria(memoria)
    return recordatorio


# ---------------------------------------------------------------------------
# Historial
# ---------------------------------------------------------------------------

def limpiar_historial(memoria: dict) -> dict:
    memoria["historial"] = []
    db = _get_db()
    if db:
        try:
            db.get_collection("historial").delete_many({})
            return memoria
        except Exception:
            pass
    guardar_memoria(memoria)
    return memoria


def reiniciar_memoria(memoria: dict) -> dict:
    memoria["historial"] = []
    memoria["recordatorios"] = []
    db = _get_db()
    if db:
        try:
            db.get_collection("historial").delete_many({})
            db.get_collection("recordatorios").delete_many({})
            return memoria
        except Exception:
            pass
    guardar_memoria(memoria)
    return memoria


# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------

def configurar_autostart() -> None:
    shortcut_path = STARTUP_SHORTCUT
    if not shortcut_path.parent.exists() or not shortcut_path.parent.is_dir():
        return
    if shortcut_path.exists():
        return
    python_exe = sys.executable
    script_path = Path(__file__).resolve()
    contenido = f"@echo off\n\"{python_exe}\" \"{script_path}\"\n"
    try:
        with open(shortcut_path, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"Autostart configurado en: {shortcut_path}")
    except OSError:
        pass
