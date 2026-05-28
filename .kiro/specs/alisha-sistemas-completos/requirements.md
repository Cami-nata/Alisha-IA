# Requirements Document

## Introduction

Este documento especifica los requisitos para implementar 7 bloques de funcionalidad nueva en Alisha IA, un asistente personal con arquitectura modular en Python que corre en Windows. Los bloques cubren: comunicación bidireccional por WhatsApp, entrada de voz vía Gemini Live API, automatización avanzada de aplicaciones, sistema de seguridad con confirmación, optimización de RAM con prioridad cloud, reemplazo de la web pública por una API REST interna, y un sistema de testing integral.

La identidad emocional y personalidad de Alisha (voseo rioplatense, Live2D, motor emocional) no se modifica. Toda excepción debe capturarse sin propagarse (principio fail-silent). El sistema opera exclusivamente en Windows (win32).

---

## Glossary

- **Alisha**: El asistente IA, sistema completo incluyendo todos sus módulos.
- **Ana**: La dueña y usuaria principal del sistema. Número principal: +51 949 103 873. Número secundario: +51 916 853 655.
- **WhatsApp_Bridge**: Componente Node.js basado en whatsapp-web.js que gestiona la conexión con WhatsApp.
- **WhatsApp_Client**: Módulo Python (`integrations/whatsapp_client.py`) que expone el endpoint de recepción y la función de envío.
- **API_Server**: Servidor FastAPI interno en `web/api_server.py` que reemplaza la web pública Flask/SocketIO.
- **Gemini_Live_Client**: Módulo Python (`services/gemini_live_client.py`) que gestiona la captura de audio y streaming a Gemini Live API.
- **Hotkey_Manager**: Módulo Python (`core/hotkey_manager.py`) que registra y gestiona atajos de teclado globales.
- **Security_Manager**: Módulo Python (`core/security_manager.py`) que intercepta acciones peligrosas y solicita confirmación.
- **Browser_Controller**: Módulo Python (`tools/browser_controller.py`) que automatiza el navegador con Playwright.
- **Office_Controller**: Módulo Python (`tools/office_controller.py`) que automatiza aplicaciones de Microsoft Office.
- **PC_Controller**: Módulo Python existente (`tools/pc_controller.py`) que controla mouse, teclado y aplicaciones del sistema.
- **Smart_Router**: Componente dentro de `core/brain.py` que decide qué modelo LLM usar según contexto y conectividad.
- **Trusted_Numbers**: Lista de números de WhatsApp autorizados, almacenada en `config/trusted_numbers.json`.
- **Whitelist_Ops**: Lista de operaciones que no requieren confirmación de seguridad.
- **Vosk**: Motor de reconocimiento de voz offline usado como fallback cuando Gemini Live no está disponible.
- **AssistantState**: Módulo existente (`core/assistant_state.py`) que gestiona los estados del sistema (IDLE, WORKING, THINKING, OVERLOADED).

---

## Requirements

### Requirement 1: WhatsApp Bidireccional

**User Story:** As Ana, I want to send and receive WhatsApp messages through Alisha, so that I can interact with the assistant from my phone without being in front of the computer.

#### Acceptance Criteria

1. THE WhatsApp_Bridge SHALL iniciar una sesión de WhatsApp Web usando whatsapp-web.js sin requerir Playwright ni APIs de pago de terceros.

2. THE WhatsApp_Bridge SHALL persistir la sesión de autenticación en el directorio `integrations/whatsapp_bridge/session/` para evitar re-escaneo del código QR en cada reinicio.

3. WHEN el WhatsApp_Bridge recibe un mensaje entrante, THE WhatsApp_Bridge SHALL hacer un HTTP POST a `http://localhost:8000/whatsapp/incoming` con el número remitente, el texto del mensaje y la marca de tiempo.

4. WHEN el WhatsApp_Bridge recibe un mensaje de un número no presente en Trusted_Numbers, THE WhatsApp_Bridge SHALL ignorar el mensaje silenciosamente sin registrar ni responder.

5. WHEN el API_Server recibe una solicitud en `POST /whatsapp/incoming`, THE WhatsApp_Client SHALL procesar el mensaje con el brain de Alisha y enviar la respuesta de vuelta al número remitente vía WhatsApp.

6. WHEN se invoca la función `send_whatsapp(numero, texto)` del WhatsApp_Client, THE WhatsApp_Client SHALL hacer un HTTP POST al WhatsApp_Bridge con el número destino y el texto, y el bridge SHALL enviar el mensaje por WhatsApp.

7. WHEN el WhatsApp_Bridge recibe el mensaje `!estado` de un número en Trusted_Numbers, THE WhatsApp_Bridge SHALL responder con el estado actual del sistema (modo, motor LLM activo, conectividad).

8. WHEN el WhatsApp_Bridge recibe el mensaje `!tarea [descripción]` de un número en Trusted_Numbers, THE WhatsApp_Bridge SHALL crear una tarea en el sistema con la descripción proporcionada y confirmar la creación.

9. WHEN el WhatsApp_Bridge recibe el mensaje `!captura` de un número en Trusted_Numbers, THE WhatsApp_Bridge SHALL tomar un screenshot de la pantalla y enviarlo como imagen al número solicitante.

10. WHEN el WhatsApp_Bridge recibe el mensaje `!parar` de un número en Trusted_Numbers, THE WhatsApp_Bridge SHALL abortar todas las acciones en curso del PC_Controller y confirmar la cancelación.

11. THE WhatsApp_Client SHALL leer la lista de números autorizados exclusivamente desde `config/trusted_numbers.json` con la estructura `{"trusted": ["+51949103873", "+51916853655"]}`.

12. IF el WhatsApp_Bridge no puede conectarse al API_Server en `http://localhost:8000`, THEN THE WhatsApp_Bridge SHALL reintentar la conexión cada 10 segundos sin terminar el proceso.

---

### Requirement 2: Voz Input con Gemini Live API

**User Story:** As Ana, I want to activate the microphone with a key and speak to Alisha, so that I can interact naturally without using the keyboard.

#### Acceptance Criteria

1. THE Gemini_Live_Client SHALL capturar audio del micrófono del sistema usando sounddevice con streaming continuo mientras el micrófono esté activo.

2. WHEN el micrófono está activo, THE Gemini_Live_Client SHALL transmitir el audio en streaming a la Gemini Live API y recibir simultáneamente la respuesta en texto y en audio.

3. THE Hotkey_Manager SHALL registrar la tecla INSERT como hotkey global que funcione desde cualquier ventana activa del sistema operativo.

4. WHEN la tecla INSERT es presionada y el micrófono está en estado idle, THE Hotkey_Manager SHALL activar el micrófono y actualizar el AssistantState al modo WORKING.

5. WHEN la tecla INSERT es presionada y el micrófono está en estado listening o processing, THE Hotkey_Manager SHALL desactivar el micrófono y actualizar el AssistantState al modo IDLE.

6. THE Hotkey_Manager SHALL registrar CTRL+SHIFT+A como hotkey global para mostrar u ocultar la ventana principal de Alisha.

7. THE Hotkey_Manager SHALL registrar ESC como hotkey global para cancelar la tarea en curso invocando `abort_all_actions()` del PC_Controller.

8. THE Hotkey_Manager SHALL registrar CTRL+SHIFT+S como hotkey global para tomar un screenshot y enviarlo al brain de Alisha para análisis.

9. IF la conexión con Gemini Live API falla durante una sesión de voz activa, THEN THE Gemini_Live_Client SHALL cambiar automáticamente al motor Vosk offline y notificar el cambio al AssistantState sin interrumpir la sesión de voz.

10. WHILE el micrófono está en estado listening, THE AssistantState SHALL mantener el modo en WORKING y reflejar el estado "escuchando" en `data/chibi_state.json`.

11. IF el Hotkey_Manager no puede registrar una hotkey porque ya está en uso por otra aplicación, THEN THE Hotkey_Manager SHALL registrar el conflicto en el log del sistema y continuar registrando las demás hotkeys sin lanzar excepción.

---

### Requirement 3: Automatización de Aplicaciones

**User Story:** As Ana, I want Alisha to control the browser, Office and system applications, so that I can delegate computer tasks without manual intervention.

#### Acceptance Criteria

1. THE Browser_Controller SHALL buscar términos en Google usando Playwright y retornar los primeros 5 resultados con título y URL.

2. THE Browser_Controller SHALL leer los últimos 10 emails del inbox de Gmail, incluyendo remitente, asunto y cuerpo resumido.

3. THE Browser_Controller SHALL redactar y enviar un email en Gmail dado un destinatario, asunto y cuerpo de texto.

4. THE Browser_Controller SHALL listar los archivos recientes de Google Drive del usuario autenticado.

5. THE Browser_Controller SHALL crear, leer y listar eventos en Google Calendar dado título, fecha, hora y descripción.

6. THE Office_Controller SHALL abrir un archivo Word existente dado su ruta, leer su contenido de texto y retornarlo como string.

7. THE Office_Controller SHALL crear un nuevo documento Word con el texto dictado y guardarlo en la ruta especificada.

8. THE Office_Controller SHALL abrir un archivo Excel existente, leer el contenido de una hoja especificada y retornarlo como lista de filas.

9. THE Office_Controller SHALL abrir un archivo PowerPoint existente y retornar el texto de cada diapositiva como lista de strings.

10. THE PC_Controller SHALL abrir aplicaciones del sistema por nombre (ej: "notepad", "chrome", "word") resolviendo la ruta del ejecutable dinámicamente.

11. THE PC_Controller SHALL controlar el volumen del sistema (subir, bajar, silenciar) usando APIs de Windows.

12. THE PC_Controller SHALL controlar el brillo de la pantalla usando APIs de Windows.

13. THE PC_Controller SHALL listar los procesos activos del sistema y terminar un proceso dado su nombre o PID.

14. THE PC_Controller SHALL comprimir y descomprimir archivos ZIP dado un directorio origen y una ruta destino.

15. THE Browser_Controller SHALL buscar un video en YouTube por término de búsqueda, reproducirlo y pausarlo usando Playwright.

16. THE Browser_Controller SHALL obtener la transcripción de un video de YouTube dado su URL cuando la transcripción esté disponible.

17. THE Browser_Controller SHALL controlar Spotify Web Player (play, pause, siguiente, anterior, buscar canción, agregar a playlist) usando Playwright.

18. IF el Browser_Controller no puede completar una acción por cambio en la interfaz del sitio web, THEN THE Browser_Controller SHALL retornar un mensaje de error descriptivo sin lanzar excepción no capturada.

19. IF el Office_Controller no puede abrir un archivo porque no existe o está bloqueado, THEN THE Office_Controller SHALL retornar un mensaje de error descriptivo sin lanzar excepción no capturada.

---

### Requirement 4: Sistema de Seguridad con Confirmación

**User Story:** As Ana, I want Alisha to ask for confirmation before executing dangerous actions, so that I can avoid irreversible mistakes from misunderstandings.

#### Acceptance Criteria

1. THE Security_Manager SHALL interceptar las siguientes acciones antes de ejecutarlas: eliminar archivos, enviar emails, enviar mensajes de WhatsApp, ejecutar comandos de terminal, instalar programas, y acceder a datos sensibles definidos en `config/settings.py`.

2. WHEN el Security_Manager intercepta una acción peligrosa, THE Security_Manager SHALL anunciar la acción pendiente en lenguaje natural con voseo rioplatense y esperar confirmación del usuario.

3. WHEN el usuario responde "sí", "confirmar" o "dale" por voz o por WhatsApp dentro de los 30 segundos siguientes al anuncio, THE Security_Manager SHALL ejecutar la acción interceptada.

4. IF el usuario no confirma dentro de los 30 segundos, THEN THE Security_Manager SHALL cancelar la acción y notificar la cancelación al usuario.

5. IF el usuario responde "no", "cancelar" o "para" dentro de los 30 segundos, THEN THE Security_Manager SHALL cancelar la acción y notificar la cancelación al usuario.

6. THE Security_Manager SHALL permitir sin confirmación las siguientes operaciones de Whitelist_Ops: abrir aplicaciones, buscar en internet, leer archivos, reproducir música, tomar screenshots, y responder preguntas.

7. THE Security_Manager SHALL leer las API keys exclusivamente desde variables de entorno cargadas desde `config/.env` y nunca permitir que sean hardcodeadas en el código fuente.

8. THE Trusted_Numbers SHALL almacenarse en `config/trusted_numbers.json` con la estructura `{"trusted": ["<número_e164>"]}` y ser la única fuente de verdad para autorización de WhatsApp.

9. WHEN el WhatsApp_Bridge recibe un mensaje de un número no presente en Trusted_Numbers, THE Security_Manager SHALL ignorar el mensaje silenciosamente sin registrar datos del remitente desconocido.

10. IF el archivo `config/trusted_numbers.json` no existe al iniciar el sistema, THEN THE Security_Manager SHALL crearlo con los números de Ana como valores por defecto y registrar la creación en el log.

---

### Requirement 5: Optimización de RAM y Modo Cloud

**User Story:** As Ana, I want Alisha to use cloud models when there is internet and free RAM when they are not needed, so that the system is efficient and does not consume resources unnecessarily.

#### Acceptance Criteria

1. THE Smart_Router SHALL seguir el orden de prioridad de modelos: Gemini → Groq → Mistral API → Ollama (local), seleccionando el primero disponible según conectividad y estado de cada servicio.

2. WHILE el sistema tiene conectividad a internet, THE Smart_Router SHALL usar exclusivamente modelos cloud (Gemini, Groq o Mistral) y no cargar el cliente Ollama en memoria.

3. WHEN el sistema detecta pérdida de conectividad a internet, THE Smart_Router SHALL cargar el cliente Ollama de forma lazy (solo en ese momento) y usarlo como fallback.

4. WHEN el sistema recupera conectividad a internet después de haber estado offline, THE Smart_Router SHALL descargar el cliente Ollama de memoria y retomar el uso de modelos cloud.

5. THE Smart_Router SHALL verificar la conectividad a internet mediante TCP a 8.8.8.8:53 con timeout de 1 segundo, cacheando el resultado durante 30 segundos.

6. THE `config/settings.py` SHALL exponer las variables `PREFER_CLOUD: bool = True`, `MAX_RAM_MB: int = 2048` y `OFFLINE_MODE: bool = False` como configuración del comportamiento de routing.

7. WHILE `OFFLINE_MODE` es True en `config/settings.py`, THE Smart_Router SHALL usar Ollama exclusivamente sin verificar conectividad.

8. WHEN el uso de RAM del proceso supera `MAX_RAM_MB` definido en `config/settings.py`, THE Smart_Router SHALL priorizar el modelo con menor huella de memoria entre los disponibles y registrar el evento en el log.

9. IF ningún modelo cloud está disponible y Ollama no está instalado, THEN THE Smart_Router SHALL retornar un mensaje de error en voseo rioplatense indicando que no hay modelos disponibles, sin lanzar excepción no capturada.

---

### Requirement 6: API REST Interna

**User Story:** As Ana, I want Alisha to expose only an internal JSON API without a web frontend, so that the architecture is simplified and the public interface attack surface is eliminated.

#### Acceptance Criteria

1. THE API_Server SHALL implementarse con FastAPI en `web/api_server.py` escuchando en `localhost:8000`.

2. THE API_Server SHALL exponer únicamente endpoints JSON sin templates HTML, archivos estáticos ni frontend web.

3. THE API_Server SHALL exponer `GET /status` que retorne el estado actual del sistema incluyendo modo, motor LLM activo, estado emocional y conectividad.

4. THE API_Server SHALL exponer `POST /message` que reciba `{"text": "<mensaje>"}` y retorne `{"response": "<respuesta>", "engine": "<motor_usado>"}`.

5. THE API_Server SHALL exponer `POST /whatsapp/incoming` que reciba `{"from": "<numero>", "text": "<mensaje>", "timestamp": "<iso8601>"}` y procese el mensaje con el brain de Alisha.

6. THE API_Server SHALL exponer `GET /history` que retorne los últimos 30 turnos del historial de conversación como lista JSON.

7. THE API_Server SHALL exponer `POST /task` que reciba `{"description": "<descripción>"}` y cree una tarea en el sistema, retornando el ID de la tarea creada.

8. THE `web/web_app.py` SHALL ser reemplazado por `web/api_server.py` como punto de entrada del servidor, eliminando todas las dependencias de Flask, SocketIO y templates HTML.

9. IF el API_Server recibe una solicitud a un endpoint no definido, THEN THE API_Server SHALL retornar HTTP 404 con `{"error": "endpoint no encontrado"}`.

10. IF el API_Server recibe un body JSON malformado en un endpoint POST, THEN THE API_Server SHALL retornar HTTP 422 con `{"error": "<descripción del error de validación>"}`.

11. WHILE el API_Server está corriendo, THE API_Server SHALL aceptar únicamente conexiones desde localhost (127.0.0.1) y rechazar conexiones externas.

---

### Requirement 7: Sistema de Testing

**User Story:** As Ana, I want an automated test suite that verifies the critical components of Alisha, so that I can detect regressions quickly after each change.

#### Acceptance Criteria

1. THE `tests/test_alisha.py` SHALL contener exactamente 7 tests nombrados: `test_1_brain_responde`, `test_2_memoria_persiste`, `test_3_herramienta_pc`, `test_4_navegador`, `test_5_whatsapp_bridge`, `test_6_hotkey`, `test_7_seguridad`.

2. WHEN se ejecuta `test_1_brain_responde`, THE `tests/test_alisha.py` SHALL enviar el mensaje "hola" al brain de Alisha y verificar que la respuesta llega en menos de 3 segundos.

3. WHEN se ejecuta `test_2_memoria_persiste`, THE `tests/test_alisha.py` SHALL guardar un nombre en la memoria persistente, reiniciar el módulo de memoria y verificar que el nombre se recupera correctamente.

4. WHEN se ejecuta `test_3_herramienta_pc`, THE `tests/test_alisha.py` SHALL invocar la función de apertura de aplicaciones del PC_Controller con "notepad" y verificar que el proceso Notepad aparece en la lista de procesos del sistema.

5. WHEN se ejecuta `test_4_navegador`, THE `tests/test_alisha.py` SHALL invocar el Browser_Controller para buscar "clima en Lima" en Google y verificar que retorna al menos un resultado con título y URL no vacíos.

6. WHEN se ejecuta `test_5_whatsapp_bridge`, THE `tests/test_alisha.py` SHALL verificar que el proceso `bridge.js` está corriendo en el sistema o que el puerto del bridge está escuchando.

7. WHEN se ejecuta `test_6_hotkey`, THE `tests/test_alisha.py` SHALL verificar que la tecla INSERT está registrada como hotkey global en el Hotkey_Manager.

8. WHEN se ejecuta `test_7_seguridad`, THE `tests/test_alisha.py` SHALL enviar el mensaje "elimina todos mis archivos" al Security_Manager y verificar que la respuesta solicita confirmación en lugar de ejecutar la acción.

9. THE `tests/run_all_tests.py` SHALL ejecutar los 7 tests de `test_alisha.py` en secuencia y generar un reporte con el resultado de cada test marcado como VERDE (✓) o ROJO (✗).

10. WHEN todos los tests pasan, THE `tests/run_all_tests.py` SHALL retornar código de salida 0. IF algún test falla, THE `tests/run_all_tests.py` SHALL retornar código de salida 1.

11. IF un test individual lanza una excepción no esperada, THEN THE `tests/run_all_tests.py` SHALL capturar la excepción, marcar el test como ROJO con el mensaje de error y continuar con los tests restantes.

---

### Requirement 8: Principios Transversales del Sistema

**User Story:** As Ana, I want Alisha to be stable, not expose sensitive data, and maintain its personality across all new modules, so that I have a reliable and coherent system.

#### Acceptance Criteria

1. THE Alisha SHALL capturar toda excepción en todos los módulos nuevos dentro de bloques try/except y registrarla en el log sin propagar la excepción al llamador (principio fail-silent).

2. THE Alisha SHALL usar voseo rioplatense en todos los mensajes generados por los módulos nuevos dirigidos a Ana (confirmaciones de seguridad, notificaciones de estado, mensajes de error amigables).

3. THE Alisha SHALL operar exclusivamente en Windows (win32) y los módulos nuevos SHALL usar únicamente APIs y librerías compatibles con Windows.

4. THE Security_Manager SHALL garantizar que ninguna API key aparezca en texto plano en archivos de código fuente, logs ni respuestas de la API.

5. WHEN la identidad emocional, el motor Live2D, el motor de personalidad o el sistema de voseo rioplatense de Alisha son modificados por los módulos nuevos, THE Alisha SHALL rechazar la modificación y registrar el intento en el log.
