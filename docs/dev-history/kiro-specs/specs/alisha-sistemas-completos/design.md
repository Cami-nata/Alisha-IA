# Design Document — Alisha IA: Sistemas Completos

## Overview

Este documento describe la arquitectura técnica para implementar los 7 bloques de funcionalidad nueva en Alisha IA. El proyecto ya tiene una base modular sólida en `core/`, `services/`, `tools/`, `integrations/` y `web/`. Los nuevos módulos se integran en esa estructura sin modificar la identidad emocional ni la personalidad de Alisha.

---

## Architecture

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        ALISHA IA                            │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  core/       │    │  services/   │    │  tools/      │  │
│  │  brain.py    │◄───│  gemini      │    │  pc_ctrl     │  │
│  │  hotkey_mgr  │    │  groq        │    │  browser_ctrl│  │
│  │  security_mgr│    │  mistral     │    │  office_ctrl │  │
│  │  assistant_  │    │  ollama      │    │  safety_guard│  │
│  │  state.py    │    │  gemini_live │    │              │  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘  │
│         │                                                   │
│  ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  web/        │    │ integrations/│    │  config/     │  │
│  │  api_server  │◄───│  whatsapp_   │    │  settings.py │  │
│  │  (FastAPI    │    │  client.py   │    │  trusted_    │  │
│  │   :8000)     │    │              │    │  numbers.json│  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │                               │
└─────────────────────────────┼───────────────────────────────┘
                              │ HTTP
                    ┌─────────▼──────────┐
                    │  integrations/     │
                    │  whatsapp_bridge/  │
                    │  bridge.js (Node)  │
                    │  :3000             │
                    └────────────────────┘
                              │
                         WhatsApp Web
```

---

## Bloque 1: WhatsApp Bidireccional

### bridge.js (Node.js)
- Usa `whatsapp-web.js` con `LocalAuth` para persistir sesión en `session/`
- Expone servidor Express en puerto 3000
- `POST /send` → recibe `{to, message}` y envía por WhatsApp
- Al recibir mensaje: filtra por whitelist, hace POST a `http://localhost:8000/whatsapp/incoming`
- Reintentos automáticos si el API server no responde

### integrations/whatsapp_client.py
- Función `send_whatsapp(number, text)` → POST a bridge.js en puerto 3000
- Comandos especiales: `!estado`, `!tarea`, `!captura`, `!parar`
- Lee whitelist desde `config/trusted_numbers.json`

### config/trusted_numbers.json
```json
{
  "owner": "Ana",
  "trusted_numbers": [
    {"number": "+51949103873", "label": "celular principal", "can_send_commands": true},
    {"number": "+51916853655", "label": "celular secundario", "can_send_commands": true}
  ]
}
```

---

## Bloque 2: Voz Input (Gemini Live API)

### services/gemini_live_client.py
- Captura audio con `sounddevice` (16kHz, mono, chunks de 1024 samples)
- Streaming a Gemini Live API usando `google-genai`
- Estados: `idle` → `listening` → `processing` → `idle`
- Fallback automático a Vosk si Gemini Live falla
- Notifica cambios de estado a `core/assistant_state.py`

### core/hotkey_manager.py
- Usa librería `keyboard` para hotkeys globales
- INSERT: toggle micrófono
- CTRL+SHIFT+A: mostrar/ocultar ventana
- ESC: cancelar tarea (`abort_all_actions()`)
- CTRL+SHIFT+S: screenshot → brain
- Manejo de conflictos: log + continuar sin excepción

---

## Bloque 3: Automatización de Aplicaciones

### tools/browser_controller.py
- Playwright con Chromium (headless=False para Google/Gmail que requieren login)
- Métodos: `search_google`, `read_gmail`, `send_email`, `search_drive`, `get_calendar_events`
- YouTube: `search_video`, `play_video`, `get_transcript`
- Spotify: `play_pause`, `next_track`, `search_song`
- Manejo de errores: try/except en cada método, retorna string descriptivo

### tools/office_controller.py
- `python-docx` para Word: crear, leer, guardar
- `openpyxl` para Excel: abrir, leer celdas, guardar
- `python-pptx` para PowerPoint: abrir, leer diapositivas
- Fallback a `pywinauto` para operaciones que requieren UI

### tools/pc_controller.py (mejoras)
- `volumen_subir/bajar/silenciar` usando `pycaw` o `ctypes`
- `brillo_ajustar` usando WMI
- `listar_procesos` y `terminar_proceso` usando `psutil`
- `comprimir_zip` y `descomprimir_zip` usando `zipfile`

---

## Bloque 4: Sistema de Seguridad

### core/security_manager.py
- Decorador `@requiere_confirmacion` para acciones peligrosas
- Lista de acciones peligrosas en `config/settings.py`
- Timeout de 30 segundos para confirmación
- Palabras de confirmación: "sí", "si", "confirmar", "dale", "ok"
- Palabras de cancelación: "no", "cancelar", "para", "stop"
- Whitelist de operaciones seguras (sin confirmación)

---

## Bloque 5: Optimización RAM

### Cambios en core/brain.py (SmartRouter)
- Orden: Gemini → Groq → Mistral → Ollama
- Ollama se carga lazy: solo cuando no hay internet
- Cuando vuelve internet: `del ollama_client` + `gc.collect()`
- Nuevas variables en `config/settings.py`: `PREFER_CLOUD`, `MAX_RAM_MB`, `OFFLINE_MODE`

---

## Bloque 6: API REST Interna

### web/api_server.py (reemplaza web_app.py)
- FastAPI en `localhost:8000`
- Solo JSON, sin HTML ni templates
- Endpoints: `GET /status`, `POST /message`, `POST /whatsapp/incoming`, `GET /history`, `POST /task`
- Middleware para rechazar conexiones no-localhost
- `web/web_app.py` se mantiene pero no se usa como punto de entrada

---

## Bloque 7: Testing

### tests/test_alisha.py
- 7 tests con pytest
- Mocks para evitar llamadas reales a APIs en CI
- `test_3_herramienta_pc` y `test_4_navegador` marcados como `@pytest.mark.integration`

### tests/run_all_tests.py
- Ejecuta pytest programáticamente
- Reporte visual con ✓/✗ por test
- Exit code 0 si todo pasa, 1 si alguno falla

---

## Data Flow: Mensaje WhatsApp → Respuesta

```
Ana (WhatsApp) 
  → bridge.js recibe mensaje
  → verifica whitelist
  → POST /whatsapp/incoming a api_server.py
  → security_manager verifica si requiere confirmación
  → brain.py procesa con SmartRouter
  → SmartRouter elige Gemini/Groq/Mistral/Ollama
  → respuesta → whatsapp_client.send_whatsapp()
  → POST /send a bridge.js
  → bridge.js envía por WhatsApp
  → Ana recibe respuesta
```

## Data Flow: Voz → Respuesta

```
Ana presiona INSERT
  → hotkey_manager detecta INSERT
  → gemini_live_client activa micrófono
  → assistant_state → WORKING/listening
  → audio streaming → Gemini Live API
  → respuesta texto + audio
  → brain.py registra en memoria
  → TTS reproduce audio
  → assistant_state → IDLE
```

---

## Dependencias

### Python
```
google-genai>=0.8.0
sounddevice>=0.4.6
keyboard>=0.13.5
fastapi>=0.110.0
uvicorn>=0.29.0
playwright>=1.43.0
python-docx>=1.1.0
openpyxl>=3.1.2
python-pptx>=0.6.23
pytest>=8.0.0
requests>=2.31.0
```

### Node.js
```json
{
  "whatsapp-web.js": "^1.23.0",
  "express": "^4.18.2",
  "axios": "^1.6.7",
  "qrcode-terminal": "^0.12.0"
}
```
