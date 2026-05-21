"""
alisha_print.py — Módulo de Gestión de Impresión — MODO SOLO CONSULTA.

PROTOCOLO DE SEGURIDAD:
  - Alisha NUNCA envía comandos de impresión por su cuenta.
  - Solo busca, prepara y abre la carpeta del archivo.
  - VOS apretás el botón de imprimir en tu programa.
  - imprimir_archivo() está BLOQUEADA — lanza excepción si se llama.

Flujo seguro:
  1. Usuario pide imprimir
  2. Alisha busca el archivo en Descargas
  3. Prepara imagen a A4 si es necesario (solo conversión, sin imprimir)
  4. Abre la carpeta de Descargas con el archivo seleccionado
  5. Muestra botón: "¿Querés que prepare este archivo para que VOS lo imprimas?"
  6. VOS abrís el archivo y apretás Ctrl+P
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from PIL import Image as _PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import win32print
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False

DOWNLOADS_DIR = Path.home() / "Downloads"
EXTENSIONES_IMPRIMIBLES = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}
A4_WIDTH_PX  = 2480
A4_HEIGHT_PX = 3508

# ── BLOQUEO DE IMPRESIÓN AUTÓNOMA ─────────────────────────────────────────────
_PRINT_BLOQUEADO = True  # nunca cambiar a False sin confirmación explícita del usuario


def imprimir_archivo(*args, **kwargs):
    """BLOQUEADO — Alisha no puede imprimir por su cuenta."""
    raise PermissionError(
        "[SEGURIDAD] Alisha no puede enviar comandos de impresión de forma autónoma. "
        "El usuario debe imprimir manualmente."
    )


# ══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA DE ARCHIVOS (solo lectura)
# ══════════════════════════════════════════════════════════════════════════════

def buscar_archivo_reciente(tipo: str = "pdf", carpeta: Path = DOWNLOADS_DIR, n: int = 1) -> list[Path]:
    extensiones = {
        "pdf":        [".pdf"],
        "word":       [".docx", ".doc"],
        "imagen":     [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"],
        "cualquiera": list(EXTENSIONES_IMPRIMIBLES),
    }.get(tipo.lower(), [f".{tipo.lower()}"])

    archivos = []
    for ext in extensiones:
        archivos.extend(carpeta.glob(f"*{ext}"))
        archivos.extend(carpeta.glob(f"*{ext.upper()}"))
    archivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return archivos[:n]


def buscar_por_nombre(nombre: str, carpeta: Path = DOWNLOADS_DIR) -> Optional[Path]:
    nombre_lower = nombre.lower()
    candidatos = [
        f for f in carpeta.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONES_IMPRIMIBLES
        and nombre_lower in f.name.lower()
    ]
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidatos[0]


# ══════════════════════════════════════════════════════════════════════════════
# IMPRESORAS (solo lectura)
# ══════════════════════════════════════════════════════════════════════════════

def get_impresora_default() -> str:
    if _WIN32_OK:
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["wmic", "printer", "where", "Default=TRUE", "get", "Name"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
        if lines:
            return lines[0]
    except Exception:
        pass
    return "EPSON ET-16600 Series"


def listar_impresoras() -> list[str]:
    if _WIN32_OK:
        try:
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [p[2] for p in printers]
        except Exception:
            pass
    try:
        result = subprocess.run(["wmic", "printer", "get", "Name"],
                                capture_output=True, text=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        return [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PREPARACIÓN DE IMAGEN A4 (sin imprimir — solo convierte)
# ══════════════════════════════════════════════════════════════════════════════

def preparar_imagen_a4(ruta: Path) -> Path:
    """
    Convierte imagen a PDF A4. NO imprime — solo prepara el archivo.
    Retorna la ruta del PDF preparado (en Descargas).
    """
    if not _PIL_OK:
        return ruta
    try:
        img = _PILImage.open(ruta)
        if img.mode in ("RGBA", "P", "LA"):
            bg = _PILImage.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        ratio = min(A4_WIDTH_PX / img.width, A4_HEIGHT_PX / img.height)
        new_w, new_h = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((new_w, new_h), _PILImage.LANCZOS)

        canvas = _PILImage.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), (255, 255, 255))
        canvas.paste(img, ((A4_WIDTH_PX - new_w) // 2, (A4_HEIGHT_PX - new_h) // 2))

        out = DOWNLOADS_DIR / f"_listo_para_imprimir_{ruta.stem}.pdf"
        canvas.save(str(out), "PDF", resolution=300)
        print(f"[Print] Imagen preparada como A4: {out.name}")
        return out
    except Exception as e:
        print(f"[Print] Error preparando imagen: {e}")
        return ruta


def abrir_carpeta_con_archivo(ruta: Path) -> None:
    """Abre el Explorador de Windows con el archivo seleccionado."""
    try:
        subprocess.Popen(["explorer", "/select,", str(ruta)],
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"[Print] Error abriendo carpeta: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SANDBOX — simulación antes de cualquier acción
# ══════════════════════════════════════════════════════════════════════════════

def simular_accion(nombre: str, fn, *args, **kwargs) -> tuple[bool, str]:
    """
    Ejecuta fn en modo simulación (dry-run).
    Loguea el resultado. Si falla, retorna (False, error) sin afectar el sistema.
    """
    print(f"[Sandbox] Simulando: {nombre}...")
    try:
        # Para funciones de búsqueda/lectura, ejecutar real (no tienen efecto)
        # Para funciones de escritura/impresión, solo loguear
        if "imprimir" in nombre.lower() or "print" in nombre.lower():
            print(f"[Sandbox] BLOQUEADO en simulación: {nombre} — no se ejecuta")
            return True, "Simulación OK (acción bloqueada por seguridad)"
        result = fn(*args, **kwargs)
        print(f"[Sandbox] OK: {nombre} → {result}")
        return True, str(result)
    except Exception as e:
        print(f"[Sandbox] FALLO en simulación: {nombre} → {e}")
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# PRINT MANAGER — Solo Consulta
# ══════════════════════════════════════════════════════════════════════════════

class PrintManager:
    """
    Gestor de impresión en MODO SOLO CONSULTA.
    
    Alisha:
      ✅ Busca archivos
      ✅ Prepara imágenes a A4
      ✅ Abre la carpeta con el archivo listo
      ✅ Muestra botón de preparación en el chat
      ❌ NUNCA envía comandos de impresión
    """

    def __init__(self):
        self._pendiente: Optional[dict] = None
        self._lock = threading.Lock()

    def solicitar_preparacion(self, tipo: str = "pdf", nombre: str = None) -> dict:
        """
        Busca el archivo, lo prepara si es imagen, y abre la carpeta.
        NO imprime. Retorna info para mostrar el botón en el chat.
        """
        # Sandbox: verificar que la búsqueda funciona antes de proceder
        ok, msg = simular_accion("buscar_archivo", buscar_archivo_reciente, tipo)
        if not ok:
            return {"encontrado": False, "mensaje": f"Error en verificación: {msg}"}

        # Buscar archivo real
        if nombre:
            ruta = buscar_por_nombre(nombre)
        else:
            archivos = buscar_archivo_reciente(tipo)
            ruta = archivos[0] if archivos else None

        if not ruta:
            return {"encontrado": False, "mensaje": f"No encontré ningún {tipo} reciente en Descargas."}

        # Preparar imagen si es necesario
        ext = ruta.suffix.lower()
        archivo_preparado = ruta
        preparado = False
        if ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"):
            archivo_preparado = preparar_imagen_a4(ruta)
            preparado = (archivo_preparado != ruta)

        tamanio_kb = archivo_preparado.stat().st_size // 1024
        impresora  = get_impresora_default()

        with self._lock:
            self._pendiente = {"ruta": archivo_preparado, "original": ruta}

        return {
            "encontrado":   True,
            "archivo":      archivo_preparado.name,
            "ruta":         str(archivo_preparado),
            "impresora":    impresora,
            "tamanio_kb":   tamanio_kb,
            "preparado_a4": preparado,
            "mensaje": (
                f"Encontré '{ruta.name}'"
                + (f" y lo convertí a A4" if preparado else "")
                + f" ({tamanio_kb} KB). "
                f"¿Querés que abra la carpeta para que VOS lo imprimas?"
            ),
        }

    def abrir_para_usuario(self) -> dict:
        """
        Abre el Explorador con el archivo listo. El usuario imprime manualmente.
        Esta es la única acción 'activa' permitida.
        """
        with self._lock:
            pendiente = self._pendiente
            self._pendiente = None

        if not pendiente:
            return {"ok": False, "mensaje": "No hay ningún archivo preparado."}

        ruta = pendiente["ruta"]
        abrir_carpeta_con_archivo(ruta)

        return {
            "ok": True,
            "mensaje": (
                f"Abrí la carpeta con '{ruta.name}' seleccionado. "
                f"Abrilo y apretá Ctrl+P para imprimir."
            ),
        }

    def cancelar(self) -> dict:
        with self._lock:
            self._pendiente = None
        return {"ok": True, "mensaje": "Cancelado. Avisame cuando quieras."}

    def listar_recientes(self, tipo: str = "cualquiera", n: int = 8) -> list[dict]:
        archivos = buscar_archivo_reciente(tipo, n=n)
        result = []
        for f in archivos:
            result.append({
                "nombre":     f.name,
                "ruta":       str(f),
                "tipo":       f.suffix.lower().lstrip("."),
                "tamanio_kb": f.stat().st_size // 1024,
                "fecha":      time.strftime("%d/%m %H:%M", time.localtime(f.stat().st_mtime)),
            })
        return result

    # Alias para compatibilidad con código anterior — redirige al flujo seguro
    def solicitar_impresion(self, tipo="pdf", nombre=None, **kwargs) -> dict:
        resultado = self.solicitar_preparacion(tipo=tipo, nombre=nombre)
        # Cambiar el mensaje de confirmación al estilo seguro
        if resultado.get("encontrado"):
            resultado["mensaje_confirmacion"] = resultado["mensaje"]
        return resultado

    def confirmar_impresion(self) -> dict:
        """Redirige a abrir_para_usuario — nunca imprime directamente."""
        return self.abrir_para_usuario()


_print_manager: Optional[PrintManager] = None

def get_print_manager() -> PrintManager:
    global _print_manager
    if _print_manager is None:
        _print_manager = PrintManager()
    return _print_manager
