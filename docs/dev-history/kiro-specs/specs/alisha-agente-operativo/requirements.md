# Documento de Requisitos

## Introducción

Alisha es una IA con modelo Live2D (IceGirl) que corre en Windows. Actualmente funciona como asistente de chat con capacidades de visión pasiva, autonomía básica y personalidad dinámica. Esta feature la evoluciona a un **Agente Operativo Real**: un sistema que percibe el entorno de forma continua, toma iniciativa, ejecuta acciones con naturalidad y persiste su memoria en base de datos, todo sin romper el flujo de chat ni el modelo Live2D existentes.

El principio rector es **fail-silent**: si cualquier componente nuevo falla, Alisha sigue funcionando como siempre.

---

## Glosario

- **Alisha**: La IA principal. Habla en voseo rioplatense con personalidad propia.
- **AgentLoop**: Bucle central de percepción-decisión-acción que corre en hilo daemon.
- **EventBus**: Sistema de publicación/suscripción interno para comunicar eventos entre módulos.
- **ScreenWatcher**: Componente que monitorea ventanas activas, archivos y música de forma continua.
- **NaturalMouse**: Módulo de control de mouse con trayectorias curvas y velocidad variable.
- **AssistanceProtocol**: Protocolo de 4 pasos: analizar pantalla → buscar info → generar propuesta → crear archivo.
- **MemoryDB**: Base de datos SQLite que reemplaza los JSON de memoria episódica.
- **StateMapper**: Componente que traduce estados operativos (IDLE/THINKING/WORKING/OVERLOADED) a parámetros Live2D.
- **MouseCoordinator**: Componente que detecta movimiento del mouse del usuario y cede el control.
- **GeminiVision**: Integración con Gemini para análisis semántico de capturas de pantalla.
- **chibi_state.json**: Archivo de estado compartido entre módulos y el modelo Live2D.
- **Camila**: Nombre de la usuaria principal (puede configurarse).
- **Voseo rioplatense**: Forma de hablar de Alisha: "vos tenés", "hacé", "mirá", etc.

---

## Requisitos

### Requisito 1: Bucle Continuo de Percepción de Eventos

**User Story:** Como usuaria, quiero que Alisha perciba cambios en mi entorno (archivos, ventanas, música) de forma continua y autónoma, para que pueda reaccionar sin que yo tenga que iniciar la conversación.

#### Criterios de Aceptación

1. THE AgentLoop SHALL ejecutarse en un hilo daemon con ciclos de percepción cada 5 segundos.
2. WHEN el AgentLoop detecta un cambio de ventana activa, THE EventBus SHALL publicar un evento `window_changed` con el título y proceso de la nueva ventana.
3. WHEN el AgentLoop detecta que un archivo fue creado o modificado en el directorio de trabajo de Camila en los últimos 30 segundos, THE EventBus SHALL publicar un evento `file_changed` con la ruta y tipo del archivo.
4. WHEN el AgentLoop detecta un cambio en los metadatos de audio de Windows (título o artista diferente al anterior), THE EventBus SHALL publicar un evento `media_changed` con título, artista y aplicación.
5. IF el AgentLoop lanza una excepción no controlada en un ciclo, THEN THE AgentLoop SHALL registrar el error en el log y continuar el siguiente ciclo sin interrumpir el sistema.
6. WHILE el sistema de chat web está procesando una respuesta, THE AgentLoop SHALL continuar su ciclo de percepción sin interferir con el hilo de Flask/SocketIO.

---

### Requisito 2: Estados Operativos Mapeados a Gestos Live2D

**User Story:** Como usuaria, quiero que el modelo Live2D de Alisha refleje visualmente su estado operativo actual, para tener retroalimentación visual de lo que está haciendo.

#### Criterios de Aceptación

1. THE StateMapper SHALL traducir el estado IDLE a los parámetros Live2D: `estado="neutral"`, `gaze_x=0.0`, `gaze_y=0.0`, `mouth_amplitude=0.0`.
2. THE StateMapper SHALL traducir el estado THINKING a los parámetros Live2D: `estado="curiosidad"`, `gaze_x` con valor aleatorio entre -0.3 y 0.3, `gaze_y` entre -0.2 y 0.2.
3. THE StateMapper SHALL traducir el estado WORKING a los parámetros Live2D: `estado="concentración"`, `gaze_x=0.0`, `gaze_y=-0.1`, `mouth_amplitude=0.0`.
4. THE StateMapper SHALL traducir el estado OVERLOADED a los parámetros Live2D: `estado="frustración"`, `gaze_x` con valor aleatorio entre -0.5 y 0.5, `gaze_y=0.3`.
5. WHEN el StateMapper escribe en chibi_state.json, THE StateMapper SHALL preservar todos los campos existentes del archivo y solo actualizar los campos de estado y gaze.
6. IF chibi_state.json no existe o está corrupto, THEN THE StateMapper SHALL crear un archivo nuevo con valores por defecto sin lanzar excepción.
7. WHEN el estado cambia de WORKING a IDLE, THE StateMapper SHALL aplicar una transición gradual de 2 segundos antes de escribir el estado IDLE en chibi_state.json.

---

### Requisito 3: Control de Mouse con Trayectorias Naturales

**User Story:** Como usuaria, quiero que cuando Alisha mueva el mouse, lo haga con movimientos curvos y velocidad variable, para que se sienta natural y no robótico.

#### Criterios de Aceptación

1. THE NaturalMouse SHALL mover el cursor desde la posición actual hasta el destino siguiendo una curva de Bézier cuadrática con un punto de control aleatorio desplazado entre 20 y 80 píxeles del eje directo.
2. THE NaturalMouse SHALL variar la velocidad del movimiento usando una función de aceleración/desaceleración (ease-in-out), con duración total entre 0.3 y 1.2 segundos según la distancia.
3. WHEN la distancia al destino es menor a 50 píxeles, THE NaturalMouse SHALL usar movimiento lineal directo con duración de 0.15 segundos.
4. THE NaturalMouse SHALL agregar micro-variaciones aleatorias de ±2 píxeles en cada paso intermedio del movimiento para simular imprecisión humana.
5. IF PyAutoGUI lanza una excepción FailSafeException durante el movimiento, THEN THE NaturalMouse SHALL detener el movimiento y registrar el evento sin propagar la excepción.
6. THE NaturalMouse SHALL exponer una función `mover_a(x, y)` y una función `click_natural(x, y)` que reemplacen las llamadas directas a `pyautogui.moveTo` y `pyautogui.click` en actions.py.

---

### Requisito 4: Reconocimiento de Aplicaciones Activas

**User Story:** Como usuaria, quiero que Alisha reconozca qué aplicación estoy usando (Canva, PowerPoint, navegador, etc.) y adapte su comportamiento y rol, para recibir asistencia contextualmente relevante.

#### Criterios de Aceptación

1. THE ScreenWatcher SHALL detectar la aplicación activa leyendo el título de la ventana en primer plano y el nombre del proceso cada 5 segundos.
2. WHEN el ScreenWatcher detecta una aplicación de diseño (Canva, Figma, Photoshop, Illustrator), THE EventBus SHALL publicar un evento `app_context_changed` con `rol="directora_creativa"`.
3. WHEN el ScreenWatcher detecta una aplicación de desarrollo (VS Code, PyCharm, terminal), THE EventBus SHALL publicar un evento `app_context_changed` con `rol="senior_dev"`.
4. WHEN el ScreenWatcher detecta un navegador web (Chrome, Edge, Firefox), THE EventBus SHALL publicar un evento `app_context_changed` con `rol="investigadora"`.
5. WHEN el ScreenWatcher detecta una aplicación de ofimática (Word, Excel, PowerPoint, LibreOffice), THE EventBus SHALL publicar un evento `app_context_changed` con `rol="asistente_ejecutiva"`.
6. WHEN el AgentLoop recibe un evento `app_context_changed`, THE AgentLoop SHALL actualizar el rol activo en chibi_state.json bajo la clave `"rol_activo"`.
7. IF la aplicación activa no coincide con ninguna categoría conocida, THEN THE ScreenWatcher SHALL publicar el evento con `rol="companion"` sin lanzar excepción.

---

### Requisito 5: Coordinación de Mouse — Ceder Control al Usuario

**User Story:** Como usuaria, quiero que Alisha deje de mover el mouse inmediatamente cuando yo lo muevo, para que nunca haya conflicto entre mis acciones y las de ella.

#### Criterios de Aceptación

1. THE MouseCoordinator SHALL monitorear la posición del mouse cada 100 milisegundos usando pynput o psutil.
2. WHEN el MouseCoordinator detecta que la posición del mouse cambió más de 5 píxeles respecto a la última posición registrada, THE MouseCoordinator SHALL publicar un evento `user_mouse_active` en el EventBus.
3. WHEN el AgentLoop recibe el evento `user_mouse_active`, THE AgentLoop SHALL cancelar cualquier operación de NaturalMouse en curso y cambiar el estado operativo a IDLE.
4. WHILE el estado operativo es IDLE por causa de `user_mouse_active`, THE AgentLoop SHALL esperar al menos 3 segundos sin movimiento del usuario antes de permitir nuevas operaciones de mouse.
5. THE MouseCoordinator SHALL registrar el timestamp del último movimiento del usuario en chibi_state.json bajo la clave `"ultimo_movimiento_usuario"`.
6. IF pynput no está disponible, THEN THE MouseCoordinator SHALL usar polling de posición con pyautogui.position() como fallback sin interrumpir el sistema.

---

### Requisito 6: Capturas Silenciosas con Análisis Gemini

**User Story:** Como usuaria, quiero que Alisha tome capturas de pantalla periódicas y las analice con Gemini para entender qué estoy diseñando o trabajando, para que pueda ofrecer ayuda proactiva y contextualmente relevante.

#### Criterios de Aceptación

1. THE GeminiVision SHALL tomar una captura de pantalla silenciosa cada 10 a 15 segundos con intervalo aleatorio para naturalidad.
2. WHEN la captura es tomada, THE GeminiVision SHALL enviarla a Gemini con el prompt: "Describí brevemente en 1-2 oraciones qué está haciendo esta persona en su computadora. Sé específico sobre la app y la tarea visible."
3. WHEN Gemini retorna una descripción, THE GeminiVision SHALL almacenarla en un buffer circular de las últimas 5 descripciones en memoria.
4. WHEN el brain.py procesa una consulta del usuario, THE GeminiVision SHALL proveer la descripción más reciente como contexto adicional si tiene menos de 30 segundos de antigüedad.
5. IF el uso de CPU supera el 70%, THEN THE GeminiVision SHALL pausar las capturas automáticas hasta que el CPU baje del 60% sin interrumpir el sistema.
6. IF la API de Gemini retorna un error, THEN THE GeminiVision SHALL registrar el error, esperar 60 segundos y reintentar sin propagar la excepción al sistema principal.
7. THE GeminiVision SHALL operar en modo completamente silencioso: sin logs visibles al usuario, sin modificar el flujo de chat, sin emitir eventos de voz.

---

### Requisito 7: Extracción de Metadatos de Audio de Windows

**User Story:** Como usuaria, quiero que Alisha sepa qué música estoy escuchando en tiempo real, para que pueda reaccionar con su personalidad musical y adaptar su estado de ánimo.

#### Criterios de Aceptación

1. THE ScreenWatcher SHALL leer los metadatos de audio de Windows cada 5 segundos usando el módulo alisha_media.py existente.
2. WHEN alisha_media.py retorna un título y artista diferentes a los del ciclo anterior, THE EventBus SHALL publicar un evento `media_changed` con los nuevos metadatos.
3. WHEN el AgentLoop recibe un evento `media_changed`, THE AgentLoop SHALL actualizar chibi_state.json con la clave `"media_actual"` conteniendo título, artista y aplicación.
4. WHEN el AgentLoop recibe un evento `media_changed` y el género detectado tiene afinidad mayor a 0.6 en alisha_identity.py, THE AgentLoop SHALL activar el gesto de tarareo del módulo GestosNoVerbales existente.
5. WHEN el AgentLoop recibe un evento `media_changed` y el género detectado tiene afinidad menor a -0.5 en alisha_identity.py, THE AgentLoop SHALL activar el gesto de ojo_en_blanco del módulo GestosNoVerbales existente.
6. IF alisha_media.py no está disponible o retorna None, THEN THE ScreenWatcher SHALL continuar el ciclo sin publicar el evento `media_changed` y sin lanzar excepción.

---

### Requisito 8: Protocolo de Asistencia Operativa

**User Story:** Como usuaria, quiero que cuando le pida a Alisha que me ayude con una tarea compleja, ella ejecute un protocolo estructurado de 4 pasos, para recibir una propuesta concreta y un archivo de resultado.

#### Criterios de Aceptación

1. WHEN el usuario envía un mensaje que contiene palabras clave de solicitud de asistencia ("ayudame con", "hacé un", "creá un", "analizá", "buscá info sobre"), THE AssistanceProtocol SHALL iniciar el protocolo de 4 pasos.
2. WHEN el AssistanceProtocol inicia, THE AssistanceProtocol SHALL ejecutar el Paso 1: tomar captura de pantalla y enviarla a GeminiVision para obtener contexto visual.
3. WHEN el Paso 1 completa, THE AssistanceProtocol SHALL ejecutar el Paso 2: consultar al brain.py con el contexto visual y la solicitud del usuario para generar una propuesta estructurada.
4. WHEN el Paso 2 completa, THE AssistanceProtocol SHALL ejecutar el Paso 3: presentar la propuesta al usuario via SocketIO con el evento `"propuesta_asistencia"` antes de ejecutar ninguna acción.
5. WHEN el usuario confirma la propuesta (responde "sí", "dale", "hacelo", "ok"), THE AssistanceProtocol SHALL ejecutar el Paso 4: crear el archivo de resultado usando las funciones existentes de actions.py.
6. WHEN el AssistanceProtocol crea un archivo, THE AssistanceProtocol SHALL notificar al usuario via SocketIO con la ruta del archivo creado.
7. IF cualquier paso del AssistanceProtocol falla, THEN THE AssistanceProtocol SHALL notificar al usuario con un mensaje en voseo rioplatense explicando el problema y ofrecer continuar sin ese paso.
8. THE AssistanceProtocol SHALL actualizar el estado operativo a WORKING durante la ejecución y a IDLE al completar o fallar.

---

### Requisito 9: Persistencia de Memoria con Base de Datos

**User Story:** Como usuaria, quiero que Alisha recuerde conversaciones, preferencias y contexto de sesiones anteriores de forma confiable, para que la relación con ella mejore con el tiempo sin perder información.

#### Criterios de Aceptación

1. THE MemoryDB SHALL usar SQLite como motor de base de datos con el archivo `alisha_memory.db` en el directorio raíz del proyecto.
2. THE MemoryDB SHALL mantener las siguientes tablas: `conversaciones` (id, timestamp, entrada, respuesta, estado_emocional), `preferencias` (clave, valor, timestamp), `sesiones` (id, inicio, fin, actividad_principal, resumen).
3. WHEN el sistema procesa un turno de conversación, THE MemoryDB SHALL persistir la entrada del usuario y la respuesta de Alisha en la tabla `conversaciones` dentro de los 2 segundos posteriores a la respuesta.
4. WHEN el sistema inicia, THE MemoryDB SHALL cargar las últimas 20 conversaciones en memoria para acceso rápido sin leer el archivo JSON de memoria existente.
5. THE MemoryDB SHALL proveer una función `buscar_contexto(query: str) -> list[dict]` que retorne las 5 conversaciones más relevantes usando búsqueda por similitud de texto (LIKE en SQLite).
6. WHEN la tabla `conversaciones` supera 10.000 registros, THE MemoryDB SHALL archivar los registros más antiguos en una tabla `conversaciones_archivo` sin eliminarlos.
7. IF la base de datos SQLite está bloqueada o corrupta, THEN THE MemoryDB SHALL hacer fallback a los archivos JSON existentes (ia_recuerdos.json, memory.json) sin interrumpir el sistema.
8. THE MemoryDB SHALL ser compatible con el módulo agent_memory.py existente: las funciones `get_memory()` y `ultimo_tema_activo()` deben seguir funcionando sin modificación.

---

### Requisito 10: Sistema Unificado en Proceso Único

**User Story:** Como usuaria, quiero que todos los componentes nuevos del agente operativo se inicien desde Alisha_IA.py sin modificar el flujo existente, para que el sistema siga siendo un único proceso con bandeja del sistema.

#### Criterios de Aceptación

1. THE Alisha_IA.py SHALL iniciar el AgentLoop como hilo daemon adicional después de iniciar el servidor web y antes de iniciar el ícono de bandeja.
2. WHEN Alisha_IA.py inicia el AgentLoop, THE AgentLoop SHALL iniciar el ScreenWatcher, MouseCoordinator, GeminiVision y MemoryDB como sub-componentes internos.
3. THE Alisha_IA.py SHALL mantener el orden de inicio existente: servidor web → Live2D → saludo inicial → bandeja del sistema.
4. IF cualquier componente del AgentLoop falla al iniciar, THEN THE Alisha_IA.py SHALL registrar el error y continuar el inicio sin ese componente.
5. WHEN el usuario selecciona "Cerrar Alisha" desde el ícono de bandeja, THE AgentLoop SHALL detener todos sus sub-componentes de forma ordenada antes de que el proceso termine.
6. THE AgentLoop SHALL exponer un endpoint HTTP en `/api/agent/status` que retorne el estado actual de todos sus sub-componentes en formato JSON para diagnóstico.
7. WHILE el AgentLoop está activo, THE AgentLoop SHALL escribir un heartbeat en chibi_state.json bajo la clave `"agent_heartbeat"` con el timestamp actual cada 30 segundos.
