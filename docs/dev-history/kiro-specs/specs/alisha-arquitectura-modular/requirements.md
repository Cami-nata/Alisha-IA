# Requirements Document

## Introduction

Este documento describe los requisitos para la transformacion arquitectonica del proyecto **Alisha IA** — una IA emocional y personaje digital con estetica ciberpunk/anime y personalidad rioplatense. El objetivo es migrar desde una estructura monolitica con ~80 archivos Python en la raiz hacia una arquitectura modular, desacoplada y escalable, organizada en paquetes con responsabilidades bien definidas.

La migracion debe preservar completamente la identidad y comportamiento de Alisha. Los modulos `personality/` y `avatar/` son componentes de primera clase, no decoracion. El resultado final debe permitir conectar un frontend moderno (React/Electron/Tauri), agregar voz input (Vosk), integrar plataformas externas (Discord/Telegram) y escalar a multiples instancias, todo sin modificar el nucleo.

## Glossary

- **Sistema**: El proyecto Alisha IA en su conjunto, incluyendo todos sus modulos.
- **Modulo**: Un paquete Python (directorio con `__init__.py`) con responsabilidad unica y bien definida.
- **core/**: Modulo que contiene el cerebro (`brain.py`), el puente neuronal (`neural_bridge.py`), el estado del asistente (`assistant_state.py`), el orquestador (`orchestrator.py`) y el motor emocional (`emotion_engine.py`).
- **memory/**: Modulo que contiene la base de datos de memoria (`memory_db.py`), la memoria episodica del agente (`agent_memory.py`) y la memoria semantica (`alisha_memoria_semantica.py`).
- **personality/**: Modulo que contiene la identidad de Alisha (`alisha_identity.py`), el motor de escepticismo (`skepticism_engine.py`), el motor de curiosidad (`alisha_curiosidad.py`) y el motor de estado de animo (`mood_engine.py`).
- **avatar/**: Modulo que contiene la cabina virtual Live2D (`cabina_virtual.py`), el puente de memoria compartida (`alisha_bridge.py`), la sincronizacion audio-visual (`audio_visual_sync.py`) y el motor TTS (`tts_engine.py`).
- **vision/**: Modulo que contiene el motor de vision (`vision_engine.py`), la vision de pantalla (`screen_vision.py`) y el monitor de contexto (`context_monitor.py`).
- **tools/**: Modulo que contiene las herramientas de accion (`tools.py`), el controlador de PC (`pc_controller.py`), el mouse natural (`natural_mouse.py`) y el guardia de seguridad (`safety_guard.py`).
- **services/**: Modulo que contiene los wrappers independientes de cada proveedor LLM: `gemini_client.py`, `groq_client.py`, `openai_client.py`, `ollama_client.py`, `mistral_client.py`.
- **integrations/**: Modulo que contiene los conectores a plataformas externas: `discord_bot.py`, `telegram_bot.py`, `whatsapp_bridge.py`, `youtube_client.py`. Inicialmente vacios con estructura base.
- **web/**: Modulo que contiene la aplicacion web Flask (`web_app.py`), templates y archivos estaticos.
- **data/**: Directorio que contiene todos los archivos `.json` y `.db` (SQLite) de persistencia.
- **config/**: Modulo que contiene la configuracion centralizada (`settings.py`), el cargador de variables de entorno (`env_loader.py`) y las constantes del sistema (`constants.py`).
- **main.py**: Unico punto de entrada del sistema. Solo inicializa modulos y arranca el sistema, sin logica propia.
- **Migrador**: El proceso automatizado que reorganiza los archivos segun la nueva estructura.
- **Import_Circular**: Dependencia donde el modulo A importa de B y B importa de A, creando un ciclo que impide la carga correcta.
- **Wrapper_LLM**: Clase o modulo que encapsula la comunicacion con un proveedor de modelo de lenguaje especifico, exponiendo una interfaz uniforme.
- **API_REST**: Interfaz de programacion basada en HTTP con endpoints JSON, sin estado de sesion en el servidor.
- **EventBus**: Sistema de publicacion/suscripcion en memoria para comunicacion desacoplada entre modulos.

## Requirements

### Requirement 1: Reorganizacion de la Estructura de Directorios

**User Story:** As a desarrolladora, I want todos los archivos Python organizados en paquetes con responsabilidad unica, so that pueda navegar, mantener y escalar el proyecto sin perderme entre 80 archivos en la raiz.

#### Acceptance Criteria

1. THE Sistema SHALL crear los directorios `core/`, `memory/`, `personality/`, `avatar/`, `vision/`, `tools/`, `services/`, `integrations/`, `web/`, `data/`, `config/` dentro de la raiz del proyecto.
2. THE Sistema SHALL crear un archivo `__init__.py` en cada uno de los directorios listados en el criterio anterior.
3. WHEN el Migrador mueve un archivo a su modulo destino, THE Sistema SHALL actualizar todos los imports que referencian ese archivo en el resto del proyecto para reflejar la nueva ruta del paquete.
4. THE Sistema SHALL mover cada archivo Python existente al modulo que corresponde segun la tabla de asignacion definida en la estructura objetivo, sin modificar la logica interna de ningun archivo.
5. WHEN la migracion finaliza, THE Sistema SHALL dejar la raiz del proyecto conteniendo unicamente `main.py`, archivos de configuracion de entorno (`.env`, `.gitignore`, `requirements.txt`) y directorios de paquetes.

---

### Requirement 2: Extraccion de Wrappers LLM a services/

**User Story:** As a desarrolladora, I want que cada proveedor de LLM sea un modulo independiente en `services/`, so that pueda agregar, quitar o cambiar proveedores sin tocar el cerebro de Alisha.

#### Acceptance Criteria

1. THE Sistema SHALL crear en `services/` un archivo independiente por cada proveedor LLM: `gemini_client.py`, `groq_client.py`, `openai_client.py`, `ollama_client.py`, `mistral_client.py`.
2. WHEN se extrae un Wrapper_LLM de `brain.py` u otro archivo, THE Sistema SHALL mover toda la logica de inicializacion, autenticacion y llamada a la API de ese proveedor al archivo correspondiente en `services/`.
3. THE Sistema SHALL definir en cada Wrapper_LLM una interfaz uniforme con al menos los metodos `chat(messages: list) -> str` y `is_available() -> bool`.
4. THE `core/brain.py` SHALL importar los clientes LLM exclusivamente desde `services/`, sin contener logica de inicializacion de proveedores.
5. IF un proveedor LLM no esta disponible (API key ausente o servicio caido), THEN THE Wrapper_LLM correspondiente SHALL retornar `is_available() == False` sin lanzar excepciones no controladas.
6. FOR ALL Wrapper_LLM en `services/`, serializar una solicitud y deserializar la respuesta SHALL producir el mismo resultado independientemente del proveedor utilizado (propiedad de interfaz uniforme).

---

### Requirement 3: Eliminacion de Dependencias Circulares

**User Story:** As a desarrolladora, I want que los modulos tengan un grafo de dependencias aciclico y bien definido, so that el sistema arranque sin errores de importacion y sea predecible.

#### Acceptance Criteria

1. THE Sistema SHALL respetar la jerarquia de dependencias: `core/` puede importar de `services/`, `memory/` y `personality/`; `personality/` NO SHALL importar de `core/`; `tools/` y `vision/` NO SHALL importar de `core/`; `avatar/` solo recibe datos de `core/` y NO SHALL importar de `core/` para logica de negocio.
2. WHEN se detecta un Import_Circular entre dos modulos durante la migracion, THE Sistema SHALL resolverlo extrayendo la dependencia compartida a un modulo de nivel inferior (como `config/` o un nuevo modulo de utilidades) o usando inyeccion de dependencias.
3. THE Sistema SHALL verificar la ausencia de Import_Circular ejecutando una importacion completa del paquete raiz sin errores de tipo `ImportError` o `CircularImportError`.
4. THE `personality/` SHALL comunicarse con `core/` exclusivamente a traves del EventBus o callbacks inyectados, sin importar directamente desde `core/`.
5. THE `tools/` y `vision/` SHALL ser modulos independientes que exponen funciones puras o clases sin estado compartido con `core/`.

---

### Requirement 4: Configuracion Centralizada en config/

**User Story:** As a desarrolladora, I want un unico lugar donde esten todas las variables de configuracion del sistema, so that no tenga que buscar en 10 archivos distintos cuando necesito cambiar un parametro.

#### Acceptance Criteria

1. THE Sistema SHALL crear `config/settings.py` como archivo central de configuracion que consolide todas las variables de entorno, rutas, umbrales y constantes actualmente dispersas en multiples archivos.
2. THE Sistema SHALL crear `config/env_loader.py` que cargue las variables de entorno desde `.env` usando `python-dotenv` y las exponga como atributos tipados.
3. THE Sistema SHALL crear `config/constants.py` que contenga todas las constantes del sistema (umbrales de CPU/RAM, intervalos de tiempo, limites de memoria, etc.) sin depender de variables de entorno.
4. WHEN cualquier modulo del sistema necesita una variable de configuracion, THE modulo SHALL importarla exclusivamente desde `config/`, no desde variables de entorno directamente ni desde otros modulos.
5. IF una variable de entorno requerida no esta definida en `.env`, THEN THE `config/env_loader.py` SHALL lanzar un error descriptivo al arranque indicando que variable falta, en lugar de fallar silenciosamente en tiempo de ejecucion.
6. THE `config/settings.py` SHALL exponer un objeto de configuracion unico (patron singleton o modulo-nivel) que sea importable con una sola linea desde cualquier modulo.

---

### Requirement 5: main.py como Unico Punto de Entrada

**User Story:** As a desarrolladora, I want que `main.py` sea el unico archivo que arranca el sistema, so that sea obvio donde empieza todo y no haya logica de negocio escondida en el punto de entrada.

#### Acceptance Criteria

1. THE `main.py` SHALL ser el unico archivo ejecutable directamente para arrancar el sistema completo (`python main.py`).
2. THE `main.py` SHALL contener exclusivamente: importacion de modulos, instanciacion de componentes principales, configuracion del orden de arranque y llamada al bucle principal.
3. THE `main.py` SHALL NOT contener logica de negocio, procesamiento de mensajes, acceso a base de datos ni llamadas directas a APIs externas.
4. WHEN `main.py` arranca, THE Sistema SHALL inicializar los modulos en el siguiente orden: `config/` -> `services/` -> `memory/` -> `personality/` -> `core/` -> `avatar/` -> `vision/` -> `tools/` -> `web/`.
5. IF cualquier modulo falla durante la inicializacion, THEN THE `main.py` SHALL registrar el error en el log de arranque y continuar con los modulos restantes (principio fail-silent), excepto para `config/` y `core/` que son criticos.
6. THE `main.py` SHALL tener una longitud maxima de 100 lineas de codigo.

---

### Requirement 6: API REST Limpia en web/

**User Story:** As a desarrolladora, I want que `web/web_app.py` exponga una API REST con endpoints JSON bien definidos, so that pueda conectar cualquier frontend moderno (React, Electron, Tauri) sin modificar el backend.

#### Acceptance Criteria

1. THE `web/web_app.py` SHALL exponer los siguientes endpoints JSON minimos: `POST /api/chat` (enviar mensaje y recibir respuesta), `GET /api/state` (estado emocional y animacion actual), `GET /api/memory/recent` (ultimos recuerdos), `POST /api/config` (actualizar configuracion en caliente).
2. WHEN un cliente envia una solicitud a `POST /api/chat`, THE `web/web_app.py` SHALL delegar el procesamiento al `core/orchestrator.py` sin contener logica de generacion de respuestas.
3. THE `web/web_app.py` SHALL retornar respuestas en formato JSON con estructura consistente: `{"status": "ok"|"error", "data": {...}, "timestamp": "ISO8601"}`.
4. THE `web/web_app.py` SHALL soportar WebSocket via Socket.IO para actualizaciones en tiempo real del estado emocional y lip-sync, manteniendo compatibilidad con el frontend actual.
5. THE `web/web_app.py` SHALL NOT importar directamente desde `brain.py`, `emotion_engine.py` ni ningun modulo de `core/` que no sea `core/orchestrator.py`.
6. WHEN el frontend solicita `GET /api/state`, THE `web/web_app.py` SHALL retornar el estado en menos de 50ms leyendo desde `data/chibi_state.json` sin invocar el LLM.

---

### Requirement 7: Modulo integrations/ con Estructura Base

**User Story:** As a desarrolladora, I want que `integrations/` exista con archivos base listos, so that pueda implementar Discord, Telegram y WhatsApp en el futuro sin tener que disenar la estructura desde cero.

#### Acceptance Criteria

1. THE Sistema SHALL crear los archivos `integrations/discord_bot.py`, `integrations/telegram_bot.py`, `integrations/whatsapp_bridge.py`, `integrations/youtube_client.py` con estructura base (clase vacia, docstring y metodo `start()` stub).
2. THE `integrations/__init__.py` SHALL exponer una funcion `load_integration(name: str) -> Optional[object]` que cargue dinamicamente el modulo de integracion solicitado.
3. THE archivos de `integrations/` SHALL NOT contener logica de negocio implementada en la migracion inicial — solo la estructura de clase y los metodos stub necesarios para implementacion futura.
4. WHEN se implementa una integracion en el futuro, THE integracion SHALL comunicarse con el sistema exclusivamente a traves de `core/orchestrator.py`, sin importar directamente de `core/brain.py` ni de `personality/`.
5. THE `integrations/` SHALL ser un modulo opcional: IF ninguna integracion esta activa, THEN THE Sistema SHALL arrancar y funcionar normalmente sin errores.

---

### Requirement 8: Preservacion de la Identidad y Personalidad de Alisha

**User Story:** As a usuaria, I want que Alisha mantenga exactamente su personalidad, voz rioplatense, reacciones emocionales y comportamiento despues de la migracion, so that la refactorizacion sea transparente desde mi perspectiva.

#### Acceptance Criteria

1. THE `personality/` SHALL contener todos los componentes de identidad de Alisha (`alisha_identity.py`, `skepticism_engine.py`, `alisha_curiosidad.py`, `mood_engine.py`) como modulos de primera clase con la misma logica que antes de la migracion.
2. WHEN Alisha genera una respuesta despues de la migracion, THE Sistema SHALL producir respuestas con el mismo estilo de voseo rioplatense, nivel de sarcasmo y reacciones emocionales que antes de la migracion.
3. THE `personality/` SHALL NOT ser importado por `core/` de forma directa — `core/` SHALL recibir el contexto de personalidad a traves de inyeccion de dependencias o el EventBus.
4. THE `avatar/` SHALL mantener todos los componentes de presentacion visual y auditiva (`cabina_virtual.py`, `alisha_bridge.py`, `audio_visual_sync.py`, `tts_engine.py`) con la misma funcionalidad de lip-sync y animaciones Live2D.
5. WHEN el motor de curiosidad (`personality/alisha_curiosidad.py`) genera una iniciativa espontanea, THE Sistema SHALL respetar el semaforo global de silencio (`alisha_silencio.py`) exactamente como lo hacia antes de la migracion.
6. FOR ALL respuestas generadas antes y despues de la migracion con el mismo input y estado emocional, THE Sistema SHALL producir respuestas con el mismo perfil de personalidad (voseo, temas de interes, nivel de acidez).

---

### Requirement 9: Independencia de vision/ y tools/

**User Story:** As a desarrolladora, I want que `vision/` y `tools/` sean modulos completamente independientes, so that pueda agregar Vosk (voz input) o nuevas herramientas sin tocar el nucleo del sistema.

#### Acceptance Criteria

1. THE `vision/` SHALL contener `vision_engine.py`, `screen_vision.py` y `context_monitor.py` como modulos que no importan de `core/`, `personality/` ni `avatar/`.
2. THE `tools/` SHALL contener `tools.py`, `pc_controller.py`, `natural_mouse.py` y `safety_guard.py` como modulos que no importan de `core/`, `personality/` ni `avatar/`.
3. WHEN se agrega un nuevo modulo de entrada (como Vosk para voz) en el futuro, THE Sistema SHALL permitir su integracion modificando unicamente `main.py` y el nuevo modulo, sin cambios en `core/`.
4. THE `tools/safety_guard.py` SHALL validar toda accion de control del PC antes de ejecutarla, independientemente del modulo que la solicite.
5. THE `vision/vision_engine.py` SHALL exponer una interfaz de solo lectura (`get_last_snapshot()`, `start()`, `stop()`) que `core/` pueda consumir sin conocer los detalles de implementacion de la captura de pantalla.

---

### Requirement 10: Limite de Tamano de Archivos y Cohesion

**User Story:** As a desarrolladora, I want que ningun archivo supere las 300 lineas sin justificacion documentada, so that el codigo sea legible y mantenible a largo plazo.

#### Acceptance Criteria

1. THE Sistema SHALL garantizar que ningun archivo Python en la nueva estructura supere las 300 lineas de codigo, excluyendo comentarios y lineas en blanco.
2. IF un archivo supera las 300 lineas durante la migracion, THEN THE Sistema SHALL dividirlo en submodulos dentro del mismo paquete, documentando la razon de la division en el `__init__.py` del paquete.
3. THE `core/brain.py` SHALL ser refactorizado para delegar la logica de cada proveedor LLM a `services/`, reduciendo su tamano al limite establecido.
4. THE `core/orchestrator.py` SHALL contener exclusivamente la logica de coordinacion entre modulos, sin logica de generacion de respuestas ni acceso directo a base de datos.
5. WHEN se crea un nuevo archivo durante la migracion, THE archivo SHALL tener una unica responsabilidad claramente expresada en su docstring de modulo.

---

### Requirement 11: Escalabilidad a Multiples Instancias

**User Story:** As a desarrolladora, I want que la arquitectura soporte multiples instancias de Alisha en el futuro, so that el sistema pueda escalar horizontalmente sin rediseno.

#### Acceptance Criteria

1. THE `core/assistant_state.py` SHALL gestionar el estado de una instancia de Alisha de forma aislada, sin variables globales de modulo que impidan multiples instancias simultaneas.
2. THE `memory/` SHALL acceder a los datos de persistencia usando identificadores de instancia, de modo que dos instancias de Alisha puedan coexistir con memorias separadas.
3. THE `config/settings.py` SHALL soportar configuracion por instancia mediante un parametro `instance_id` opcional, con valores por defecto para la instancia unica actual.
4. THE `services/` SHALL ser stateless: cada Wrapper_LLM SHALL poder ser instanciado multiples veces sin compartir estado entre instancias.
5. WHEN se ejecutan dos instancias del sistema simultaneamente con diferentes `instance_id`, THE Sistema SHALL mantener memorias, estados emocionales y configuraciones completamente separadas para cada instancia.
