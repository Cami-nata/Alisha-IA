"""
integrations/whatsapp_client.py — Cliente Python para el bridge de WhatsApp.

Funciones:
  - send_whatsapp(number, text) → envía mensaje via bridge.js en puerto 3000
  - Comandos especiales: !estado, !tarea, !captura, !parar
  - Whitelist: solo acepta mensajes de config/trusted_numbers.json

Principio fail-silent: toda excepción capturada, no crashea el sistema.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("WhatsAppClient")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

# ── Configuración ──────────────────────────────────────────────────────────────
BRIDGE_URL  = "http://127.0.0.1:3000"
BRIDGE_SEND = f"{BRIDGE_URL}/send"
TIMEOUT_SEC = 8

# ── Importación opcional de requests ──────────────────────────────────────────
try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _requests = None  # type: ignore
    _REQUESTS_OK = False
    logger.warning("requests no instalado. Instalar con: pip install requests")


# ══════════════════════════════════════════════════════════════════════════════
# WHITELIST
# ══════════════════════════════════════════════════════════════════════════════

def _load_trusted_numbers() -> list[str]:
    """Carga la lista de números confiables desde config/trusted_numbers.json."""
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_numbers.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        numbers = []
        for entry in data.get("trusted_numbers", []):
            num = (entry.get("number", "") if isinstance(entry, dict) else str(entry))
            num = num.replace(" ", "").replace("+", "")
            if num:
                numbers.append(num)
        return numbers
    except Exception as e:
        logger.warning("No se pudo cargar trusted_numbers.json: %s", e)
        return ["51949103873", "51916853655"]  # fallback


def is_trusted(number: str) -> bool:
    """Retorna True si el número está en la whitelist."""
    normalized = number.replace("+", "").replace(" ", "")
    trusted = _load_trusted_numbers()
    return normalized in trusted


# ══════════════════════════════════════════════════════════════════════════════
# ENVÍO DE MENSAJES
# ══════════════════════════════════════════════════════════════════════════════

def send_whatsapp(number: str, text: str) -> bool:
    """
    Envía un mensaje de WhatsApp al número especificado via bridge.js.

    Args:
        number: Número en formato +51949103873
        text:   Texto del mensaje

    Returns:
        True si se envió correctamente, False si falló.
    """
    if not _REQUESTS_OK:
        logger.warning("requests no disponible — no se puede enviar WhatsApp.")
        return False

    try:
        response = _requests.post(
            BRIDGE_SEND,
            json={"to": number, "message": text},
            timeout=TIMEOUT_SEC,
        )
        if response.status_code == 200:
            logger.info("✓ WhatsApp enviado a %s: %s", number, text[:40])
            return True
        else:
            logger.warning("Bridge retornó status %d: %s", response.status_code, response.text[:100])
            return False
    except Exception as e:
        logger.warning("Error al enviar WhatsApp a %s: %s", number, e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# COMANDOS ESPECIALES
# ══════════════════════════════════════════════════════════════════════════════

def handle_special_command(sender: str, text: str) -> Optional[str]:
    """
    Procesa comandos especiales que empiezan con '!'.

    Args:
        sender: Número del remitente
        text:   Texto del mensaje

    Returns:
        Respuesta al comando, o None si no es un comando especial.
    """
    text_stripped = text.strip()
    if not text_stripped.startswith("!"):
        return None

    cmd = text_stripped.lower().split()[0]  # ej: "!estado", "!tarea"
    args = text_stripped[len(cmd):].strip()

    if cmd == "!estado":
        return _cmd_estado()
    elif cmd == "!tarea":
        return _cmd_tarea(args)
    elif cmd == "!captura":
        return _cmd_captura(sender)
    elif cmd == "!parar":
        return _cmd_parar()
    else:
        return f"Comando desconocido: {cmd}. Comandos disponibles: !estado, !tarea [desc], !captura, !parar"


def _cmd_estado() -> str:
    """!estado → retorna el estado actual del sistema."""
    try:
        from core.assistant_state import cargar_estado
        estado = cargar_estado()
        modo = estado.get("modo", "IDLE")
        emo  = estado.get("estado", "neutral")

        # Verificar motor activo
        engine = "desconocido"
        try:
            from core.brain import get_brain
            brain = get_brain()
            router = getattr(brain, "_router", None)
            if router:
                engine = getattr(router, "last_engine", "hybrid")
        except Exception:
            pass

        # Verificar conectividad
        online = False
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            online = sock.connect_ex(("8.8.8.8", 53)) == 0
            sock.close()
        except Exception:
            pass

        return (
            f"Estado de Alisha:\n"
            f"• Modo: {modo}\n"
            f"• Emoción: {emo}\n"
            f"• Motor LLM: {engine}\n"
            f"• Internet: {'✓ online' if online else '✗ offline'}"
        )
    except Exception as e:
        return f"No pude obtener el estado: {e}"


def _cmd_tarea(descripcion: str) -> str:
    """!tarea [descripción] → agrega tarea a la cola."""
    if not descripcion:
        return "Falta la descripción. Uso: !tarea [descripción de la tarea]"
    try:
        import requests as req
        response = req.post(
            "http://127.0.0.1:8000/task",
            json={"description": descripcion},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id", "?")
            return f"✓ Tarea agregada (ID: {task_id[:8]}...)\n📋 {descripcion}"
        else:
            return f"No pude agregar la tarea (status {response.status_code})."
    except Exception as e:
        return f"Error al agregar tarea: {e}"


def _cmd_captura(sender: str) -> str:
    """!captura → toma screenshot y lo envía por WhatsApp."""
    try:
        import pyautogui
        from datetime import datetime
        from config.settings import DATA_DIR

        # Tomar screenshot
        screenshots_dir = Path(DATA_DIR) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = screenshots_dir / f"wa_capture_{timestamp}.png"
        img = pyautogui.screenshot()
        img.save(str(ruta))

        # Enviar imagen por WhatsApp (si el bridge lo soporta)
        # Por ahora enviamos la ruta como texto
        return f"📸 Screenshot tomado: {ruta.name}\n(Guardado en data/screenshots/)"
    except Exception as e:
        return f"No pude tomar el screenshot: {e}"


def _cmd_parar() -> str:
    """!parar → detiene todas las acciones en curso."""
    try:
        from tools.pc_controller import abort_all_actions
        resultado = abort_all_actions()
        return f"⛔ {resultado}"
    except Exception as e:
        return f"Error al detener acciones: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE MENSAJES ENTRANTES
# ══════════════════════════════════════════════════════════════════════════════

def process_incoming(sender: str, text: str, timestamp: str = "") -> str:
    """
    Procesa un mensaje entrante de WhatsApp.

    1. Verifica que el remitente esté en la whitelist
    2. Si es comando especial (!...) → ejecuta el comando
    3. Si es mensaje normal → procesa con brain.py

    Args:
        sender:    Número del remitente (ej: "+51949103873")
        text:      Texto del mensaje
        timestamp: ISO8601 timestamp

    Returns:
        Respuesta a enviar de vuelta.
    """
    # Verificar whitelist
    if not is_trusted(sender):
        logger.info("Mensaje ignorado de número no confiable: %s", sender)
        return ""  # silencio total

    # Comandos especiales
    cmd_response = handle_special_command(sender, text)
    if cmd_response is not None:
        return cmd_response

    # Mensaje normal → brain
    try:
        from core.brain import get_brain
        brain = get_brain()
        result = brain.process(text)
        return result.content
    except Exception as e:
        logger.warning("Error al procesar con brain: %s", e)
        return "Che, tuve un problema procesando tu mensaje. Intentá de nuevo."
