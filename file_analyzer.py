"""Análisis de imágenes y documentos para el asistente IA."""
import base64
import json
import re
from pathlib import Path
from typing import Optional

import requests

from config import OLLAMA_URL

# ---------------------------------------------------------------------------
# Configuración de modelos de visión
# ---------------------------------------------------------------------------

# Extensiones soportadas
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
DOC_EXTS   = {".pdf", ".docx", ".txt", ".md", ".csv"}

# Modelo local (fallback)
VISION_MODEL = "llava-llama3"
TEXT_MODEL   = "llama3.1"

# API Key de Gemini — se lee desde .env o variable de entorno
# Conseguila gratis en: https://aistudio.google.com
GEMINI_API_KEY = ""  # no poner la key acá, usar .env
GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
MAX_IMAGE_SIZE_MB = 10

class GeminiAPIError(Exception):
    """Error específico de Gemini para el análisis multimodal."""


def _get_gemini_key() -> str:
    """Obtiene la API key de Gemini desde .env o variable de entorno."""
    import os
    # Intentar cargar .env si existe
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY).strip()


def analizar_imagen_gemini(path: str, pregunta: str = "") -> str:
    """Analiza una imagen usando Gemini 1.5 Flash — mucho mejor que llava para texto e imágenes."""
    key = _get_gemini_key()
    if not key:
        return "⚠️ No hay API key de Gemini configurada."

    file_size = Path(path).stat().st_size
    if file_size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise GeminiAPIError(
            f"El archivo es muy pesado ({file_size / 1024 / 1024:.1f} MB). "
            f"El límite es de {MAX_IMAGE_SIZE_MB} MB."
        )

    try:
        img_b64 = _encode_image_b64(path)
        ext = Path(path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "gif": "image/gif",
                "webp": "image/webp", "bmp": "image/bmp"}.get(ext, "image/jpeg")

        prompt = pregunta or (
            "Analizá esta imagen en detalle en español rioplatense. "
            "Si contiene texto, transcribilo completo. "
            "Si hay ejercicios, problemas matemáticos o tareas, resolvelós paso a paso. "
            "Si es una foto, describí lo que ves con detalle."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": img_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={key}",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiAPIError("Gemini respondió sin candidatos.")

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        texto = " ".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()

        if not texto:
            raise GeminiAPIError("Gemini devolvió una respuesta vacía.")

        return texto

    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 400:
            raise GeminiAPIError("Error: imagen no válida o formato no soportado.")
        if status == 403:
            raise GeminiAPIError("Error: API key inválida o sin permisos.")
        if status == 429:
            raise GeminiAPIError("Error: límite de cuota alcanzado. Por favor intenta más tarde.")
        raise GeminiAPIError(f"Error HTTP de Gemini: {status or 'desconocido'}.")
    except requests.RequestException:
        raise GeminiAPIError(
            "Lo siento, Camila, mis ojos están algo cansados (error de conexión). "
            "¿Podrías intentar subir la imagen de nuevo?"
        )
    except GeminiAPIError:
        raise
    except Exception as e:
        raise GeminiAPIError(f"Error con Gemini: {e}")


def _encode_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _extract_pdf_text(path: str) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        texto = "\n".join(page.get_text() for page in doc)
        doc.close()
        return texto[:8000]  # limitar para no saturar el prompt
    except Exception as e:
        return f"[Error leyendo PDF: {e}]"


def _extract_docx_text(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:8000]
    except Exception as e:
        return f"[Error leyendo DOCX: {e}]"


def _extract_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:8000]
    except Exception as e:
        return f"[Error leyendo archivo: {e}]"


def _check_model_available(model: str) -> bool:
    """Verifica si un modelo está disponible en Ollama."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        return model in models
    except Exception:
        return False


def analizar_imagen(path: str, pregunta: str = "") -> str:
    """Analiza una imagen. Usa Gemini si hay API key, sino llava local."""
    # Intentar Gemini primero (mucho mejor calidad)
    if _get_gemini_key():
        return analizar_imagen_gemini(path, pregunta)

    # Fallback: llava local
    if not _check_model_available(VISION_MODEL):
        return (
            f"⚠️ No hay API key de Gemini ni modelo local disponible.\n"
            f"Configurá GEMINI_API_KEY en file_analyzer.py o instalá llava:\n"
            f"  ollama pull {VISION_MODEL}"
        )

    img_b64 = _encode_image_b64(path)

    # Intentos con prompts progresivamente más simples
    prompts = [
        f"INSTRUCCIÓN: Responde ÚNICAMENTE en español. NUNCA en inglés ni portugués.\n\nTarea: {pregunta}" if pregunta
        else "INSTRUCCIÓN: Responde ÚNICAMENTE en español. NUNCA en inglés ni portugués.\n\nDescribí detalladamente qué ves en esta imagen. Si hay texto, ejercicios, problemas matemáticos o tareas escolares, transcribílos completos y resolvelós paso a paso en español.",
        "Responde en español solamente. ¿Qué hay en esta imagen? Si tiene texto o ejercicios, explicálos en español.",
        "En español: describí esta imagen.",
    ]

    system_prompt = (
        "Eres un asistente útil. SIEMPRE respondes en español rioplatense. "
        "NUNCA en inglés, portugués u otro idioma. "
        "Si la imagen tiene texto, ejercicios o problemas, los transcribís y resolvés. "
        "Eres directo y útil."
    )

    for prompt in prompts:
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": VISION_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": prompt, "images": [img_b64]},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=120,
            )
            response.raise_for_status()
            resultado = response.json().get("message", {}).get("content", "").strip()

            # Si el modelo se negó, intentar con el siguiente prompt
            frases_negacion = [
                "desculpe", "não consigo", "não posso", "lo siento", "no puedo ayudar",
                "i cannot", "i'm sorry", "i can't", "unable to",
            ]
            if any(f in resultado.lower() for f in frases_negacion):
                continue

            return resultado

        except requests.ConnectionError:
            return "Error: Ollama no está corriendo."
        except Exception as e:
            return f"Error analizando imagen: {e}"

    # Si todos los intentos fallaron con respuestas de negación
    return "No pude analizar esta imagen. Intentá con otra o reformulá la pregunta."


def analizar_documento(path: str, pregunta: str = "") -> str:
    """Extrae texto de un documento y lo analiza con el LLM."""
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        texto = _extract_pdf_text(path)
    elif ext == ".docx":
        texto = _extract_docx_text(path)
    elif ext in {".txt", ".md", ".csv"}:
        texto = _extract_text_file(path)
    else:
        return f"Formato no soportado: {ext}"

    if not texto.strip():
        return "El documento parece estar vacío o no se pudo extraer texto."

    prompt_base = pregunta or "Analizá este documento. Resumí su contenido principal y destacá los puntos más importantes."
    prompt = f"{prompt_base}\n\nContenido del documento:\n{texto}"

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": TEXT_MODEL,
                "messages": [
                    {"role": "system", "content": "Sos un asistente que analiza documentos. Respondé en español, de forma clara y directa."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "Sin respuesta.")
    except Exception as e:
        return f"Error analizando documento: {e}"


def analizar_archivo(path: str, pregunta: str = "") -> str:
    """Detecta el tipo de archivo y lo analiza con el modelo apropiado."""
    ext = Path(path).suffix.lower()
    nombre = Path(path).name

    if ext in IMAGE_EXTS:
        return f"📷 Analizando imagen '{nombre}'...\n\n" + analizar_imagen(path, pregunta)
    elif ext in DOC_EXTS:
        return f"📄 Analizando documento '{nombre}'...\n\n" + analizar_documento(path, pregunta)
    else:
        return f"Formato '{ext}' no soportado. Formatos válidos: {', '.join(IMAGE_EXTS | DOC_EXTS)}"


def es_archivo_soportado(path: str) -> bool:
    return Path(path).suffix.lower() in (IMAGE_EXTS | DOC_EXTS)
