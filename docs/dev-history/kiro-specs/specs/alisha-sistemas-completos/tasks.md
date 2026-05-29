# Implementation Tasks — Alisha IA: Sistemas Completos

## Task List

- [x] 1. Configuración base y archivos de configuración
  - [x] 1.1 Crear `config/trusted_numbers.json` con los números de Ana
  - [x] 1.2 Agregar `PREFER_CLOUD`, `MAX_RAM_MB`, `OFFLINE_MODE` a `config/settings.py`
  - [x] 1.3 Verificar que `config/env_loader.py` carga todas las keys necesarias
  - Requirements: 4.8, 4.10, 5.6

- [x] 2. API REST Interna (Bloque 6)
  - [x] 2.1 Crear `web/api_server.py` con FastAPI en localhost:8000
  - [x] 2.2 Implementar `GET /status` con estado del sistema
  - [x] 2.3 Implementar `POST /message` que procesa con brain.py
  - [x] 2.4 Implementar `POST /whatsapp/incoming` para recibir del bridge
  - [x] 2.5 Implementar `GET /history` con últimos 30 turnos
  - [x] 2.6 Implementar `POST /task` para crear tareas
  - [x] 2.7 Agregar middleware localhost-only
  - Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.9, 6.10, 6.11

- [x] 3. Sistema de Seguridad (Bloque 4)
  - [x] 3.1 Crear `core/security_manager.py` con lista de acciones peligrosas
  - [x] 3.2 Implementar flujo de confirmación con timeout de 30 segundos
  - [x] 3.3 Implementar whitelist de operaciones seguras
  - [x] 3.4 Integrar con brain.py para interceptar acciones antes de ejecutar
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9

- [x] 4. Optimización RAM y Modo Cloud (Bloque 5)
  - [x] 4.1 Actualizar SmartRouter en `core/brain.py` con orden Gemini→Groq→Mistral→Ollama
  - [x] 4.2 Implementar carga lazy de Ollama (solo sin internet)
  - [x] 4.3 Implementar descarga de Ollama cuando vuelve internet
  - [x] 4.4 Respetar `PREFER_CLOUD`, `MAX_RAM_MB`, `OFFLINE_MODE` de settings
  - Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 5.8, 5.9

- [x] 5. Hotkey Manager (Bloque 2 - parte 1)
  - [x] 5.1 Crear `core/hotkey_manager.py` con registro de hotkeys globales
  - [x] 5.2 Implementar INSERT → toggle micrófono
  - [x] 5.3 Implementar CTRL+SHIFT+A → mostrar/ocultar ventana
  - [x] 5.4 Implementar ESC → cancelar tarea en curso
  - [x] 5.5 Implementar CTRL+SHIFT+S → screenshot → brain
  - [x] 5.6 Manejo de conflictos de hotkeys (log + continuar)
  - Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.11

- [x] 6. Gemini Live Client (Bloque 2 - parte 2)
  - [x] 6.1 Crear `services/gemini_live_client.py` con captura de audio via sounddevice
  - [x] 6.2 Implementar streaming a Gemini Live API
  - [x] 6.3 Implementar estados idle/listening/processing conectados a assistant_state
  - [x] 6.4 Implementar fallback automático a Vosk offline
  - Requirements: 2.1, 2.2, 2.9, 2.10

- [x] 7. WhatsApp Bridge Node.js (Bloque 1 - parte 1)
  - [x] 7.1 Crear `integrations/whatsapp_bridge/package.json`
  - [x] 7.2 Crear `integrations/whatsapp_bridge/bridge.js` con whatsapp-web.js
  - [x] 7.3 Implementar sesión persistente con LocalAuth
  - [x] 7.4 Implementar filtro de whitelist en bridge.js
  - [x] 7.5 Implementar POST a api_server al recibir mensajes
  - [x] 7.6 Implementar endpoint POST /send para enviar mensajes
  - [x] 7.7 Implementar reintentos si api_server no responde
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.12

- [x] 8. WhatsApp Client Python (Bloque 1 - parte 2)
  - [x] 8.1 Implementar `integrations/whatsapp_client.py` completo
  - [x] 8.2 Implementar `send_whatsapp(number, text)` que llama a bridge.js
  - [x] 8.3 Implementar comandos especiales: !estado, !tarea, !captura, !parar
  - [x] 8.4 Integrar con api_server.py en endpoint /whatsapp/incoming
  - Requirements: 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11

- [x] 9. Browser Controller (Bloque 3 - parte 1)
  - [x] 9.1 Crear `tools/browser_controller.py` con Playwright
  - [x] 9.2 Implementar `search_google(query)` → retorna 5 resultados
  - [x] 9.3 Implementar `read_gmail()` → últimos 10 emails
  - [x] 9.4 Implementar `send_email(to, subject, body)` via Gmail
  - [x] 9.5 Implementar `search_drive(query)` → archivos recientes
  - [x] 9.6 Implementar `get_calendar_events()` → eventos de hoy
  - [x] 9.7 Implementar `search_youtube(query)` y `play_youtube(url)`
  - [x] 9.8 Implementar `get_youtube_transcript(url)`
  - [x] 9.9 Implementar control de Spotify Web Player
  - Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.15, 3.16, 3.17, 3.18

- [x] 10. Office Controller (Bloque 3 - parte 2)
  - [x] 10.1 Crear `tools/office_controller.py`
  - [x] 10.2 Implementar lectura y creación de documentos Word con python-docx
  - [x] 10.3 Implementar lectura de archivos Excel con openpyxl
  - [x] 10.4 Implementar lectura de presentaciones PowerPoint con python-pptx
  - [x] 10.5 Manejo de errores descriptivos sin excepciones no capturadas
  - Requirements: 3.6, 3.7, 3.8, 3.9, 3.19

- [x] 11. PC Controller mejoras (Bloque 3 - parte 3)
  - [x] 11.1 Agregar control de volumen (subir/bajar/silenciar) a `tools/pc_controller.py`
  - [x] 11.2 Agregar control de brillo a `tools/pc_controller.py`
  - [x] 11.3 Agregar listar/terminar procesos a `tools/pc_controller.py`
  - [x] 11.4 Agregar comprimir/descomprimir ZIP a `tools/pc_controller.py`
  - Requirements: 3.10, 3.11, 3.12, 3.13, 3.14

- [x] 12. Sistema de Testing (Bloque 7)
  - [x] 12.1 Crear `tests/test_alisha.py` con los 7 tests requeridos
  - [x] 12.2 Implementar `test_1_brain_responde` (respuesta < 3s)
  - [x] 12.3 Implementar `test_2_memoria_persiste` (guardar y recuperar nombre)
  - [x] 12.4 Implementar `test_3_herramienta_pc` (abrir notepad)
  - [x] 12.5 Implementar `test_4_navegador` (buscar en Google)
  - [x] 12.6 Implementar `test_5_whatsapp_bridge` (verificar bridge corriendo)
  - [x] 12.7 Implementar `test_6_hotkey` (verificar INSERT registrado)
  - [x] 12.8 Implementar `test_7_seguridad` (confirmar antes de eliminar)
  - [x] 12.9 Crear `tests/run_all_tests.py` con reporte visual ✓/✗
  - Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11
