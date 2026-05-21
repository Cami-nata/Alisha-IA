"""
mongodb_client.py — Cliente MongoDB con Auto-Healing y soporte Atlas.

Características:
- Conexión a MongoDB Atlas via MONGO_URI del .env
- Keep-Alive con connectTimeoutMS y socketTimeoutMS configurados
- Reintentos automáticos (hasta 3) con backoff exponencial
- Ping de seguridad al despertar
- Reconexión transparente sin cerrar el programa
- Fallback a JSON si Atlas no responde tras reintentos
"""
import threading
import time
from typing import Optional

try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import (
        AutoReconnect,
        ConnectionFailure,
        ServerSelectionTimeoutError,
        NetworkTimeout,
    )
    _PYMONGO_OK = True
except ImportError:
    _PYMONGO_OK = False

from config import MONGO_URI, MONGO_DB

# Número máximo de reintentos ante fallo de conexión
_MAX_REINTENTOS = 3
# Segundos base para backoff exponencial: 1s, 2s, 4s
_BACKOFF_BASE = 1


class MongoDBClient:
    """Singleton para conexión a MongoDB Atlas con Auto-Healing."""

    _instance: Optional["MongoDBClient"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._client = None
                inst._db = None
                inst._available = False
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # Conexión inicial
    # ------------------------------------------------------------------

    def _init_connection(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # Conectar en hilo separado para no bloquear el arranque
        threading.Thread(target=self._conectar, daemon=True).start()

    def _conectar(self) -> bool:
        """Intenta conectar a MongoDB Atlas. Retorna True si tuvo éxito."""
        if not _PYMONGO_OK:
            return False
        try:
            # Keep-Alive: connectTimeoutMS evita esperas largas;
            # socketTimeoutMS=None mantiene sockets abiertos indefinidamente.
            self._client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500,
                socketTimeoutMS=None,
                retryWrites=True,
                retryReads=True,
            )
            self._client.admin.command("ping")
            self._db = self._client[MONGO_DB]
            self._available = True
            self._crear_indices()

            # Detectar si es Atlas o local para el mensaje de bienvenida
            if "mongodb.net" in MONGO_URI:
                print("✨ Che Camila, ya estoy conectada a Atlas. "
                      "Mi memoria ahora está en la nube y es persistente ✨")
            else:
                print(f"[MongoDB] Conectada a {MONGO_URI}")
            return True
        except Exception as e:
            # Silenciar error largo de SSL — solo mostrar resumen
            msg = str(e)
            if "SSL" in msg or "TLSV1" in msg:
                print("[MongoDB] Sin conexión a Atlas (SSL). Usando memoria local.")
            else:
                print(f"[MongoDB] No disponible: {msg[:100]}")
            self._available = False
            return False

    def _crear_indices(self) -> None:
        try:
            self._db["historial"].create_index([("fecha", DESCENDING)])
        except Exception:
            pass
        # Índice compuesto para colección conversaciones (Req 6.6)
        try:
            from pymongo import ASCENDING
            self._db["conversaciones"].create_index(
                [("session_id", ASCENDING), ("timestamp", ASCENDING)],
                name="idx_session_timestamp",
                background=True,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Auto-Healing: ping + reconexión con reintentos
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Ping de seguridad. Reconecta si falla."""
        if not _PYMONGO_OK or self._client is None:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            self._available = False
            return self._reconectar_con_reintentos()

    def _reconectar_con_reintentos(self) -> bool:
        """Intenta reconectar silenciosamente en background."""
        for intento in range(1, _MAX_REINTENTOS + 1):
            time.sleep(_BACKOFF_BASE * (2 ** (intento - 1)))
            try:
                if self._client:
                    try: self._client.close()
                    except Exception: pass
                self._client = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=1500,
                    connectTimeoutMS=1500,
                    socketTimeoutMS=None,
                    retryWrites=True,
                    retryReads=True,
                )
                self._client.admin.command("ping")
                self._db = self._client[MONGO_DB]
                self._available = True
                print(f"[MongoDB] Reconectada ✓")
                return True
            except Exception:
                pass
        self._available = False
        return False

    # ------------------------------------------------------------------
    # Wrapper con reintentos para operaciones de lectura/escritura
    # ------------------------------------------------------------------

    def _ejecutar_con_reintento(self, operacion, *args, **kwargs):
        """
        Envuelve cualquier operación de DB en try/except con reintentos
        ante AutoReconnect o ServerSelectionTimeoutError.
        """
        errores_reintentables = (AutoReconnect, ServerSelectionTimeoutError, NetworkTimeout) if _PYMONGO_OK else ()

        for intento in range(1, _MAX_REINTENTOS + 1):
            try:
                return operacion(*args, **kwargs)
            except errores_reintentables as e:
                print(f"[MongoDB] Error de conexión (intento {intento}): {e}")
                if intento < _MAX_REINTENTOS:
                    espera = _BACKOFF_BASE * (2 ** (intento - 1))
                    time.sleep(espera)
                    self._reconectar_con_reintentos()
                else:
                    self._available = False
                    raise
            except Exception:
                raise

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        # Si la conexión inicial todavía está en progreso, no bloquear
        if not self._initialized:
            return False
        if not self._available or self._client is None:
            return False
        try:
            self._client.admin.command("ping", serverSelectionTimeoutMS=500)
            return True
        except Exception:
            self._available = False
            return False

    def get_collection(self, nombre: str):
        """Retorna la colección pymongo con reintentos automáticos."""
        if not self.is_available():
            raise RuntimeError("MongoDB no está disponible.")
        return _CollectionProxy(self._db[nombre], self)

    def ping_startup(self) -> bool:
        """
        Ping de seguridad al despertar (inicio del loop principal).
        Si falla, refresca el cliente sin cerrar el programa.
        """
        self._init_connection()
        return self.ping()


class _CollectionProxy:
    """
    Proxy transparente sobre una colección pymongo que envuelve
    insert_one, find, find_one, replace_one, delete_one, delete_many,
    count_documents y create_index con reintentos automáticos.
    """

    def __init__(self, collection, client: MongoDBClient):
        self._col = collection
        self._client = client

    def insert_one(self, doc):
        return self._client._ejecutar_con_reintento(self._col.insert_one, doc)

    def find(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.find, *args, **kwargs)

    def find_one(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.find_one, *args, **kwargs)

    def replace_one(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.replace_one, *args, **kwargs)

    def delete_one(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.delete_one, *args, **kwargs)

    def delete_many(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.delete_many, *args, **kwargs)

    def count_documents(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.count_documents, *args, **kwargs)

    def create_index(self, *args, **kwargs):
        return self._client._ejecutar_con_reintento(self._col.create_index, *args, **kwargs)

    def sort(self, *args, **kwargs):
        # sort retorna el cursor, no necesita reintento propio
        return self._col.sort(*args, **kwargs)


def get_db() -> Optional[MongoDBClient]:
    """Retorna instancia si MongoDB está disponible, None si no."""
    client = MongoDBClient()
    # Disparar conexión en background si no se inició aún
    client._init_connection()
    if client.is_available():
        return client
    return None
