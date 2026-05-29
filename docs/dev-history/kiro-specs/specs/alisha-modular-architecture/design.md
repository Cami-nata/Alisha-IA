# Design Document — Alisha IA: Arquitectura Modular

## Overview

La refactorización transforma ~80 archivos Python en el directorio raíz en una arquitectura modular con 11 paquetes de responsabilidad única. El principio guía es **desacoplamiento por capas**: cada módulo tiene una responsabilidad clara, las dependencias fluyen en una sola dirección, y ningún módulo conoce los detalles internos de otro.

**Principios de diseño:**
- Fail-silent: toda excepción se captura y registra, nunca se propaga al caller
- Comunicación entre capas via parámetros de función o archivos de estado (`chibi_state.json`)
- Un único punto de entrada: `main.py`
- Configuración centralizada: `config/settings.py`
- Sin imports circulares entre módulos

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│              (único punto de entrada)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ inicializa
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────┐
    │  config/ │    │   web/   │    │ integrations/│
    │settings  │    │web_app   │    │ (opcional)   │
    │env_loader│    │routes/   │    └──────────────┘
    │constants │    └────┬─────┘
    └──────────┘         │ importa
          ▲              │
          │    ┌─────────┼──────────┬──────────┐
          │    ▼         ▼          ▼          ▼
          │ ┌──────┐ ┌───────┐ ┌───────┐ ┌────────┐
          │ │core/ │ │memory/│ │tools/ │ │vision/ │
          │ │brain │ │mem_db │ │tools  │ │vision  │
          │ │agent │ │agent_ │ │pc_ctrl│ │screen  │
          │ │emo   │ │memory │ │mouse  │ │context │
          │ │orch  │ │semant │ │safety │ └────────┘
          │ │neural│ └───────┘ └───────┘
          │ │screen│     ▲
          │ └──┬───┘     │ importa
          │    │         │
          │    │  ┌──────────────┐
          │    │  │ personality/ │
          │    │  │ identity     │
          │    │  │ curiosidad   │
          │    │  │ skepticism   │
          │    │  │ mood_engine  │
          │    │  └──────────────┘
          │    │
          │    │  ┌──────────┐
          │    └─►│services/ │
          │       │gemini    │
          │       │groq      │
          │       │openai    │
          │       │ollama    │
          │       │mistral   │
          │       └──────────┘
          │
          │  ┌──────────┐
          │  │ avatar/  │  ← lee chibi_state.json (NO importa core/)
          │  │ cabina   │
          │  │ bridge   │
          │  │ avs      │
          │  │ tts      │
          │  └──────────┘
          │
          └── todos los módulos importan config/
```

**Reglas de dependencia (quién puede importar a quién):**

| Módulo | Puede importar de |
|--------|-------------------|
| `config/` | nadie (hoja del grafo) |
| `services/` | `config/` |
| `memory/` | `config/` |
| `personality/` | `config/` |
| `tools/` | `config/` |
| `vision/` | `config/` |
| `avatar/` | `config/` (lee `chibi_state.json`, NO importa `core/`) |
| `core/` | `config/`, `services/`, `memory/`, `personality/` |
| `web/` | `config/`, `core/`, `memory/`, `tools/`, `vision/`, `avatar/` |
| `integrations/` | solo HTTP a `web/` (no imports directos) |
| `main.py` | todos los módulos |

---

## Components and Interfaces

### config/

**Responsabilidad:** Centralizar toda la configuración del sistema. Ningún módulo lee `os.environ` directamente.

**Archivos:**
- `config/__init__.py` — exporta `settings`, `BASE_DIR`, `DATA_DIR`
- `config/env_loader.py` — carga `.env` con python-dotenv
- `config/settings.py` — todas las variables de configuración
- `config/constants.py` — constantes inmutables (rutas, intervalos, umbrales)

**Interfaz pública:**
```python
from config import BASE_DIR, DATA_DIR
from config.settings import OLLAMA_URL, MODEL, ELEVENLABS_API_KEY, SAFE_MODE
from config.constants import STATE_FILE, CYCLE_INTERVAL_S
from config.env_loader import load_env
```

---

### services/

**Responsabilidad:** Wrappers independientes para cada proveedor LLM. Cada cliente implementa la misma interfaz.

**Archivos:**
- `services/__init__.py` — exporta todos los clientes
- `services/gemini_client.py` — GeminiClient
- `services/groq_client.py` — GroqClient
- `services/openai_client.py` — OpenAIClient
- `services/ollama_client.py` — OllamaClient
- `services/mistral_client.py` — MistralClient

**Interfaz común (todos los clientes):**
```python
class BaseLLMClient:
    def is_available(self) -> bool: ...
    def chat(self, messages: list[dict], **kwargs) -> str: ...
```

**Interfaz pública:**
```python
from services import GeminiClient, GroqClient, OpenAIClient, OllamaClient, MistralClient
```

---

### memory/

**Responsabilidad:** Persistencia de conversaciones, recuerdos y memoria semántica.

**Archivos:**
- `memory/__init__.py` — exporta MemoryDB, AgentMemory, SemanticMemory
- `memory/memory_db.py` — MemoryDB (SQLite)
- `memory/agent_memory.py` — AgentMemory (JSON)
- `memory/alisha_memoria_semantica.py` — SemanticMemory (índice semántico)

**Interfaz pública:**
```python
from memory import MemoryDB, AgentMemory, SemanticMemory
from memory.memory_db import MemoryDB
```

---

### personality/

**Responsabilidad:** Identidad, personalidad y comportamiento de Alisha. NO conoce core/.

**Archivos:**
- `personality/__init__.py` — exporta PersonalitySynthesizer, SkepticismEngine, CuriosityEngine
- `personality/alisha_identity.py` — SemillaPersonalidad, GestosNoVerbales
- `personality/skepticism_engine.py` — SkepticismEngine
- `personality/alisha_curiosidad.py` — CuriosityEngine
- `personality/mood_engine.py` — PersonalitySynthesizer (extraída de brain.py)

**Interfaz pública:**
```python
from personality import PersonalitySynthesizer, SkepticismEngine, CuriosityEngine
```

**Nota:** `PersonalitySynthesizer` recibe `EmotionalState` como parámetro — no importa `EmotionEngine` de `core/`.

---

### core/

**Responsabilidad:** Cerebro central, orquestación, estado del asistente y motor de emociones.

**Archivos:**
- `core/__init__.py` — exporta HybridIntelligenceCore, AgentLoop, EmotionEngine, EventBus
- `core/brain.py` — HybridIntelligenceCore, SmartRouter, UnifiedMemory, ConnectivityChecker
- `core/orchestrator.py` — lógica de orquestación, routing de respuestas, IdleWatcher
- `core/neural_bridge.py` — MicroGestureEngine, SarcasmScoreEngine
- `core/emotion_engine.py` — EmotionEngine (dopamina, cansancio, humor)
- `core/agent_loop.py` — AgentLoop, EventBus
- `core/screen_watcher.py` — ScreenWatcher, StateMapper
- `core/assistant_state.py` — funciones de lectura/escritura de chibi_state.json

**Interfaz pública:**
```python
from core import HybridIntelligenceCore, AgentLoop, EmotionEngine, EventBus
from core.brain import get_brain
from core.agent_loop import AgentLoop
from core.emotion_engine import EmotionEngine
```

---

### avatar/

**Responsabilidad:** Representación visual y audio de Alisha. Lee `chibi_state.json` para recibir instrucciones de `core/` — NO importa `core/` directamente.

**Archivos:**
- `avatar/__init__.py`
- `avatar/cabina_virtual.py` — modelo Live2D (GLFW)
- `avatar/alisha_bridge.py` — bridge de animaciones idle
- `avatar/audio_visual_sync.py` — sincronización audio-visual
- `avatar/tts_engine.py` — motor TTS (ElevenLabs/edge-tts)

**Comunicación con core/:** Solo via `data/chibi_state.json`

---

### vision/

**Responsabilidad:** Percepción visual del entorno. Independiente de core/.

**Archivos:**
- `vision/__init__.py`
- `vision/vision_engine.py` — VisionEngine, detección de rol
- `vision/screen_vision.py` — captura de pantalla
- `vision/context_monitor.py` — monitor de contexto

---

### tools/

**Responsabilidad:** Control del PC (mouse, teclado, apps). Independiente de core/.

**Archivos:**
- `tools/__init__.py`
- `tools/tools.py` — herramientas generales
- `tools/pc_controller.py` — control del PC
- `tools/natural_mouse.py` — movimiento natural del mouse
- `tools/safety_guard.py` — guardia de seguridad

---

### web/

**Responsabilidad:** API REST y WebSocket. Orquesta los módulos para responder requests.

**Archivos:**
- `web/__init__.py`
- `web/web_app.py` — Flask app factory, SocketIO, inicialización (~100 líneas)
- `web/routes/__init__.py`
- `web/routes/chat.py` — /api/chat, /api/audio, WebSocket
- `web/routes/system.py` — /api/status, /api/perfil, /api/sesiones, /api/stop
- `web/routes/files.py` — /api/upload, /api/analyze-doc
- `web/routes/config.py` — /api/config, /api/despertar, /api/lock
- `web/templates/` — plantillas HTML (movidas desde root/templates/)
- `web/static/` — archivos estáticos (movidos desde root/static/)

---

### integrations/

**Responsabilidad:** Integraciones externas opcionales. Se comunican con Alisha via HTTP, no via imports.

**Archivos:**
- `integrations/__init__.py` — get_available_integrations()
- `integrations/discord_bot.py` — DiscordBot (estructura base)
- `integrations/telegram_bot.py` — TelegramBot (estructura base)
- `integrations/whatsapp_bridge.py` — WhatsAppBridge (estructura base)
- `integrations/youtube_client.py` — YouTubeClient (estructura base)

---

## Data Models

### EmotionalState (core/brain.py)
```python
@dataclass
class EmotionalState:
    dopamina:      float = 0.7
    humor:         float = 0.7
    irritabilidad: float = 0.0
    tension:       float = 0.0
    flow:          float = 0.0
    hablando:      bool  = False
    categoria:     str   = "neutro"
```

### AlishaResponse (core/brain.py)
```python
@dataclass
class AlishaResponse:
    content:         str
    engine_used:     str   # "gemini" | "groq" | "openai" | "ollama" | "fallback"
    emotional_state: EmotionalState
    confidence:      float = 1.0
    processing_time: float = 0.0
    sarcasm_score:   float = 0.0
```

### RoutingDecision (core/brain.py)
```python
@dataclass
class RoutingDecision:
    engine:     str    # "gemini" | "groq" | "openai" | "ollama"
    confidence: float
    reason:     str
```

### chibi_state.json (data/)
```json
{
  "estado":          "neutral",
  "hablando":        false,
  "gaze_x":          0.0,
  "gaze_y":          0.0,
  "mouth_amplitude": 0.0,
  "agent_state":     "IDLE",
  "sarcasm_score":   0.0,
  "rol_activo":      "companion",
  "media_actual":    null
}
```

### Interfaz común LLM (services/)
```python
class BaseLLMClient:
    def is_available(self) -> bool:
        """Retorna True si el proveedor está accesible. Nunca lanza excepciones."""
        ...

    def chat(self, messages: list[dict], **kwargs) -> str:
        """
        Envía mensajes al LLM y retorna la respuesta como string.
        messages: lista de {"role": "user"|"assistant"|"system", "content": str}
        Retorna string vacío si falla (fail-silent).
        """
        ...
```

---

## File Split Plan

### brain.py (~2000 líneas) → múltiples archivos

| Clase/Componente | Destino | Líneas aprox. |
|-----------------|---------|---------------|
| `ConnectivityChecker` | `core/brain.py` | 50 |
| `SmartRouter` | `core/brain.py` | 80 |
| `UnifiedMemory` | `core/brain.py` | 80 |
| `HybridIntelligenceCore` | `core/brain.py` | 100 |
| `get_brain()`, `get_idle_watcher()` | `core/brain.py` | 20 |
| `MicroGestureEngine` | `core/neural_bridge.py` | 100 |
| `SarcasmScoreEngine` | `core/neural_bridge.py` | 80 |
| `PersonalitySynthesizer` | `personality/mood_engine.py` | 200 |
| `IdleWatcher` | `core/orchestrator.py` | 60 |
| Lógica de orquestación | `core/orchestrator.py` | 150 |
| `GeminiClient` | `services/gemini_client.py` | 120 |
| `GroqClient` | `services/groq_client.py` | 80 |
| `OpenAIClient` | `services/openai_client.py` | 80 |
| `OllamaClient` | `services/ollama_client.py` | 80 |
| `MistralClient` | `services/mistral_client.py` | 60 |
| `EmotionalState`, `AlishaResponse`, `RoutingDecision` | `core/brain.py` | 30 |

### web_app.py (~2100 líneas) → web/

| Sección | Destino | Líneas aprox. |
|---------|---------|---------------|
| Flask app, SocketIO, `_inicializar()` | `web/web_app.py` | 100 |
| `/api/chat`, `/api/audio`, WebSocket `mensaje` | `web/routes/chat.py` | 250 |
| `/api/status`, `/api/perfil`, `/api/sesiones`, `/api/historial`, `/api/stop`, `/api/agent/status` | `web/routes/system.py` | 200 |
| `/api/upload`, `/api/analyze-doc`, `/api/generar_imagen` | `web/routes/files.py` | 200 |
| `/api/config`, `/api/despertar`, `/api/lock`, `/config` | `web/routes/config.py` | 150 |
| `/api/trust`, `/api/imprimir/*`, `/api/entrenar`, `/api/habilidades` | `web/routes/extras.py` | 200 |
| Helpers: `_detectar_accion_fisica`, `_analizar_intencion_y_proponer`, `_map_brain_emotion` | `web/helpers.py` | 150 |

### agent_loop.py (~1900 líneas) → core/

| Clase/Componente | Destino | Líneas aprox. |
|-----------------|---------|---------------|
| `EventBus` | `core/agent_loop.py` | 60 |
| `AgentLoop` | `core/agent_loop.py` | 250 |
| `ScreenWatcher` | `core/screen_watcher.py` | 150 |
| `StateMapper` | `core/screen_watcher.py` | 100 |
| Helpers `_read_state`, `_write_state`, `_update_state` | `core/assistant_state.py` | 50 |
| Constantes y categorías de apps | `config/constants.py` | 40 |

---

## Migration Strategy

### Fase 1 — Estructura de directorios (sin mover código)
Crear todos los directorios con `__init__.py` vacíos. El sistema sigue funcionando con los archivos en el root.

```
core/__init__.py
memory/__init__.py
personality/__init__.py
avatar/__init__.py
vision/__init__.py
tools/__init__.py
services/__init__.py
integrations/__init__.py
web/__init__.py
web/routes/__init__.py
config/__init__.py
```

### Fase 2 — Configuración centralizada
Crear `config/settings.py`, `config/env_loader.py`, `config/constants.py` con el contenido de `config.py` actual. Mantener `config.py` en el root como shim de compatibilidad:

```python
# config.py (shim de compatibilidad — NO eliminar hasta que todos los imports estén actualizados)
from config.settings import *
from config.constants import *
```

### Fase 3 — Mover archivos simples (sin dependencias circulares)
Mover en este orden (de menos a más dependencias):
1. `emotion_engine.py` → `core/emotion_engine.py`
2. `memory_db.py` → `memory/memory_db.py`
3. `agent_memory.py` → `memory/agent_memory.py`
4. `alisha_memoria_semantica.py` → `memory/alisha_memoria_semantica.py`
5. `alisha_identity.py` → `personality/alisha_identity.py`
6. `skepticism_engine.py` → `personality/skepticism_engine.py`
7. `alisha_curiosidad.py` → `personality/alisha_curiosidad.py`
8. `vision_engine.py` → `vision/vision_engine.py`
9. `screen_vision.py` → `vision/screen_vision.py`
10. `context_monitor.py` → `vision/context_monitor.py`
11. `tools.py` → `tools/tools.py`
12. `pc_controller.py` → `tools/pc_controller.py`
13. `natural_mouse.py` → `tools/natural_mouse.py`
14. `safety_guard.py` → `tools/safety_guard.py`
15. `cabina_virtual.py` → `avatar/cabina_virtual.py`
16. `alisha_bridge.py` → `avatar/alisha_bridge.py`
17. `audio_visual_sync.py` → `avatar/audio_visual_sync.py`
18. `tts_engine.py` → `avatar/tts_engine.py`

Para cada archivo movido: actualizar todos los imports en el proyecto.

### Fase 4 — Extraer clientes LLM a services/
Extraer de `brain.py` las clases cliente y crear archivos independientes en `services/`. Actualizar `brain.py` para importar desde `services/`.

### Fase 5 — Dividir archivos grandes
- Dividir `brain.py` según el File Split Plan
- Dividir `web_app.py` en `web/web_app.py` + `web/routes/`
- Dividir `agent_loop.py` en `core/agent_loop.py` + `core/screen_watcher.py`
- Extraer `PersonalitySynthesizer` a `personality/mood_engine.py`

### Fase 6 — Crear main.py
Crear `main.py` en el root con la lógica de `Alisha_IA.py` refactorizada para usar los nuevos módulos. Mantener `Alisha_IA.py` como shim:

```python
# Alisha_IA.py (shim de compatibilidad)
from main import main
if __name__ == "__main__":
    main()
```

### Fase 7 — Integrations y limpieza
- Crear `integrations/` con archivos base
- Actualizar `__init__.py` de cada módulo para exportar las clases correctas
- Verificar que `python main.py` arranca sin errores
- Eliminar shims de compatibilidad cuando todos los imports estén actualizados

---

## Dependency Graph Rules

```
PERMITIDO:
  config/     ← cualquier módulo
  services/   ← core/
  memory/     ← core/, web/
  personality/← core/
  tools/      ← web/
  vision/     ← web/
  avatar/     ← (solo lee data/chibi_state.json, no imports de core/)
  core/       ← web/, main.py
  web/        ← main.py, integrations/ (via HTTP)

PROHIBIDO:
  personality/ → core/
  services/    → core/
  memory/      → core/
  tools/       → core/, memory/, personality/, avatar/
  vision/      → core/, memory/, personality/, avatar/
  avatar/      → core/ (usa chibi_state.json en su lugar)
  web/         → (no puede ser importado por otros módulos)
  integrations/→ core/, memory/, personality/, avatar/ (solo HTTP)
```

---

## Backward Compatibility

### Shims de compatibilidad en el root
Durante la migración, mantener shims en el root para no romper imports existentes:

```python
# emotion_engine.py (shim)
from core.emotion_engine import *

# memory_db.py (shim)
from memory.memory_db import *

# agent_memory.py (shim)
from memory.agent_memory import *
```

Los shims se eliminan en la Fase 7 cuando todos los imports estén actualizados.

### sys.path para tests
El directorio raíz del proyecto debe estar en `sys.path` para que los imports absolutos funcionen:

```python
# tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Archivos del root que NO se mueven
Los siguientes archivos permanecen en el root (no forman parte de ningún módulo):
- `main.py` — punto de entrada
- `Alisha_IA.py` — shim de compatibilidad → `main.py`
- `Alisha_IA.pyw` — versión sin consola
- `alisha.bat`, `Alisha.ps1` — scripts de arranque
- `alisha.ico` — ícono
- `requirements.txt`, `requirements-dev.txt`
- `.env`, `.gitignore`
- `README.md`
- `data/` — directorio de datos en runtime
- `tests/` — suite de tests
- `docs/` — documentación
- `landing/` — landing page
