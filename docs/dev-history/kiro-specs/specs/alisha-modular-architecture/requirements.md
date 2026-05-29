# Requirements Document

## Introduction

Alisha IA es una IA emocional/personaje digital con interfaz Live2D, múltiples LLMs y capacidad de control de PC. El proyecto actualmente tiene ~80 archivos Python en el directorio raíz sin estructura modular, con lógica mezclada entre archivos de más de 2000 líneas.

Este documento define los requisitos para transformar la arquitectura actual en una arquitectura modular limpia que permita: conectar un frontend moderno (React/Electron/Tauri), agregar nuevas capacidades de entrada (voz, visión), integrar servicios externos (Discord, Telegram) como módulos opcionales, implementar auto-programación en sandbox aislado, y escalar a múltiples instancias de Alisha.

La migración debe preservar toda la funcionalidad existente sin modificar la lógica interna de los módulos — solo reorganizar la estructura y corregir imports.

## Glossary

- **Sistema**: El conjunto completo de Alisha IA tras la refactorización modular.
- **Módulo**: Paquete Python con su propio `__init__.py` dentro de la estructura objetivo.
- **core/**: Módulo que contiene el cerebro (HybridIntelligenceCore), orquestador, estado del asistente y motor de emociones.
- **memory/**: Módulo de persistencia: SQLite, JSON y memoria semántica.
- **personality/**: Módulo de identidad, curiosidad, escepticismo y motor de humor.
- **avatar/**: Módulo de representación visual y audio: Live2D, TTS, sincronización audio-visual.
- **vision/**: Módulo de percepción visual: captura de pantalla, análisis de contexto.
- **tools/**: Módulo de herramientas de control del PC: mouse, teclado, seguridad.
- **services/**: Módulo de clientes LLM: uno por proveedor (Gemini, Groq, OpenAI, Ollama, Mistral).
- **integrations/**: Módulo de integraciones externas opcionales: Discord, Telegram, WhatsApp, YouTube.
- **web/**: Módulo del servidor Flask con API REST limpia.
- **config/**: Módulo de configuración centralizada: settings, variables de entorno, constantes.
- **data/**: Directorio de datos en tiempo de ejecución: archivos `.json` y `.db`.
- **main.py**: Único punto de entrada del sistema.
- **Dependencia circular**: Situación donde el módulo A importa de B y B importa de A.
- **SmartRouter**: Componente de `core/` que decide qué cliente LLM usar según el contexto.
- **HybridIntelligenceCore**: Núcleo central de `core/` que coordina todos los componentes.
- **AgentLoop**: Bucle de percepción-decisión-acción que vive en `core/`.
- **EventBus**: Sistema pub/sub en memoria para comunicación entre componentes.
- **EmotionEngine**: Motor de emociones (dopamina, cansancio, humor) que vive en `core/`.
- **PersonalitySynthesizer**: Componente de `personality/` que mantiene la identidad rioplatense de Alisha.
- **Wrapper LLM**: Clase cliente que encapsula la comunicación con un proveedor de LLM específico.
- **API REST**: Interfaz HTTP con endpoints JSON que expone `web/` para el frontend.
- **chibi_state.json**: Archivo de estado compartido en `data/` para comunicación entre `core/` y `avatar/`.

---

## Requirements

### Requisito 1: Estructura de directorios modular

**User Story:** Como desarrollador del proyecto, quiero que todos los archivos Python estén organizados en módulos con responsabilidades claras, para que pueda navegar, mantener y escalar el código sin perderme en 80 archivos en el directorio raíz.

#### Criterios de Aceptación

1. THE Sistema SHALL crear los directorios `core/`, `memory/`, `personality/`, `avatar/`, `vision/`, `tools/`, `services/`, `integrations/`, `web/`, `data/` y `config/` dentro del directorio raíz del proyecto.
2. THE Sistema SHALL crear un archivo `__init__.py` en cada uno de los directorios del criterio anterior.
3. WHEN un archivo Python existente es movido a su módulo destino, THE Sistema SHALL preservar su contenido y lógica interna sin modificaciones funcionales.
4. THE Sistema SHALL mover los archivos según la siguiente asignación:
   - `core/`: `brain.py`, `agent_loop.py`, `emotion_engine.py`, y los nuevos `neural_bridge.py`, `assistant_state.py`, `orchestrator.py`
   - `memory/`: `memory_db.py`, `agent_memory.py`, `alisha_memoria_semantica.py`
   - `personality/`: `alisha_identity.py`, `skepticism_engine.py`, `alisha_curiosidad.py`, y el nuevo `mood_engine.py`
   - `avatar/`: `cabina_virtual.py`, `alisha_bridge.py`, `audio_visual_sync.py`, `tts_engine.py`
   - `vision/`: `vision_engine.py`, `screen_vision.py`, `context_monitor.py`
   - `tools/`: `tools.py`, `pc_controller.py`, `natural_mouse.py`, `safety_guard.py`
   - `web/`: `web_app.py`, directorio `templates/`, directorio `static/`
   - `config/`: `settings.py` (nuevo), `env_loader.py` (nuevo), `constants.py` (nuevo)
5. THE Sistema SHALL crear `main.py` en el directorio raíz como único punto de entrada.
6. IF un archivo listado en el criterio 4 no existe en el proyecto actual, THEN THE Sistema SHALL crear ese archivo con estructura base vacía (docstring + imports mínimos).

---

### Requisito 2: Extracción de clientes LLM a services/

**User Story:** Como desarrollador, quiero que cada cliente LLM sea un módulo independiente en `services/`, para que pueda agregar, reemplazar o deshabilitar un proveedor sin tocar el cerebro central.

#### Criterios de Aceptación

1. THE Sistema SHALL crear un archivo independiente por cada proveedor LLM dentro de `services/`:
   - `services/gemini_client.py`
   - `services/groq_client.py`
   - `services/openai_client.py`
   - `services/ollama_client.py`
   - `services/mistral_client.py`
2. WHEN se extrae un wrapper LLM de `brain.py` a `services/`, THE Sistema SHALL mover la clase cliente completa (incluyendo métodos `is_available()`, `chat()` y manejo de errores) sin modificar su lógica interna.
3. THE `core/brain.py` SHALL importar los clientes LLM desde `services/` en lugar de definirlos localmente.
4. THE `services/` SHALL exponer una interfaz común: cada cliente SHALL implementar los métodos `is_available() -> bool` y `chat(messages: list, **kwargs) -> str`.
5. IF un cliente LLM no puede conectarse a su proveedor, THEN THE cliente SHALL retornar `False` en `is_available()` sin lanzar excepciones no controladas.
6. THE `services/__init__.py` SHALL exportar todos los clientes para que `core/` pueda importarlos con una sola línea.

---

### Requisito 3: Grafo de dependencias sin ciclos

**User Story:** Como desarrollador, quiero que los módulos tengan un grafo de dependencias acíclico y predecible, para que agregar una nueva funcionalidad no rompa módulos no relacionados.

#### Criterios de Aceptación

1. THE `core/` SHALL poder importar de `services/`, `memory/` y `personality/`, pero `services/`, `memory/` y `personality/` SHALL NOT importar de `core/`.
2. THE `personality/` SHALL NOT importar de `core/`. IF `personality/` necesita datos del estado emocional, THEN THE `core/` SHALL pasar esos datos como parámetros en la llamada.
3. THE `tools/` SHALL NOT importar de `core/`, `memory/`, `personality/` ni `avatar/`. THE `tools/` SHALL ser completamente independiente.
4. THE `vision/` SHALL NOT importar de `core/`, `memory/`, `personality/` ni `avatar/`. THE `vision/` SHALL ser completamente independiente.
5. THE `avatar/` SHALL recibir datos de `core/` únicamente como parámetros de función o mediante lectura de `data/chibi_state.json`. THE `avatar/` SHALL NOT importar de `core/` directamente.
6. THE `web/` SHALL importar de `core/`, `memory/`, `tools/` y `vision/` para orquestar las respuestas de la API REST. THE `web/` SHALL NOT ser importado por ningún otro módulo.
7. THE `config/` SHALL ser importable por cualquier módulo sin restricciones. THE `config/` SHALL NOT importar de ningún otro módulo del proyecto.
8. WHEN se ejecuta una herramienta de análisis de imports (como `pydeps` o `importlib`), THE Sistema SHALL producir cero ciclos de dependencia entre los módulos listados.

---

### Requisito 4: Configuración centralizada en config/

**User Story:** Como desarrollador, quiero un único lugar donde estén todas las variables de configuración del sistema, para que cambiar una API key o una ruta no requiera buscar en 10 archivos distintos.

#### Criterios de Aceptación

1. THE `config/settings.py` SHALL centralizar todas las variables de configuración actualmente dispersas en `config.py`, incluyendo: `OLLAMA_URL`, `MODEL`, `ELEVENLABS_API_KEY`, `LIVE2D_MODEL_PATH`, `MONGO_URI`, `SAFE_MODE`, `CONFIRMAR_ACCIONES`, `ACCIONES_PELIGROSAS`, `VALID_ACTIONS`, `APP_RUTAS`, `POWER_COMMANDS`.
2. THE `config/env_loader.py` SHALL encapsular la carga de variables de entorno desde `.env` usando `python-dotenv`, exponiendo una función `load_env() -> None`.
3. THE `config/constants.py` SHALL contener todas las constantes que no cambian en tiempo de ejecución: rutas de archivos de estado, intervalos de ciclo, umbrales de detección.
4. WHEN cualquier módulo necesita una variable de configuración, THE módulo SHALL importarla desde `config/settings` en lugar de leerla directamente con `os.environ.get()`.
5. IF una variable de entorno requerida no está definida, THEN THE `config/settings.py` SHALL usar un valor por defecto seguro y registrar una advertencia en el log.
6. THE `config/settings.py` SHALL exponer `BASE_DIR` y `DATA_DIR` como objetos `pathlib.Path` para que todos los módulos los usen de forma consistente.

---

### Requisito 5: main.py como único punto de entrada

**User Story:** Como operador del sistema, quiero ejecutar `python main.py` para arrancar Alisha completa, para que no haya ambigüedad sobre cómo iniciar el sistema.

#### Criterios de Aceptación

1. THE `main.py` SHALL ser el único archivo ejecutable en el directorio raíz que inicia el sistema completo.
2. THE `main.py` SHALL inicializar los módulos en el siguiente orden: `config/`, `core/`, `memory/`, `personality/`, `avatar/`, `vision/`, `tools/`, `web/`.
3. THE `main.py` SHALL NOT contener lógica de negocio propia. Toda la lógica SHALL residir en los módulos correspondientes.
4. THE `main.py` SHALL iniciar el servidor web Flask con SocketIO, el modelo Live2D en proceso separado, y el ícono en bandeja del sistema.
5. THE `main.py` SHALL implementar el mecanismo de single-instance lock (archivo `.lock` con PID) actualmente en `Alisha_IA.py`.
6. THE `main.py` SHALL implementar el watchdog de auto-restart del servidor web actualmente en `Alisha_IA.py`.
7. WHEN `main.py` recibe los argumentos `--install` o `--remove`, THE Sistema SHALL ejecutar la instalación o remoción del autostart de Windows respectivamente.
8. IF cualquier módulo falla durante la inicialización, THEN THE `main.py` SHALL registrar el error en `crash_log.txt` y continuar iniciando los módulos restantes (principio fail-silent).

---

### Requisito 6: API REST limpia en web/

**User Story:** Como desarrollador frontend, quiero que `web/web_app.py` exponga una API REST con endpoints JSON bien definidos, para que pueda conectar un frontend React/Electron/Tauri sin depender de la implementación interna de Python.

#### Criterios de Aceptación

1. THE `web/web_app.py` SHALL exponer todos los endpoints actuales como endpoints JSON bajo el prefijo `/api/`.
2. THE `web/web_app.py` SHALL separar la inicialización de módulos (actualmente en `_inicializar()`) de la definición de rutas HTTP.
3. WHEN un endpoint recibe una petición, THE `web/web_app.py` SHALL delegar el procesamiento al módulo correspondiente (`core/`, `memory/`, `tools/`, etc.) en lugar de contener lógica de negocio propia.
4. THE `web/web_app.py` SHALL exponer los siguientes grupos de endpoints:
   - `/api/chat` (POST): procesamiento de mensajes de texto
   - `/api/audio` (POST): transcripción y procesamiento de audio
   - `/api/perfil` (GET/POST): datos del perfil del usuario
   - `/api/historial` (GET): historial de conversaciones
   - `/api/sesiones` (GET): lista de sesiones
   - `/api/status` (GET): estado del sistema
   - `/api/brain/status` (GET): estado del HybridIntelligenceCore
   - `/api/vision/*` (GET/POST): endpoints de visión
   - `/api/upload` (POST): análisis de archivos
   - `/api/stop` (POST): abortar acciones en curso
5. THE `web/web_app.py` SHALL incluir cabeceras CORS configurables para permitir conexiones desde frontends en dominios distintos.
6. WHEN un endpoint falla, THE `web/web_app.py` SHALL retornar un JSON con la clave `"error"` y el código HTTP apropiado (400, 500, 503) en lugar de propagar la excepción.
7. THE `web/web_app.py` SHALL mantener la comunicación en tiempo real via WebSocket (SocketIO) para los eventos `respuesta`, `engine_indicator` y `doc_analysis`.

---

### Requisito 7: Módulo integrations/ con estructura base

**User Story:** Como desarrollador, quiero que `integrations/` exista con archivos base vacíos para Discord, Telegram, WhatsApp y YouTube, para que pueda implementar cada integración de forma aislada sin tocar el núcleo del sistema.

#### Criterios de Aceptación

1. THE Sistema SHALL crear los siguientes archivos dentro de `integrations/`:
   - `integrations/__init__.py`
   - `integrations/discord_bot.py`
   - `integrations/telegram_bot.py`
   - `integrations/whatsapp_bridge.py`
   - `integrations/youtube_client.py`
2. WHEN se crea un archivo de integración, THE archivo SHALL contener: docstring descriptivo, imports mínimos necesarios, y una clase base con método `start() -> None` y método `stop() -> None` que no hacen nada (pass).
3. THE `integrations/` SHALL NOT importar de `core/`, `memory/`, `personality/` ni `avatar/` directamente. IF una integración necesita enviar un mensaje a Alisha, THEN SHALL hacerlo a través de la API REST de `web/`.
4. THE `integrations/__init__.py` SHALL exponer una función `get_available_integrations() -> list[str]` que retorna los nombres de las integraciones disponibles.
5. WHERE una integración está habilitada en `config/settings.py`, THE Sistema SHALL inicializarla automáticamente desde `main.py` sin modificar el código de otros módulos.

---

### Requisito 8: Corrección de imports tras la migración

**User Story:** Como desarrollador, quiero que todos los imports del proyecto sean correctos después de mover los archivos, para que el sistema arranque sin errores de `ModuleNotFoundError`.

#### Criterios de Aceptación

1. WHEN un archivo es movido a su módulo destino, THE Sistema SHALL actualizar todos los imports que referencian ese archivo en el resto del proyecto.
2. THE imports relativos dentro de un mismo módulo SHALL usar la sintaxis de import relativo (ej: `from .brain import HybridIntelligenceCore`).
3. THE imports entre módulos distintos SHALL usar la sintaxis de import absoluto desde la raíz del proyecto (ej: `from core.brain import HybridIntelligenceCore`).
4. THE `core/__init__.py` SHALL exportar `HybridIntelligenceCore`, `AgentLoop`, `EmotionEngine` y `EventBus` para que otros módulos puedan importarlos con `from core import HybridIntelligenceCore`.
5. THE `memory/__init__.py` SHALL exportar `MemoryDB`, `AgentMemory` y `SemanticMemory`.
6. THE `personality/__init__.py` SHALL exportar `PersonalitySynthesizer`, `SkepticismEngine` y `CuriosityEngine`.
7. THE `services/__init__.py` SHALL exportar todos los clientes LLM disponibles.
8. WHEN el sistema arranca con `python main.py`, THE Sistema SHALL iniciar sin errores de `ImportError` ni `ModuleNotFoundError`.

---

### Requisito 9: Límite de tamaño de archivos

**User Story:** Como desarrollador, quiero que ningún archivo supere las 300 líneas sin justificación documentada, para que el código sea legible y mantenible.

#### Criterios de Aceptación

1. THE Sistema SHALL dividir `brain.py` (actualmente ~2000 líneas) en al menos los siguientes archivos dentro de `core/`:
   - `core/brain.py`: HybridIntelligenceCore, SmartRouter, UnifiedMemory (~300 líneas)
   - `core/orchestrator.py`: lógica de orquestación y routing de respuestas (~200 líneas)
   - `core/neural_bridge.py`: MicroGestureEngine, SarcasmScoreEngine (~150 líneas)
2. THE Sistema SHALL dividir `web_app.py` (actualmente ~2100 líneas) en al menos:
   - `web/web_app.py`: definición de la app Flask y SocketIO (~100 líneas)
   - `web/routes/chat.py`: endpoints de chat y audio (~200 líneas)
   - `web/routes/system.py`: endpoints de estado y control (~200 líneas)
   - `web/routes/files.py`: endpoints de upload y análisis (~200 líneas)
3. THE Sistema SHALL dividir `agent_loop.py` (actualmente ~1900 líneas) en al menos:
   - `core/agent_loop.py`: AgentLoop, EventBus (~300 líneas)
   - `core/screen_watcher.py`: ScreenWatcher, StateMapper (~200 líneas)
4. IF un archivo supera las 300 líneas, THEN THE archivo SHALL incluir un comentario al inicio que justifique el tamaño con una razón técnica específica.
5. THE `personality/` SHALL extraer `PersonalitySynthesizer` de `brain.py` a `personality/mood_engine.py` para que `core/brain.py` no contenga lógica de personalidad.

---

### Requisito 10: Preservación de funcionalidad existente

**User Story:** Como usuario de Alisha, quiero que todas las funcionalidades actuales sigan funcionando después de la refactorización, para que la migración no rompa nada de lo que ya uso.

#### Criterios de Aceptación

1. WHEN el sistema arranca con `python main.py` tras la migración, THE Sistema SHALL iniciar el servidor Flask en `localhost:5000`, el modelo Live2D y el ícono en bandeja del sistema, igual que con `Alisha_IA.py` actualmente.
2. THE Sistema SHALL preservar el comportamiento del SmartRouter: routing a Gemini para documentos/visión, Groq para respuestas rápidas, OpenAI para código, Ollama como fallback local.
3. THE Sistema SHALL preservar el EmotionEngine completo: dopamina, cansancio, humor, y todos sus métodos públicos.
4. THE Sistema SHALL preservar la comunicación via `data/chibi_state.json` entre `core/` y `avatar/` sin cambios en el formato del archivo.
5. THE Sistema SHALL preservar todos los endpoints de la API REST actualmente en `web_app.py` con las mismas rutas y contratos de respuesta.
6. THE Sistema SHALL preservar el sistema de memoria SQLite (`memory_db.py`) y JSON (`agent_memory.py`) sin cambios en el esquema de datos.
7. WHEN se ejecuta la suite de tests existente (si existe), THE Sistema SHALL pasar todos los tests que pasaban antes de la migración.
8. IF el sistema detecta que un módulo no pudo cargarse, THEN THE Sistema SHALL continuar operando en modo degradado (fail-silent) igual que en la implementación actual.
