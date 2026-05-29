# Arquitectura de Alisha IA

## Visión general

Alisha es una IA de escritorio tipo JARVIS con arquitectura modular y canales múltiples.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CANALES EXTERNOS                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Web    │  │ Telegram │  │ WhatsApp │  │  Desktop │       │
│  │  (Flask) │  │  (Bot)   │  │ (futuro) │  │   App    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
              ┌───────▼────────┐
              │ ChannelRouter  │  ← Normaliza mensajes
              └───────┬────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│  CORE (Brain)  │◄────────┤  MEMORY         │
│  - agent_loop  │         │  - memory_db    │
│  - brain       │         │  - atlas_memory │
│  - emotion     │         └─────────────────┘
└───────┬────────┘
        │
        ├──────────┬──────────┬──────────┬──────────┐
        │          │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐
   │ AVATAR │ │ VISION │ │ VOICE  │ │ TOOLS  │ │SERVICES│
   │ Live2D │ │ Screen │ │  TTS   │ │Actions │ │ Health │
   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

## Estructura de carpetas

```
alisha-ia/
├── main.py                    # Punto de entrada único
├── Alisha_IA.py              # Shim de compatibilidad
├── config.py                 # Shim de compatibilidad
│
├── channels/                 # 🆕 Canales externos
│   ├── base.py              # Interfaz base
│   ├── channel_router.py    # Router central
│   ├── telegram_channel.py  # Telegram Bot API
│   └── whatsapp_channel.py  # Stub futuro
│
├── core/                     # Cerebro y lógica central
│   ├── brain.py             # Motor de IA principal
│   ├── agent_loop.py        # Loop autónomo
│   ├── emotion_engine.py    # Emociones
│   └── assistant_state.py   # Estado compartido
│
├── avatar/                   # Sistema Live2D
│   ├── cabina_virtual.py    # Renderizado del modelo
│   ├── alisha_bridge.py     # Sincronización
│   ├── tts_engine.py        # Síntesis de voz
│   └── audio_visual_sync.py # Lip-sync
│
├── memory/                   # Persistencia
│   ├── memory_db.py         # SQLite con WAL
│   ├── atlas_memory.py      # Memoria semántica
│   └── mongodb_client.py    # MongoDB (opcional)
│
├── personality/              # Identidad y comportamiento
│   ├── alisha_identity.py   # Identidad base
│   ├── alisha_curiosidad.py # Motor de curiosidad
│   └── emotion_evolution.py # Evolución emocional
│
├── vision/                   # Visión de pantalla
│   ├── vision_engine.py     # OCR y análisis
│   ├── screen_context.py    # Contexto visual
│   └── gemini_vision.py     # Visión con Gemini
│
├── tools/                    # Herramientas de acción
│   ├── actions.py           # Acciones básicas
│   ├── pc_controller.py     # Control del PC
│   └── natural_mouse.py     # Movimiento humano
│
├── services/                 # Servicios auxiliares
│   ├── alisha_health.py     # Monitoreo de recursos
│   ├── alisha_sleep.py      # Sistema de sueño
│   └── proactive_notifier.py # Notificaciones
│
├── web/                      # Interfaz web actual
│   ├── web_app.py           # Flask + SocketIO
│   ├── api_server.py        # API REST
│   └── routes/              # Endpoints
│
├── desktop/                  # 🆕 App de escritorio (futuro)
│   ├── README.md            # Diseño y roadmap
│   └── package.json         # Configuración
│
├── data/                     # Datos de runtime
│   ├── ia_memoria.json
│   ├── alisha_memory.db
│   ├── chibi_state.json
│   ├── telegram/            # 🆕 Inbox de Telegram
│   │   ├── audio/
│   │   ├── images/
│   │   └── documents/
│   └── screenshots/
│
├── docs/                     # Documentación
│   ├── ARQUITECTURA.md      # 🆕 Este archivo
│   └── dev-history/         # 🆕 Historial de desarrollo
│       ├── kiro-specs/      # Specs movidos de .kiro
│       └── claude-agents/   # Agents movidos de .claude
│
└── tests/                    # Tests
    └── ...
```

## Principios de diseño

### 1. Fail-silent
Si un módulo falla, Alisha sigue arrancando. Ejemplo:
- Si Telegram no está instalado → canal deshabilitado
- Si MongoDB no está disponible → fallback a SQLite
- Si el avatar falla → el cerebro sigue funcionando

### 2. Sin duplicados
- Un solo punto de entrada: `main.py`
- Shims de compatibilidad mínimos en raíz
- Código real en carpetas organizadas

### 3. Canales desacoplados
- Cada canal (Web, Telegram, WhatsApp) es independiente
- Todos pasan por `ChannelRouter`
- El core no sabe de dónde vino el mensaje

### 4. Avatar independiente
- El avatar corre como proceso separado
- Puede vivir sin la UI
- Comparte estado via `chibi_state.json`

### 5. Seguridad por diseño
- Whitelist de usuarios en Telegram
- Confirmación para acciones sensibles
- Logs sin exponer tokens ni IDs completos

## Flujo de un mensaje

### Ejemplo: Usuario envía mensaje por Telegram

```
1. Usuario → Telegram Bot
   "Hola Alisha, ¿cómo estás?"

2. TelegramChannel.handle_text()
   - Verifica whitelist
   - Crea ChannelMessage normalizado
   - Pasa al ChannelRouter

3. ChannelRouter.route_message()
   - Recibe ChannelMessage
   - Llama al core_handler

4. Core (brain.py)
   - Procesa con el LLM
   - Consulta memoria
   - Genera respuesta + emoción

5. ChannelRouter
   - Recibe ChannelResponse
   - Envía a TelegramChannel

6. TelegramChannel.send_message()
   - Envía texto a Telegram
   - Si hay audio, envía voice note
   - Si hay imagen, envía photo

7. Usuario recibe respuesta
```

## Módulos clave

### ChannelRouter
- **Ubicación:** `channels/channel_router.py`
- **Responsabilidad:** Conectar todos los canales con el core
- **API:**
  - `register_channel(channel)` — registrar canal
  - `set_core_handler(handler)` — configurar handler del core
  - `route_message(message)` — procesar mensaje

### TelegramChannel
- **Ubicación:** `channels/telegram_channel.py`
- **Responsabilidad:** Integración con Telegram Bot API
- **Features:**
  - Texto, voz, audio, imágenes, documentos
  - Comandos: `/start`, `/estado`, `/parar`, `/tarea`, `/captura`, `/ayuda`
  - Whitelist de usuarios
  - Descarga automática de archivos

### Brain
- **Ubicación:** `core/brain.py`
- **Responsabilidad:** Motor de IA principal
- **Features:**
  - Múltiples LLMs con failover
  - Memoria de conversación
  - Generación de emociones
  - Comentarios espontáneos

### Avatar
- **Ubicación:** `avatar/cabina_virtual.py`
- **Responsabilidad:** Renderizado del modelo Live2D
- **Features:**
  - Movimiento motriz natural
  - Lip-sync con TTS
  - Reacción a emociones
  - Overlay transparente

## Próximos pasos

### FASE 1: Limpieza ✅
- [x] Mover `.kiro` y `.claude` a `docs/dev-history`
- [x] Actualizar `.gitignore`
- [x] Crear estructura de `channels/`
- [x] Documentar arquitectura

### FASE 2: Telegram ⏳
- [x] Implementar `TelegramChannel`
- [x] Implementar `ChannelRouter`
- [ ] Conectar con el core
- [ ] Agregar transcripción de audio
- [ ] Agregar análisis de imágenes
- [ ] Tests

### FASE 3: UI JARVIS ⏳
- [ ] Diseñar UI en Figma
- [ ] Implementar orbe principal
- [ ] Implementar panel de módulos
- [ ] Implementar timeline
- [ ] Conectar con WebSocket

### FASE 4: Avatar independiente ⏳
- [ ] Separar proceso del avatar
- [ ] Implementar motion controller
- [ ] Corregir bug de transparencia
- [ ] Modo debug visual

### FASE 5: Desktop App ⏳
- [ ] Elegir framework (Tauri/Electron/pywebview)
- [ ] Implementar launcher
- [ ] Crear instalador Windows
- [ ] Autostart

### FASE 6: Validación ⏳
- [ ] Tests de integración
- [ ] Tests de canales
- [ ] Verificar arranque
- [ ] Documentar cambios

## Convenciones

### Imports
- Usar imports absolutos desde raíz
- Fail-silent para dependencias opcionales
- Ejemplo:
  ```python
  try:
      from telegram import Update
      TELEGRAM_AVAILABLE = True
  except ImportError:
      TELEGRAM_AVAILABLE = False
  ```

### Logging
- Usar `logging` estándar de Python
- Niveles: DEBUG, INFO, WARNING, ERROR
- No exponer tokens ni IDs completos en logs
- Ejemplo:
  ```python
  logger.info(f"Usuario {user_id[:4]}*** conectado")
  ```

### Estado compartido
- Usar `chibi_state.json` para estado del avatar
- Usar `assistant_state.py` para estado del core
- Sincronizar via archivos JSON, no memoria compartida

### Configuración
- Variables de entorno en `.env`
- Defaults sensatos si no están configuradas
- Documentar en `.env.example`

## Referencias

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [Tauri](https://tauri.app/)
