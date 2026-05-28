"""
web/api_server.py — API REST interna de Alisha IA.
FastAPI en localhost:8000. Solo JSON, sin frontend web.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

# ── FastAPI ────────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    import uvicorn
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False

# ── Brain (fail-silent) ────────────────────────────────────────────────────────
try:
    from core.brain import get_brain
    _brain = get_brain()
    _BRAIN_OK = True
except Exception:
    _brain = None
    _BRAIN_OK = False

# ── AssistantState (fail-silent) ───────────────────────────────────────────────
try:
    from core.assistant_state import cargar_estado
    _ASSISTANT_STATE_OK = True
except Exception:
    cargar_estado = None  # type: ignore
    _ASSISTANT_STATE_OK = False

# ── Estado en memoria ──────────────────────────────────────────────────────────
# Historial de conversación: máx 30 turnos [{"role": str, "content": str}]
_conversation_history: List[Dict[str, str]] = []

# Cola de tareas: [{"task_id": str, "description": str}]
_task_queue: List[Dict[str, str]] = []

_MAX_HISTORY = 30

# ── App FastAPI ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Alisha IA — API REST Interna",
    description="API interna de Alisha. Solo JSON, sin frontend web.",
    version="1.0.0",
    docs_url=None,   # Sin Swagger UI expuesto
    redoc_url=None,
)


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.7 — Middleware localhost-only
# Rechaza cualquier conexión que no provenga de 127.0.0.1
# ══════════════════════════════════════════════════════════════════════════════

@app.middleware("http")
async def localhost_only(request: Request, call_next):
    """Rechaza conexiones que no sean de localhost (127.0.0.1)."""
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse(
            status_code=403,
            content={"error": "acceso denegado — solo localhost"},
        )
    return await call_next(request)


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.9 — HTTP 404 para endpoints no definidos
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "endpoint no encontrado"},
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.10 — HTTP 422 para body malformado
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    try:
        detail = str(exc.errors()[0].get("msg", str(exc))) if exc.errors() else str(exc)
    except Exception:
        detail = str(exc)
    return JSONResponse(
        status_code=422,
        content={"error": detail},
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.2 — GET /status
# Retorna: {"mode": str, "engine": str, "emotional_state": dict, "online": bool}
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/status")
async def get_status() -> JSONResponse:
    """Estado actual del sistema."""
    try:
        mode = "IDLE"
        emotional_state: Dict[str, Any] = {}
        engine = "none"
        online = False

        # Leer estado desde assistant_state
        if _ASSISTANT_STATE_OK and cargar_estado is not None:
            try:
                estado = cargar_estado()
                mode = estado.get("modo", "IDLE")
                emotional_state = {
                    "estado": estado.get("estado", "neutral"),
                    "hablando": estado.get("hablando", False),
                }
            except Exception:
                pass

        # Leer motor activo y estado emocional desde brain
        if _BRAIN_OK and _brain is not None:
            try:
                emo = _brain.get_emotional_state()
                emotional_state.update({
                    "dopamina": round(emo.dopamina, 2),
                    "humor": round(emo.humor, 2),
                    "tension": round(emo.tension, 2),
                })
                # Detectar motor activo
                router = getattr(_brain, "_router", None)
                if router is not None:
                    engine = getattr(router, "last_engine", "unknown")
                else:
                    engine = "hybrid"
            except Exception:
                pass

        # Verificar conectividad a internet (TCP a 8.8.8.8:53)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("8.8.8.8", 53))
            sock.close()
            online = result == 0
        except Exception:
            online = False

        return JSONResponse(content={
            "mode": mode,
            "engine": engine,
            "emotional_state": emotional_state,
            "online": online,
        })

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.3 — POST /message
# Body: {"text": str}
# Retorna: {"response": str, "engine": str}
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/message")
async def post_message(request: Request) -> JSONResponse:
    """Procesa un mensaje de texto con el brain de Alisha."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"error": "body JSON inválido"},
        )

    text = body.get("text", "").strip() if isinstance(body, dict) else ""
    if not text:
        return JSONResponse(
            status_code=422,
            content={"error": "el campo 'text' es requerido y no puede estar vacío"},
        )

    try:
        response_text = ""
        engine_used = "none"

        if _BRAIN_OK and _brain is not None:
            result = _brain.process(text)
            response_text = result.content
            engine_used = result.engine_used
        else:
            response_text = "Brain no disponible en este momento."
            engine_used = "none"

        # Guardar en historial (máx 30 turnos)
        _conversation_history.append({"role": "user", "content": text})
        _conversation_history.append({"role": "assistant", "content": response_text})
        # Mantener solo los últimos 30 turnos (60 entradas: 30 user + 30 assistant)
        while len(_conversation_history) > _MAX_HISTORY * 2:
            _conversation_history.pop(0)

        return JSONResponse(content={
            "response": response_text,
            "engine": engine_used,
        })

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.4 — POST /whatsapp/incoming
# Body: {"from": str, "text": str, "timestamp": str}
# Retorna: {"ok": bool}
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/whatsapp/incoming")
async def whatsapp_incoming(request: Request) -> JSONResponse:
    """Recibe un mensaje entrante del bridge de WhatsApp y lo procesa."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"error": "body JSON inválido"},
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=422,
            content={"error": "se esperaba un objeto JSON"},
        )

    sender = body.get("from", "").strip()
    text = body.get("text", "").strip()
    timestamp = body.get("timestamp", "").strip()

    if not sender or not text:
        return JSONResponse(
            status_code=422,
            content={"error": "los campos 'from' y 'text' son requeridos"},
        )

    try:
        # Procesar con whatsapp_client (maneja whitelist + comandos + brain)
        response_text = ""
        try:
            from integrations.whatsapp_client import process_incoming, send_whatsapp
            response_text = process_incoming(sender, text, timestamp)
        except Exception:
            # Fallback directo al brain
            if _BRAIN_OK and _brain is not None:
                result = _brain.process(f"[WhatsApp de {sender}]: {text}")
                response_text = result.content
            else:
                response_text = "Sistema no disponible."

        # Guardar en historial
        if response_text:
            _conversation_history.append({"role": "user", "content": f"[{sender}]: {text}"})
            _conversation_history.append({"role": "assistant", "content": response_text})
            while len(_conversation_history) > _MAX_HISTORY * 2:
                _conversation_history.pop(0)

        # Enviar respuesta de vuelta por WhatsApp (fail-silent)
        if response_text:
            try:
                from integrations.whatsapp_client import send_whatsapp
                send_whatsapp(sender, response_text)
            except Exception:
                pass

        return JSONResponse(content={"ok": True})

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.5 — GET /history
# Retorna: lista de últimos 30 turnos [{"role": str, "content": str}]
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/history")
async def get_history() -> JSONResponse:
    """Retorna los últimos 30 turnos del historial de conversación."""
    try:
        # Retornar los últimos 30 turnos (cada turno = 1 entrada, no 1 par)
        history_slice = _conversation_history[-_MAX_HISTORY:]
        return JSONResponse(content=history_slice)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.6 — POST /task
# Body: {"description": str}
# Retorna: {"task_id": str, "ok": bool}
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/task")
async def create_task(request: Request) -> JSONResponse:
    """Crea una nueva tarea en la cola del sistema."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"error": "body JSON inválido"},
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=422,
            content={"error": "se esperaba un objeto JSON"},
        )

    description = body.get("description", "").strip()
    if not description:
        return JSONResponse(
            status_code=422,
            content={"error": "el campo 'description' es requerido y no puede estar vacío"},
        )

    try:
        task_id = str(uuid.uuid4())
        _task_queue.append({
            "task_id": task_id,
            "description": description,
        })
        return JSONResponse(content={
            "task_id": task_id,
            "ok": True,
        })
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"task_id": "", "ok": False, "error": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAREA 2.1 — Punto de entrada: FastAPI en localhost:8000
# ══════════════════════════════════════════════════════════════════════════════

def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Inicia el servidor FastAPI en localhost:8000."""
    if not _FASTAPI_OK:
        print("[APIServer] ✗ FastAPI/uvicorn no disponible. Instalá: pip install fastapi uvicorn")
        return
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    run_server()
