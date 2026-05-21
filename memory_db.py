"""
memory_db.py — Persistencia SQLite con fallback a JSON.

Base de datos SQLite para memoria episódica de Alisha.
Principio fail-silent: toda excepción se captura y registra, nunca se propaga.

Compatible con agent_memory.py existente (no lo modifica).
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import DATA_DIR


# ---------------------------------------------------------------------------
# Esquema SQL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS conversaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT    NOT NULL,
    entrada          TEXT    NOT NULL,
    respuesta        TEXT    NOT NULL,
    estado_emocional TEXT    DEFAULT 'neutral',
    session_id       INTEGER DEFAULT -1
);

CREATE TABLE IF NOT EXISTS conversaciones_archivo (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT    NOT NULL,
    entrada          TEXT    NOT NULL,
    respuesta        TEXT    NOT NULL,
    estado_emocional TEXT    DEFAULT 'neutral',
    archivado_en     TEXT    NOT NULL,
    session_id       INTEGER DEFAULT -1
);

CREATE TABLE IF NOT EXISTS preferencias (
    clave     TEXT PRIMARY KEY,
    valor     TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio              TEXT    NOT NULL,
    fin                 TEXT,
    actividad_principal TEXT    DEFAULT '',
    resumen             TEXT    DEFAULT '',
    titulo              TEXT    DEFAULT 'Nueva conversación',
    mensajes_count      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS habilidades_entrenadas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre           TEXT    NOT NULL,
    descripcion      TEXT    DEFAULT '',
    pasos_json       TEXT    NOT NULL,
    script_python    TEXT    DEFAULT '',
    veces_ejecutada  INTEGER DEFAULT 0,
    creada           TEXT    NOT NULL,
    ultima_ejecucion TEXT
);

CREATE INDEX IF NOT EXISTS idx_conv_timestamp  ON conversaciones(timestamp);
CREATE INDEX IF NOT EXISTS idx_conv_entrada    ON conversaciones(entrada);
CREATE INDEX IF NOT EXISTS idx_conv_session    ON conversaciones(session_id);
CREATE INDEX IF NOT EXISTS idx_habilidades_nombre ON habilidades_entrenadas(nombre);
"""

_ARCHIVE_THRESHOLD = 10_000


class MemoryDB:
    """
    Base de datos SQLite para memoria episódica de Alisha.

    Fallback automático a JSON si SQLite no está disponible.
    """

    def __init__(self, db_path: str = None) -> None:
        if db_path is None:
            db_path = str(DATA_DIR / "alisha_memory.db")
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._fallback_data: list[dict] = []
        self._using_fallback = False

        try:
            self._conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=5.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.executescript(_DDL)
            self._conn.commit()
            # Migración: agregar columnas nuevas si no existen (base de datos vieja)
            self._migrar()
        except Exception as e:
            print(f"[MemoryDB] SQLite no disponible ({e}), usando fallback JSON")
            self._using_fallback = True
            self._conn = None
            self._fallback_to_json()

    # ------------------------------------------------------------------
    # Migración de esquema (base de datos existente)
    # ------------------------------------------------------------------

    def _migrar(self) -> None:
        """Agrega columnas nuevas a tablas existentes sin perder datos."""
        if self._conn is None:
            return
        migraciones = [
            "ALTER TABLE conversaciones ADD COLUMN session_id INTEGER DEFAULT -1",
            "ALTER TABLE conversaciones_archivo ADD COLUMN session_id INTEGER DEFAULT -1",
            "ALTER TABLE sesiones ADD COLUMN titulo TEXT DEFAULT 'Nueva conversación'",
            "ALTER TABLE sesiones ADD COLUMN mensajes_count INTEGER DEFAULT 0",
        ]
        for sql in migraciones:
            try:
                self._conn.execute(sql)
            except Exception:
                pass  # columna ya existe — ignorar
        try:
            self._conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Fallback JSON
    # ------------------------------------------------------------------

    def _fallback_to_json(self) -> None:
        """Carga ia_recuerdos.json y memory.json si SQLite falla."""
        self._fallback_data = []

        for filename in ("ia_recuerdos.json", "memory.json"):
            path = DATA_DIR / filename
            if not path.exists():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                # ia_recuerdos.json tiene clave "recuerdos"
                if isinstance(raw, dict) and "recuerdos" in raw:
                    for r in raw["recuerdos"]:
                        self._fallback_data.append({
                            "timestamp": r.get("fecha", ""),
                            "entrada": r.get("entrada", ""),
                            "respuesta": r.get("respuesta", ""),
                            "estado_emocional": r.get("emocion", "neutral"),
                        })
                # memory.json puede tener estructura diferente
                elif isinstance(raw, list):
                    for r in raw:
                        self._fallback_data.append({
                            "timestamp": r.get("timestamp", r.get("fecha", "")),
                            "entrada": r.get("entrada", ""),
                            "respuesta": r.get("respuesta", ""),
                            "estado_emocional": r.get("estado_emocional",
                                                       r.get("emocion", "neutral")),
                        })
            except Exception as e:
                print(f"[MemoryDB] Error cargando {filename}: {e}")

    # ------------------------------------------------------------------
    # CRUD — Conversaciones
    # ------------------------------------------------------------------

    def save_conversation(
        self,
        entrada: str,
        respuesta: str,
        estado_emocional: str,
        session_id: int = -1,
    ) -> None:
        """Persiste un turno de conversación. Fail-silent."""
        ts = datetime.now().isoformat()
        if self._using_fallback or self._conn is None:
            self._fallback_data.append({
                "timestamp": ts,
                "entrada": entrada,
                "respuesta": respuesta,
                "estado_emocional": estado_emocional,
                "session_id": session_id,
            })
            return

        try:
            self._conn.execute(
                "INSERT INTO conversaciones "
                "(timestamp, entrada, respuesta, estado_emocional, session_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, entrada, respuesta, estado_emocional, session_id),
            )
            self._conn.commit()
            # Actualizar contador de mensajes de la sesión
            if session_id:
                self._conn.execute(
                    "UPDATE sesiones SET mensajes_count = mensajes_count + 1 WHERE id = ?",
                    (session_id,)
                )
                self._conn.commit()
            self._archive_old_records()
        except Exception as e:
            print(f"[MemoryDB] Error en save_conversation: {e}")

    def save_to_mongo(self, entrada: str, respuesta: str, estado_emocional: str, session_id: int) -> None:
        """Persiste en MongoDB Atlas con fallback silencioso a SQLite."""
        try:
            from mongodb_client import get_db
            db = get_db()
            if db is not None:
                from datetime import datetime
                col = db["conversaciones"]
                col.insert_one({
                    "session_id":       session_id,
                    "timestamp":        datetime.now().isoformat(),
                    "entrada":          entrada[:10000],
                    "respuesta":        respuesta[:10000],
                    "estado_emocional": estado_emocional,
                })
        except Exception as e:
            print(f"[MemoryDB] MongoDB no disponible, usando SQLite: {e}")

    def load_recent(self, n: int = 20) -> list[dict]:
        """Carga las últimas n conversaciones. Fallback a JSON si SQLite falla."""
        if self._using_fallback or self._conn is None:
            return self._fallback_data[-n:]

        try:
            cursor = self._conn.execute(
                "SELECT timestamp, entrada, respuesta, estado_emocional, session_id "
                "FROM conversaciones ORDER BY id DESC LIMIT ?",
                (n,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]
        except Exception as e:
            print(f"[MemoryDB] Error en load_recent: {e}")
            return self._fallback_data[-n:]

    def load_by_session(self, session_id: int, n: int = 200) -> list[dict]:
        """Carga conversaciones de una sesión específica ordenadas por timestamp ascendente."""
        if self._using_fallback or self._conn is None:
            return [
                {**r, "session_id": r.get("session_id", -1)}
                for r in self._fallback_data
                if r.get("session_id") == session_id
            ][-n:]
        try:
            cursor = self._conn.execute(
                "SELECT timestamp, entrada, respuesta, estado_emocional, session_id "
                "FROM conversaciones WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                (session_id, n),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"[MemoryDB] Error en load_by_session: {e}")
            return []

    def update_session_title(self, session_id: int, titulo: str) -> None:
        """Actualiza el título de una sesión."""
        if self._using_fallback or self._conn is None or session_id < 0:
            return
        try:
            self._conn.execute(
                "UPDATE sesiones SET titulo = ? WHERE id = ?",
                (titulo[:80], session_id)
            )
            self._conn.commit()
        except Exception as e:
            print(f"[MemoryDB] Error en update_session_title: {e}")

    def buscar_contexto(self, query: str) -> list[dict]:
        """
        Busca conversaciones relevantes usando LIKE en entrada y respuesta.
        Retorna máximo 5 resultados.
        """
        if self._using_fallback or self._conn is None:
            pattern = query.lower()
            results = [
                r for r in self._fallback_data
                if pattern in r.get("entrada", "").lower()
                or pattern in r.get("respuesta", "").lower()
            ]
            return results[:5]

        try:
            like = f"%{query}%"
            cursor = self._conn.execute(
                "SELECT timestamp, entrada, respuesta, estado_emocional "
                "FROM conversaciones "
                "WHERE entrada LIKE ? OR respuesta LIKE ? "
                "ORDER BY id DESC LIMIT 5",
                (like, like),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"[MemoryDB] Error en buscar_contexto: {e}")
            return []

    # ------------------------------------------------------------------
    # CRUD — Preferencias
    # ------------------------------------------------------------------

    def save_preference(self, clave: str, valor: str) -> None:
        """Guarda o actualiza una preferencia. Fail-silent."""
        if self._using_fallback or self._conn is None:
            return

        ts = datetime.now().isoformat()
        try:
            self._conn.execute(
                "INSERT INTO preferencias (clave, valor, timestamp) VALUES (?, ?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, timestamp=excluded.timestamp",
                (clave, valor, ts),
            )
            self._conn.commit()
        except Exception as e:
            print(f"[MemoryDB] Error en save_preference: {e}")

    def get_preference(self, clave: str) -> Optional[str]:
        """Retorna el valor de una preferencia o None si no existe."""
        if self._using_fallback or self._conn is None:
            return None

        try:
            cursor = self._conn.execute(
                "SELECT valor FROM preferencias WHERE clave = ?",
                (clave,),
            )
            row = cursor.fetchone()
            return row["valor"] if row else None
        except Exception as e:
            print(f"[MemoryDB] Error en get_preference: {e}")
            return None

    # ------------------------------------------------------------------
    # Gestión de sesiones
    # ------------------------------------------------------------------

    def start_session(self) -> int:
        """Inicia una nueva sesión y retorna el session_id."""
        if self._using_fallback or self._conn is None:
            return -1

        ts = datetime.now().isoformat()
        try:
            cursor = self._conn.execute(
                "INSERT INTO sesiones (inicio) VALUES (?)",
                (ts,),
            )
            self._conn.commit()
            return cursor.lastrowid or -1
        except Exception as e:
            print(f"[MemoryDB] Error en start_session: {e}")
            return -1

    def end_session(self, session_id: int, resumen: str) -> None:
        """Cierra una sesión con su resumen. Fail-silent."""
        if self._using_fallback or self._conn is None or session_id < 0:
            return

        ts = datetime.now().isoformat()
        try:
            self._conn.execute(
                "UPDATE sesiones SET fin = ?, resumen = ? WHERE id = ?",
                (ts, resumen, session_id),
            )
            self._conn.commit()
        except Exception as e:
            print(f"[MemoryDB] Error en end_session: {e}")

    # ------------------------------------------------------------------
    # Archivado automático
    # ------------------------------------------------------------------

    def _archive_old_records(self) -> None:
        """
        Mueve registros antiguos a conversaciones_archivo cuando
        conversaciones supera 10.000 filas.
        """
        if self._using_fallback or self._conn is None:
            return

        try:
            cursor = self._conn.execute("SELECT COUNT(*) FROM conversaciones")
            count = cursor.fetchone()[0]

            if count <= _ARCHIVE_THRESHOLD:
                return

            # Calcular cuántos archivar (todos menos los últimos 10.000)
            to_archive = count - _ARCHIVE_THRESHOLD
            archivado_en = datetime.now().isoformat()

            self._conn.execute(
                """
                INSERT INTO conversaciones_archivo
                    (timestamp, entrada, respuesta, estado_emocional, archivado_en)
                SELECT timestamp, entrada, respuesta, estado_emocional, ?
                FROM conversaciones
                ORDER BY id ASC
                LIMIT ?
                """,
                (archivado_en, to_archive),
            )

            self._conn.execute(
                """
                DELETE FROM conversaciones
                WHERE id IN (
                    SELECT id FROM conversaciones ORDER BY id ASC LIMIT ?
                )
                """,
                (to_archive,),
            )

            self._conn.commit()
        except Exception as e:
            print(f"[MemoryDB] Error en _archive_old_records: {e}")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Cierra la conexión SQLite si está abierta."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Habilidades entrenadas
    # ------------------------------------------------------------------

    def guardar_habilidad(self, nombre: str, descripcion: str,
                          pasos: list, script: str = "") -> int:
        """Guarda o actualiza una habilidad entrenada. Retorna el ID."""
        if self._using_fallback or self._conn is None:
            return -1
        ts = datetime.now().isoformat()
        pasos_json = json.dumps(pasos, ensure_ascii=False)
        try:
            # Verificar si ya existe
            cur = self._conn.execute(
                "SELECT id FROM habilidades_entrenadas WHERE nombre = ?", (nombre,)
            )
            row = cur.fetchone()
            if row:
                self._conn.execute(
                    "UPDATE habilidades_entrenadas SET descripcion=?, pasos_json=?, "
                    "script_python=? WHERE id=?",
                    (descripcion, pasos_json, script, row["id"])
                )
                self._conn.commit()
                return row["id"]
            else:
                cur2 = self._conn.execute(
                    "INSERT INTO habilidades_entrenadas "
                    "(nombre, descripcion, pasos_json, script_python, creada) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (nombre, descripcion, pasos_json, script, ts)
                )
                self._conn.commit()
                return cur2.lastrowid or -1
        except Exception as e:
            print(f"[MemoryDB] Error en guardar_habilidad: {e}")
            return -1

    def listar_habilidades(self) -> list[dict]:
        """Lista todas las habilidades entrenadas."""
        if self._using_fallback or self._conn is None:
            return []
        try:
            cur = self._conn.execute(
                "SELECT id, nombre, descripcion, veces_ejecutada, creada "
                "FROM habilidades_entrenadas ORDER BY id DESC"
            )
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"[MemoryDB] Error en listar_habilidades: {e}")
            return []

    def obtener_habilidad(self, nombre: str) -> Optional[dict]:
        """Obtiene una habilidad por nombre."""
        if self._using_fallback or self._conn is None:
            return None
        try:
            cur = self._conn.execute(
                "SELECT * FROM habilidades_entrenadas WHERE nombre = ?", (nombre,)
            )
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["pasos"] = json.loads(d.get("pasos_json", "[]"))
            return d
        except Exception as e:
            print(f"[MemoryDB] Error en obtener_habilidad: {e}")
            return None

    def registrar_ejecucion_habilidad(self, nombre: str) -> None:
        """Incrementa el contador de ejecuciones de una habilidad."""
        if self._using_fallback or self._conn is None:
            return
        ts = datetime.now().isoformat()
        try:
            self._conn.execute(
                "UPDATE habilidades_entrenadas SET veces_ejecutada = veces_ejecutada + 1, "
                "ultima_ejecucion = ? WHERE nombre = ?",
                (ts, nombre)
            )
            self._conn.commit()
        except Exception as e:
            print(f"[MemoryDB] Error en registrar_ejecucion_habilidad: {e}")

    def __del__(self) -> None:
        self.close()
