"""
system_diagnostics.py — Diagnóstico y corrección de problemas del sistema.

Alisha puede detectar y ayudar a corregir:
- Uso excesivo de CPU/RAM/disco
- Procesos que consumen demasiados recursos
- Espacio en disco bajo
- Temperatura alta (si está disponible)
- Errores en archivos de Python del proyecto
- Dependencias faltantes
- Problemas de red
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False


# ---------------------------------------------------------------------------
# Diagnóstico de hardware
# ---------------------------------------------------------------------------

def diagnostico_completo() -> dict:
    """Retorna un diagnóstico completo del sistema."""
    resultado = {
        "cpu": _check_cpu(),
        "ram": _check_ram(),
        "disco": _check_disco(),
        "procesos_pesados": _check_procesos_pesados(),
        "red": _check_red(),
        "proyecto": _check_proyecto(),
        "alertas": [],
    }

    # Generar alertas
    if resultado["cpu"].get("porcentaje", 0) > 85:
        resultado["alertas"].append(f"⚠️ CPU al {resultado['cpu']['porcentaje']}% — sistema sobrecargado")
    if resultado["ram"].get("porcentaje", 0) > 85:
        resultado["alertas"].append(f"⚠️ RAM al {resultado['ram']['porcentaje']}% — poca memoria disponible")
    if resultado["disco"].get("porcentaje", 0) > 90:
        resultado["alertas"].append(f"⚠️ Disco al {resultado['disco']['porcentaje']}% — poco espacio")
    if resultado["proyecto"].get("errores"):
        resultado["alertas"].append(f"⚠️ Errores en el proyecto: {len(resultado['proyecto']['errores'])} archivo(s)")

    return resultado


def _check_cpu() -> dict:
    if not _PSUTIL_OK:
        return {"disponible": False}
    try:
        porcentaje = psutil.cpu_percent(interval=1)
        frecuencia = psutil.cpu_freq()
        return {
            "disponible": True,
            "porcentaje": porcentaje,
            "nucleos": psutil.cpu_count(),
            "frecuencia_mhz": round(frecuencia.current) if frecuencia else None,
        }
    except Exception as e:
        return {"disponible": False, "error": str(e)}


def _check_ram() -> dict:
    if not _PSUTIL_OK:
        return {"disponible": False}
    try:
        mem = psutil.virtual_memory()
        return {
            "disponible": True,
            "total_gb": round(mem.total / 1024**3, 1),
            "usado_gb": round(mem.used / 1024**3, 1),
            "libre_gb": round(mem.available / 1024**3, 1),
            "porcentaje": mem.percent,
        }
    except Exception as e:
        return {"disponible": False, "error": str(e)}


def _check_disco() -> dict:
    try:
        uso = shutil.disk_usage("C:\\")
        porcentaje = round(uso.used / uso.total * 100, 1)
        return {
            "disponible": True,
            "total_gb": round(uso.total / 1024**3, 1),
            "usado_gb": round(uso.used / 1024**3, 1),
            "libre_gb": round(uso.free / 1024**3, 1),
            "porcentaje": porcentaje,
        }
    except Exception as e:
        return {"disponible": False, "error": str(e)}


def _check_procesos_pesados(top_n: int = 5) -> list[dict]:
    """Retorna los procesos que más CPU/RAM consumen."""
    if not _PSUTIL_OK:
        return []
    try:
        procesos = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                if info["cpu_percent"] > 5 or info["memory_percent"] > 3:
                    procesos.append({
                        "nombre": info["name"],
                        "pid": info["pid"],
                        "cpu": round(info["cpu_percent"], 1),
                        "ram": round(info["memory_percent"], 1),
                    })
            except Exception:
                pass
        return sorted(procesos, key=lambda x: x["cpu"], reverse=True)[:top_n]
    except Exception:
        return []


def _check_red() -> dict:
    """Verifica conectividad básica."""
    try:
        import socket
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return {"conectado": True}
    except Exception:
        return {"conectado": False, "mensaje": "Sin conexión a internet"}


def _check_proyecto() -> dict:
    """Verifica el estado del proyecto de Alisha."""
    errores = []
    advertencias = []

    # Verificar archivos principales
    archivos_criticos = [
        "ia.py", "ollama.py", "config.py", "memory.py",
        "emotion_engine.py", "tts_engine.py",
    ]
    for archivo in archivos_criticos:
        if not Path(archivo).exists():
            errores.append(f"Falta {archivo}")

    # Verificar dependencias
    deps = ["requests", "pymongo", "pyautogui", "pyttsx3"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            advertencias.append(f"Dependencia no instalada: {dep}")

    # Verificar Ollama
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
        advertencias.append("Ollama no está corriendo")

    return {
        "errores": errores,
        "advertencias": advertencias,
        "ollama_activo": ollama_ok,
    }


# ---------------------------------------------------------------------------
# Correcciones automáticas
# ---------------------------------------------------------------------------

def liberar_memoria() -> str:
    """Intenta liberar memoria cerrando procesos no esenciales."""
    if not _PSUTIL_OK:
        return "psutil no disponible."
    try:
        liberados = []
        procesos_no_esenciales = ["chrome.exe", "msedge.exe", "firefox.exe"]
        for proc in psutil.process_iter(["name", "pid"]):
            if proc.info["name"].lower() in procesos_no_esenciales:
                # No matar — solo reportar
                liberados.append(proc.info["name"])
        if liberados:
            return f"Procesos que podrían cerrarse para liberar RAM: {', '.join(set(liberados))}"
        return "No encontré procesos obvios para cerrar."
    except Exception as e:
        return f"Error: {e}"


def instalar_dependencia(paquete: str) -> str:
    """Instala una dependencia faltante."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", paquete],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return f"✓ {paquete} instalado correctamente."
        return f"Error instalando {paquete}: {result.stderr[:200]}"
    except Exception as e:
        return f"Error: {e}"


def limpiar_cache_python() -> str:
    """Elimina carpetas __pycache__ del proyecto."""
    eliminados = 0
    for cache_dir in Path(".").rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir)
            eliminados += 1
        except Exception:
            pass
    return f"Eliminadas {eliminados} carpetas __pycache__."


# ---------------------------------------------------------------------------
# Resumen legible para Alisha
# ---------------------------------------------------------------------------

def resumen_para_alisha() -> str:
    """Genera un resumen del diagnóstico en lenguaje natural."""
    diag = diagnostico_completo()
    lineas = []

    cpu = diag.get("cpu", {})
    ram = diag.get("ram", {})
    disco = diag.get("disco", {})

    if cpu.get("disponible"):
        lineas.append(f"CPU: {cpu['porcentaje']}% ({cpu['nucleos']} núcleos)")
    if ram.get("disponible"):
        lineas.append(f"RAM: {ram['usado_gb']}GB usados de {ram['total_gb']}GB ({ram['porcentaje']}%)")
    if disco.get("disponible"):
        lineas.append(f"Disco C: {disco['libre_gb']}GB libres de {disco['total_gb']}GB")

    red = diag.get("red", {})
    lineas.append(f"Internet: {'✓ conectada' if red.get('conectado') else '✗ sin conexión'}")

    proyecto = diag.get("proyecto", {})
    lineas.append(f"Ollama: {'✓ activo' if proyecto.get('ollama_activo') else '✗ no corre'}")

    alertas = diag.get("alertas", [])
    if alertas:
        lineas.append("\nAlertas:")
        lineas.extend(alertas)

    procesos = diag.get("procesos_pesados", [])
    if procesos:
        top = procesos[0]
        lineas.append(f"\nProceso más pesado: {top['nombre']} ({top['cpu']}% CPU, {top['ram']}% RAM)")

    return "\n".join(lineas)
