"""
app_discovery.py — Descubrimiento dinámico de aplicaciones para Windows.

Orden de búsqueda:
  1. Caché en memoria
  2. APP_RUTAS de config.py (compatibilidad)
  3. shutil.which() — apps en PATH
  4. Rutas estándar: Program Files, AppData
  5. Registro de Windows (winreg)

La caché se persiste en app_cache.json.
"""

import json
import os
import glob
import shutil
from datetime import datetime
from typing import Optional

from config import APP_RUTAS, DATA_DIR

try:
    import winreg  # type: ignore[import]
    _WINREG_DISPONIBLE = True
except ImportError:
    _WINREG_DISPONIBLE = False

CACHE_FILE = str(DATA_DIR / "app_cache.json")

# Rutas estándar de Windows donde buscar ejecutables
_RUTAS_ESTANDAR = [
    os.environ.get("PROGRAMFILES", r"C:\Program Files"),
    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), ""),
    os.path.join(os.environ.get("APPDATA", ""), ""),
]

# Claves del registro donde suelen registrarse las apps instaladas
_REGISTRO_CLAVES = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
]


class AppDiscovery:
    """Singleton que resuelve nombres de apps a rutas ejecutables."""

    _instance: Optional["AppDiscovery"] = None

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._cargar_cache_json()

    @classmethod
    def get_instance(cls) -> "AppDiscovery":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def resolver_app(self, nombre: str) -> str:
        """Retorna la ruta al ejecutable. Lanza ValueError si no se encuentra."""
        if not nombre or not nombre.strip():
            raise ValueError("El nombre de la aplicación no puede estar vacío.")

        llave = nombre.strip().lower()

        # 1. Caché en memoria
        ruta = self._buscar_en_cache(llave)
        if ruta:
            return ruta

        # 2. APP_RUTAS de config.py (compatibilidad)
        ruta = self._buscar_en_app_rutas(llave)
        if ruta:
            self._guardar_en_cache(llave, ruta, fuente="config")
            return ruta

        # 3. shutil.which() — PATH del sistema
        ruta = self._buscar_en_path(llave)
        if ruta:
            self._guardar_en_cache(llave, ruta, fuente="path")
            return ruta

        # 4. Rutas estándar de Windows
        ruta = self._buscar_en_rutas_estandar(llave)
        if ruta:
            self._guardar_en_cache(llave, ruta, fuente="program_files")
            return ruta

        # 5. Registro de Windows
        ruta = self._buscar_en_registro(llave)
        if ruta:
            self._guardar_en_cache(llave, ruta, fuente="registro")
            return ruta

        raise ValueError(
            f"Aplicación '{nombre}' no encontrada en el sistema. "
            "Verifica que esté instalada o agrega su ruta manualmente."
        )

    def listar_apps_conocidas(self) -> list[str]:
        """Retorna lista de nombres de apps en caché."""
        return sorted(self._cache.keys())

    def agregar_ruta_manual(self, nombre: str, ruta: str) -> None:
        """Agrega o sobreescribe una ruta manualmente."""
        llave = nombre.strip().lower()
        self._guardar_en_cache(llave, ruta, fuente="manual")

    def refrescar_cache(self) -> None:
        """Elimina entradas inválidas y fuerza re-escaneo en próxima llamada."""
        invalidas = [k for k, v in self._cache.items() if not os.path.exists(v)]
        for k in invalidas:
            del self._cache[k]
        self._persistir_cache_json()

    # ------------------------------------------------------------------
    # Búsquedas internas
    # ------------------------------------------------------------------

    def _buscar_en_cache(self, llave: str) -> Optional[str]:
        ruta = self._cache.get(llave)
        if ruta and os.path.exists(ruta):
            return ruta
        if ruta:
            # Entrada inválida — limpiar
            del self._cache[llave]
        return None

    def _buscar_en_app_rutas(self, llave: str) -> Optional[str]:
        ruta = APP_RUTAS.get(llave)
        if ruta and os.path.exists(ruta):
            return ruta
        return None

    def _buscar_en_path(self, llave: str) -> Optional[str]:
        ruta = shutil.which(llave) or shutil.which(llave + ".exe")
        if ruta and os.path.exists(ruta):
            return ruta
        return None

    def _buscar_en_rutas_estandar(self, llave: str) -> Optional[str]:
        patrones = [
            os.path.join(llave, llave + ".exe"),
            os.path.join(llave, "*.exe"),
            os.path.join("*" + llave + "*", llave + ".exe"),
            os.path.join("*" + llave + "*", "*.exe"),
        ]
        for base in _RUTAS_ESTANDAR:
            if not base or not os.path.exists(base):
                continue
            for patron in patrones:
                # Limitar a 1 nivel de profundidad para evitar búsquedas lentas
                resultados = glob.glob(os.path.join(base, patron), recursive=False)
                if resultados:
                    return resultados[0]
        return None

    def _buscar_en_registro(self, llave: str) -> Optional[str]:
        if not _WINREG_DISPONIBLE:
            return None

        nombres_a_probar = [llave, llave + ".exe"]

        for clave_base in _REGISTRO_CLAVES:
            for nombre in nombres_a_probar:
                ruta = self._leer_clave_registro(clave_base, nombre)
                if ruta and os.path.exists(ruta):
                    return ruta
        return None

    def _leer_clave_registro(self, clave_base: str, subkey: str) -> Optional[str]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{clave_base}\\{subkey}") as key:
                valor, _ = winreg.QueryValueEx(key, "")
                return str(valor).strip('"')
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Persistencia de caché
    # ------------------------------------------------------------------

    def _cargar_cache_json(self) -> None:
        if not os.path.exists(CACHE_FILE):
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
            # Solo cargar entradas cuya ruta aún existe
            self._cache = {
                k: v["ruta"]
                for k, v in datos.items()
                if isinstance(v, dict) and os.path.exists(v.get("ruta", ""))
            }
        except Exception:
            self._cache = {}

    def _guardar_en_cache(self, llave: str, ruta: str, fuente: str = "desconocido") -> None:
        self._cache[llave] = ruta
        self._persistir_cache_json()

    def _persistir_cache_json(self) -> None:
        try:
            # Leer datos existentes para preservar metadatos
            datos_existentes: dict = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    datos_existentes = json.load(f)
        except Exception:
            datos_existentes = {}

        # Actualizar con entradas actuales
        for llave, ruta in self._cache.items():
            entrada_existente = datos_existentes.get(llave, {})
            datos_existentes[llave] = {
                "ruta": ruta,
                "fuente": entrada_existente.get("fuente", "desconocido"),
                "verificado": os.path.exists(ruta),
                "ultima_verificacion": datetime.now().isoformat(),
            }

        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(datos_existentes, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # No crashear si no se puede escribir la caché


# ------------------------------------------------------------------
# Función de módulo (interfaz pública simplificada)
# ------------------------------------------------------------------

def resolver_app(nombre: str) -> str:
    """Función de módulo — delega a AppDiscovery singleton."""
    return AppDiscovery.get_instance().resolver_app(nombre)
