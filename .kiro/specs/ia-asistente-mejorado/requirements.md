# Requisitos: ia-asistente-mejorado

## Requisito 1: Motor TTS Singleton

**Historia de usuario**: Como usuario del asistente, quiero que las respuestas de voz se reproduzcan sin demora perceptible para que la conversación fluya de forma natural.

### Criterios de Aceptación

1.1. DADO que el asistente está en ejecución CUANDO se llama a `speak()` por primera vez ENTONCES el motor `pyttsx3` se inicializa una sola vez y permanece activo durante toda la sesión.

1.2. DADO que el motor TTS está activo CUANDO se llama a `speak(texto)` ENTONCES el texto se encola y se procesa sin bloquear el hilo principal del asistente.

1.3. DADO que el motor TTS falla internamente CUANDO ocurre una excepción en la síntesis ENTONCES el error se loguea, el texto se imprime en consola como fallback, y el motor continúa procesando mensajes posteriores sin crashear.

1.4. DADO que se llama a `TTSEngine.get_instance()` múltiples veces ENTONCES siempre retorna la misma instancia (patrón singleton).

1.5. DADO que hay mensajes en cola CUANDO se procesan ENTONCES se respeta el orden FIFO de inserción.

---

## Requisito 2: Descubrimiento Dinámico de Aplicaciones

**Historia de usuario**: Como usuario, quiero poder pedirle al asistente que abra cualquier aplicación instalada en mi PC para no estar limitado a Chrome, Edge y Word.

### Criterios de Aceptación

2.1. DADO que el usuario pide abrir una app CUANDO la app está en `APP_RUTAS` de `config.py` ENTONCES se abre usando la ruta hardcodeada (compatibilidad preservada).

2.2. DADO que el usuario pide abrir una app no en `APP_RUTAS` CUANDO la app está en `Program Files`, `Program Files (x86)`, `AppData\Local` o `AppData\Roaming` ENTONCES el sistema la encuentra y la abre.

2.3. DADO que el usuario pide abrir una app CUANDO la app está disponible en el PATH del sistema ENTONCES `shutil.which()` la resuelve y se abre.

2.4. DADO que el usuario pide abrir una app CUANDO la app está registrada en el registro de Windows ENTONCES se encuentra vía `winreg` y se abre.

2.5. DADO que una app fue encontrada previamente CUANDO el usuario la pide de nuevo ENTONCES se usa la caché en memoria (sin búsqueda en disco).

2.6. DADO que la app no se encuentra en ninguna fuente CUANDO se intenta resolver ENTONCES se lanza `ValueError` con mensaje descriptivo y el asistente informa al usuario.

2.7. DADO que el sistema arranca ENTONCES las rutas cacheadas se persisten en `app_cache.json` y se cargan al inicio para arranques rápidos.

---

## Requisito 3: Expiración Automática del Estado de Ánimo

**Historia de usuario**: Como usuario, quiero que el asistente no recuerde indefinidamente cómo me sentía hace días para que sus respuestas sean relevantes al momento actual.

### Criterios de Aceptación

3.1. DADO que el usuario indica su estado de ánimo CUANDO se guarda ENTONCES se registra junto con un timestamp ISO en `perfil["ultima_actualizacion_estado"]`.

3.2. DADO que han pasado menos de 24 horas desde que se guardó el estado CUANDO el asistente consulta el estado ENTONCES retorna el estado guardado.

3.3. DADO que han pasado 24 horas o más desde que se guardó el estado CUANDO el asistente consulta el estado ENTONCES retorna `None` y resetea `perfil["estado"]` a `None`.

3.4. DADO que existe un estado sin timestamp (datos legacy) CUANDO el asistente consulta el estado ENTONCES lo trata como expirado y retorna `None`.

3.5. DADO que el estado expiró CUANDO el usuario interactúa ENTONCES el asistente puede preguntar cómo se siente hoy (sin forzarlo).

---

## Requisito 4: Recordatorios con Alarmas Reales

**Historia de usuario**: Como usuario, quiero que el asistente me avise en el momento exacto que le indiqué para no perder eventos importantes.

### Criterios de Aceptación

4.1. DADO que el usuario pide un recordatorio con expresión temporal CUANDO la expresión es "en X minutos/horas" ENTONCES se parsea correctamente a un `datetime` futuro.

4.2. DADO que el usuario pide un recordatorio CUANDO la expresión es "mañana a las Hpm" o "hoy a las HH:MM" ENTONCES se parsea correctamente.

4.3. DADO que el usuario pide un recordatorio CUANDO la expresión menciona un día de la semana (ej: "el viernes") ENTONCES se calcula el próximo día correspondiente.

4.4. DADO que se programa un recordatorio CUANDO llega el momento indicado ENTONCES el TTS reproduce la alerta y se muestra una notificación de escritorio.

4.5. DADO que se programa un recordatorio CUANDO la expresión temporal no es parseable ENTONCES se lanza `ValueError` y el asistente pide al usuario que sea más específico.

4.6. DADO que el programa se cierra con recordatorios pendientes CUANDO se reinicia ENTONCES los recordatorios con `cuando_datetime` en el futuro se restauran automáticamente.

4.7. DADO que el programa se reinicia y hay recordatorios cuyo tiempo ya pasó CUANDO se cargan ENTONCES se marcan como completados y se notifica al usuario al inicio.

4.8. DADO que existe un recordatorio activo CUANDO el usuario pide cancelarlo por ID ENTONCES el timer se cancela y el recordatorio se marca como completado.

---

## Requisito 5: Detección Inteligente de Necesidad de Screenshot

**Historia de usuario**: Como usuario, quiero que el asistente no tome capturas de pantalla en cada mensaje para que las respuestas sean más rápidas.

### Criterios de Aceptación

5.1. DADO que el usuario envía un mensaje CUANDO el mensaje contiene palabras clave de visión ("qué hay", "qué ves", "captura", "pantalla", "dónde está", etc.) ENTONCES se toma un screenshot y se incluye en el contexto.

5.2. DADO que el usuario envía un mensaje CUANDO el mensaje no contiene palabras clave de visión ENTONCES NO se toma screenshot; se usa contexto ligero (título de ventana activa, proceso en foco).

5.3. DADO que se obtiene contexto ligero CUANDO no hay screenshot ENTONCES el contexto incluye al menos `ventana_activa` y `proceso_activo` obtenidos vía `win32gui`.

5.4. DADO que `necesita_screenshot(mensaje)` se llama con el mismo mensaje ENTONCES siempre retorna el mismo resultado (función pura y determinista).

---

## Requisito 6: Acciones de Sistema Extendidas

**Historia de usuario**: Como usuario, quiero controlar el volumen, reproducir música, buscar archivos y ajustar el brillo desde el asistente para tener control total de mi laptop.

### Criterios de Aceptación

6.1. DADO que el usuario pide subir/bajar el volumen CUANDO se ejecuta la acción ENTONCES el volumen del sistema cambia en el porcentaje indicado (usando `pycaw`).

6.2. DADO que el usuario pide silenciar o restaurar el audio CUANDO se ejecuta la acción ENTONCES el sistema se silencia o restaura correctamente.

6.3. DADO que el usuario pide establecer el volumen a un valor específico CUANDO el valor está entre 0 y 100 ENTONCES el volumen se establece en ese porcentaje exacto.

6.4. DADO que el usuario pide reproducir música CUANDO se ejecuta la acción ENTONCES se abre el reproductor predeterminado o se busca en YouTube/Spotify según configuración.

6.5. DADO que el usuario pide pausar/siguiente/anterior CUANDO hay música reproduciéndose ENTONCES se envían las teclas multimedia correspondientes vía `pyautogui`.

6.6. DADO que el usuario pide buscar un archivo CUANDO se ejecuta la búsqueda ENTONCES retorna hasta 10 rutas encontradas en el directorio base especificado (o `C:\Users` por defecto).

6.7. DADO que el usuario pide subir/bajar el brillo CUANDO se ejecuta la acción ENTONCES el brillo de la pantalla cambia usando `screen-brightness-control`.

6.8. DADO que el usuario pide información del sistema CUANDO se ejecuta `diagnosticar` ENTONCES se reporta CPU%, RAM%, espacio en disco y temperatura si está disponible.

---

## Requisito 7: Reintentos con Backoff Exponencial para Ollama

**Historia de usuario**: Como usuario, quiero que el asistente reintente automáticamente cuando Ollama no responde para no tener que repetir mi mensaje manualmente.

### Criterios de Aceptación

7.1. DADO que Ollama no responde (timeout) CUANDO ocurre el error ENTONCES el sistema reintenta automáticamente hasta 3 veces.

7.2. DADO que se realizan reintentos CUANDO cada intento falla ENTONCES el tiempo de espera entre intentos sigue backoff exponencial: 1s, 2s, 4s.

7.3. DADO que todos los reintentos fallan CUANDO se agota `max_reintentos` ENTONCES se lanza `RuntimeError` con mensaje descriptivo y el asistente informa al usuario sin crashear.

7.4. DADO que ocurre un error irrecuperable (no timeout/conexión) CUANDO se detecta ENTONCES NO se reintenta y se propaga el error inmediatamente.

7.5. DADO que un reintento tiene éxito CUANDO Ollama responde ENTONCES se retorna la respuesta normalmente sin indicar al usuario que hubo reintentos.

---

## Requisito 8: Evolución de Identidad de la IA

**Historia de usuario**: Como usuario, quiero que la personalidad del asistente evolucione con el tiempo basándose en nuestras interacciones para que se sienta como un compañero que crece.

### Criterios de Aceptación

8.1. DADO que la IA tiene una identidad ENTONCES `ia_identidad.json` incluye campos `version`, `fecha_creacion`, `fecha_ultima_evolucion`, `rasgos` y `tono_preferido`.

8.2. DADO que se han acumulado 20 o más interacciones desde la última evolución CUANDO el asistente evalúa la identidad ENTONCES consulta a Ollama para proponer una evolución gradual de personalidad.

8.3. DADO que se propone una evolución CUANDO se aplica ENTONCES `version` se incrementa, `fecha_ultima_evolucion` se actualiza, y los cambios son graduales (no reemplazan completamente la personalidad anterior).

8.4. DADO que el usuario solicita explícitamente una evolución CUANDO se ejecuta `forzar_evolucion()` ENTONCES la identidad se actualiza inmediatamente sin esperar las 20 interacciones.

8.5. DADO que la identidad evoluciona CUANDO se guarda ENTONCES `ia_identidad.json` se actualiza y la nueva personalidad se usa en el siguiente mensaje.

---

## Requisito 9: Contexto de Memoria Ampliado para el Prompt

**Historia de usuario**: Como usuario, quiero que el asistente recuerde más contexto de nuestra conversación para dar respuestas más coherentes.

### Criterios de Aceptación

9.1. DADO que se construye el prompt para Ollama CUANDO se incluye memoria reciente ENTONCES se usan las últimas 10 entradas del historial (en lugar de 5).

9.2. DADO que el historial en disco ENTONCES se mantienen las últimas 50 entradas (comportamiento actual preservado).

9.3. DADO que cada entrada del historial ENTONCES incluye el campo `contexto_pantalla` con el título de la ventana activa al momento de la interacción.

9.4. DADO que el historial supera 50 entradas CUANDO se guarda ENTONCES se trunca a las últimas 50 entradas sin excepción.

---

## Requisito 11: IA con Personalidad Emocional y Humana

**Historia de usuario**: Como usuario, quiero que la IA sea como un compañero virtual real con emociones genuinas, no un asistente robótico, para que la interacción se sienta natural y significativa.

### Criterios de Aceptación

11.1. DADO que la IA tiene una identidad ENTONCES `ia_identidad.json` (o colección `identidad` en MongoDB) incluye campos `estado_emocional_base`, `frases_caracteristicas`, `humor_activo`, y `puede_iniciar`.

11.2. DADO que la IA responde a un mensaje CUANDO el estado emocional es "alegría" ENTONCES el tono es entusiasta, usa expresiones positivas y puede incluir humor ligero.

11.3. DADO que la IA responde a un mensaje CUANDO el estado emocional es "preocupación" ENTONCES el tono es empático, hace preguntas de seguimiento y expresa cuidado genuino.

11.4. DADO que la IA responde a un mensaje CUANDO el estado emocional es "curiosidad" ENTONCES hace preguntas genuinas sobre el tema y muestra interés real.

11.5. DADO que el usuario menciona algo personal (cansancio, logro, problema) CUANDO la IA procesa el mensaje ENTONCES actualiza su estado emocional acorde y responde con empatía.

11.6. DADO que la IA tiene `puede_iniciar=True` CUANDO han pasado más de 5 minutos sin interacción ENTONCES puede generar un mensaje espontáneo de curiosidad o saludo.

11.7. DADO que la IA responde ENTONCES usa lenguaje coloquial en español: contracciones, expresiones naturales, y evita sonar formal o robótico.

11.8. DADO que el usuario mencionó algo en una conversación anterior CUANDO la IA lo recuerda ENTONCES puede hacer referencia a ello de forma natural ("oye, ¿cómo te fue con lo que me contaste de...?").

11.9. DADO que el prompt del sistema se construye ENTONCES incluye el estado emocional actual de la IA, instrucciones de tono específicas, y frases características de su personalidad.

11.10. DADO que el estado emocional de la IA cambia ENTONCES el cambio es gradual (no brusco) y se persiste entre sesiones.

---

## Requisito 12: Interacción Solo por Texto — Sin Reconocimiento de Voz

**Historia de usuario**: Como usuario, quiero interactuar con la IA escribiendo texto y escuchar sus respuestas por voz, sin necesidad de micrófono ni reconocimiento de voz.

### Criterios de Aceptación

12.1. DADO que el usuario arranca el asistente ENTONCES el sistema NO pregunta si desea usar reconocimiento de voz; siempre usa `input()` para recibir texto.

12.2. DADO que `voice.py` existe ENTONCES solo contiene la función `speak(text)` y la inicialización del motor TTS; no contiene `elegir_modo_entrada()`, `escuchar_voz()`, ni imports de `speech_recognition`.

12.3. DADO que el usuario escribe un mensaje CUANDO presiona Enter ENTONCES la IA procesa el texto y responde por voz (TTS).

12.4. DADO que `speech_recognition` no está instalado ENTONCES el sistema funciona sin errores ni advertencias relacionadas con esa librería.

12.5. DADO que el loop principal en `ia.py` se ejecuta ENTONCES siempre usa `input("Tú: ")` para recibir la entrada del usuario, sin ninguna lógica de modo voz/texto.

12.6. DADO que la GUI tkinter está activa CUANDO el usuario escribe en el campo de texto ENTONCES la IA responde por TTS (igual que en modo terminal).

---

## Requisito 13: Persistencia en MongoDB con Fallback a JSON

**Historia de usuario**: Como usuario, quiero que el asistente guarde el historial de conversaciones en MongoDB para tener más capacidad y mejor rendimiento, pero que siga funcionando si MongoDB no está corriendo.

### Criterios de Aceptación

13.1. DADO que MongoDB está disponible en `mongodb://localhost:27017/` CUANDO el asistente arranca ENTONCES se conecta automáticamente a la base de datos `ia_asistente`.

13.2. DADO que MongoDB está disponible CUANDO se guarda una entrada de historial ENTONCES se persiste en la colección `historial` con índice por `fecha` descendente.

13.3. DADO que MongoDB está disponible ENTONCES el historial puede contener hasta 500 entradas (en lugar de 50 con JSON).

13.4. DADO que MongoDB no está disponible CUANDO el asistente arranca ENTONCES se activa automáticamente el fallback a JSON sin errores ni crashes.

13.5. DADO que el fallback JSON está activo ENTONCES el comportamiento es idéntico al sistema anterior: historial de 50 entradas, archivos `ia_memoria.json` e `ia_identidad.json`.

13.6. DADO que MongoDB está disponible ENTONCES las colecciones `perfil`, `recordatorios`, `identidad`, y `app_cache` se usan en lugar de los archivos JSON correspondientes.

13.7. DADO que MongoDB se cae durante una sesión activa CUANDO ocurre un error de escritura ENTONCES el sistema detecta la falla, loguea un aviso, y continúa con fallback JSON para esa sesión.

13.8. DADO que el sistema usa MongoDB ENTONCES `memory.py` expone la misma interfaz pública (`cargar_memoria`, `guardar_memoria`, `agregar_memoria`, etc.) independientemente del backend.

13.9. DADO que el historial en MongoDB supera 500 entradas CUANDO se agrega una nueva ENTONCES se elimina automáticamente la entrada más antigua.

13.10. DADO que el sistema arranca con MongoDB disponible ENTONCES crea automáticamente los índices necesarios (historial por fecha) si no existen.

**Historia de usuario**: Como usuario, quiero tener una interfaz gráfica opcional para interactuar con el asistente de forma más cómoda que la terminal.

### Criterios de Aceptación

10.1. DADO que el usuario arranca el asistente CUANDO elige modo GUI ENTONCES se abre una ventana tkinter con área de chat, campo de entrada y botón de envío.

10.2. DADO que la GUI está activa CUANDO el usuario escribe y envía un mensaje ENTONCES la respuesta del asistente aparece en el área de chat con diferenciación visual (usuario vs asistente).

10.3. DADO que la GUI está activa CUANDO el asistente habla ENTONCES el TTS funciona igual que en modo terminal.

10.4. DADO que el usuario no elige modo GUI CUANDO arranca el asistente ENTONCES el sistema funciona exactamente igual que antes (modo terminal, sin cambios).

10.5. DADO que la GUI está activa CUANDO el usuario cierra la ventana ENTONCES el asistente se detiene limpiamente (TTS detenido, timers cancelados).

10.6. DADO que la GUI está activa CUANDO hay un error ENTONCES el mensaje de error se muestra en el área de chat en lugar de solo en la terminal.

---

## Requisito 10: GUI Opcional con tkinter

**Historia de usuario**: Como usuario, quiero tener una interfaz gráfica opcional para interactuar con el asistente de forma más cómoda que la terminal.

### Criterios de Aceptación

10.1. DADO que el usuario arranca el asistente CUANDO elige modo GUI ENTONCES se abre una ventana tkinter con área de chat, campo de entrada y botón de envío.

10.2. DADO que la GUI está activa CUANDO el usuario escribe y envía un mensaje ENTONCES la respuesta del asistente aparece en el área de chat con diferenciación visual (usuario vs asistente).

10.3. DADO que la GUI está activa CUANDO el asistente habla ENTONCES el TTS funciona igual que en modo terminal.

10.4. DADO que el usuario no elige modo GUI CUANDO arranca el asistente ENTONCES el sistema funciona exactamente igual que antes (modo terminal, sin cambios).

10.5. DADO que la GUI está activa CUANDO el usuario cierra la ventana ENTONCES el asistente se detiene limpiamente (TTS detenido, timers cancelados).

10.6. DADO que la GUI está activa CUANDO hay un error ENTONCES el mensaje de error se muestra en el área de chat en lugar de solo en la terminal.

---

## Requisito 14: Navegación Web Real con Playwright

**Historia de usuario**: Como usuario, quiero que la IA pueda navegar por internet de verdad — abrir páginas, hacer clicks, llenar formularios y leer contenido — para que pueda ayudarme con tareas web reales.

### Criterios de Aceptación

14.1. DADO que el usuario pide abrir una URL CUANDO se ejecuta la acción ENTONCES Playwright abre la página en Chrome (o Edge/Firefox como fallback) y espera a que cargue.

14.2. DADO que el usuario pide buscar algo en Google CUANDO se ejecuta la acción ENTONCES la IA abre `google.com`, escribe la búsqueda y presiona Enter.

14.3. DADO que el usuario pide hacer click en un elemento CUANDO el elemento existe en la página ENTONCES Playwright hace click por selector CSS o por texto visible del elemento.

14.4. DADO que el usuario pide escribir en un campo CUANDO el campo existe ENTONCES Playwright limpia el campo y escribe el texto indicado.

14.5. DADO que el usuario pide leer la página actual CUANDO se ejecuta la acción ENTONCES la IA extrae el texto visible y lo resume en su respuesta.

14.6. DADO que ocurre un error de navegación (página no encontrada, timeout) CUANDO se detecta ENTONCES el error se captura, la IA informa al usuario con un mensaje amigable y el navegador no se cierra.

14.7. DADO que el asistente arranca ENTONCES Playwright NO inicia el navegador hasta que se necesite (lazy initialization).

14.8. DADO que el usuario dice "cierra el navegador" CUANDO se ejecuta la acción ENTONCES el navegador se cierra limpiamente y el singleton se resetea.

14.9. DADO que `playwright` no está instalado CUANDO se intenta usar una acción web ENTONCES el sistema informa al usuario que debe ejecutar `pip install playwright && playwright install chromium`.

---

## Requisito 15: Conocimientos de Informática y Programación

**Historia de usuario**: Como usuario, quiero que la IA sepa de programación, código y tecnología para que pueda ayudarme a programar, debuggear y aprender informática.

### Criterios de Aceptación

15.1. DADO que el usuario hace una pregunta de programación CUANDO la IA responde ENTONCES da una respuesta técnica precisa con ejemplos de código cuando sea relevante.

15.2. DADO que el usuario pide revisar un error o bug CUANDO la IA analiza el mensaje ENTONCES identifica el problema, explica la causa y sugiere la solución con código corregido.

15.3. DADO que el usuario pide que la IA escriba un script o función CUANDO se ejecuta ENTONCES la IA genera código funcional en el lenguaje solicitado (Python por defecto).

15.4. DADO que el usuario pide ejecutar un snippet de Python CUANDO se ejecuta la acción `ejecutar_codigo` ENTONCES el código se ejecuta en un subprocess con timeout de 10 segundos y se retorna el output.

15.5. DADO que el código a ejecutar contiene operaciones peligrosas (imports de os con comandos destructivos, etc.) CUANDO se detecta ENTONCES se rechaza la ejecución y se informa al usuario.

15.6. DADO que la identidad de la IA se genera ENTONCES incluye expertise en: Python, JavaScript, algoritmos, estructuras de datos, bases de datos, redes, sistemas operativos Windows/Linux, debugging, y buenas prácticas de código.

15.7. DADO que el usuario pide explicar un concepto de informática CUANDO la IA responde ENTONCES usa analogías claras, ejemplos prácticos y adapta el nivel de detalle al contexto de la conversación.
