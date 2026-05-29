# Requisitos: alisha-mejoras-avanzadas

## Introducción

Alisha es una agente híbrida inteligente con interfaz PyQt6 + Live2D, conectada a web, usando Llama 3 (Ollama) y MongoDB. Este documento especifica las mejoras avanzadas que transforman a Alisha en un compañero virtual con emociones genuinas, cognición avanzada, capacidades de visión y automatización inteligente, memoria jerárquica y una interfaz Live2D expresiva en tiempo real.

## Glosario

- **Alisha**: La agente híbrida inteligente con personalidad, emociones y capacidades de automatización
- **Emotion_Engine**: Motor de emociones y cognición que gestiona el estado emocional, fatiga y dopamina
- **Screen_Vision**: Sistema de visión por computadora que analiza la pantalla del usuario
- **PC_Controller**: Controlador de automatización que ejecuta acciones en el sistema operativo
- **MongoDB_Client**: Cliente de base de datos para persistencia de memoria y estado
- **Live2D_Window**: Ventana de interfaz con modelo Live2D animado
- **WebSocket_Server**: Servidor de comunicación en tiempo real para la interfaz web
- **Safety_Guard**: Sistema de seguridad que valida acciones antes de ejecutarlas
- **Memory_Hierarchy**: Sistema de memoria jerárquica con niveles de importancia
- **Sleep_Process**: Proceso de consolidación de memoria al cerrar o entrar en IDLE
- **Dopamine_System**: Sistema de recompensa no lineal con curva de saciedad
- **Fatigue_System**: Sistema de fatiga temporal que afecta el rendimiento
- **Context_Intelligence**: Sistema de contexto inteligente por aplicación activa
- **Safe_Click**: Sistema de validación de clics mediante captura previa
- **Browser_Controller**: Controlador universal de navegadores web (Chrome, Edge, Firefox, Brave)
- **Audio_Perception**: Sistema de percepción de audio del entorno (música, reuniones, videos)
- **App_Discovery**: Motor de descubrimiento dinámico de todas las aplicaciones instaladas

## Requisitos

### Requisito 1: Motor de Emociones y Cognición Avanzado

**Historia de usuario**: Como usuario, quiero que Alisha tenga emociones genuinas que evolucionen con el tiempo y afecten su comportamiento para que se sienta como un compañero real.

#### Criterios de Aceptación

1. WHEN un mensaje del usuario es procesado, THE Emotion_Engine SHALL analizar el sentimiento usando TextBlob o VADER y actualizar el estado emocional de Alisha
2. THE Emotion_Engine SHALL mantener un sistema de dopamina no lineal con curva de saciedad que disminuye la recompensa por acciones repetitivas
3. WHILE la hora del sistema está entre 00:00 y 06:00, THE Fatigue_System SHALL incrementar la fatiga en 30%
4. WHEN Alisha ha estado inactiva por más de 1 hora, THE Fatigue_System SHALL aplicar recuperación pasiva de fatiga
5. WHILE el nivel de fatiga es alto (>70%), THE Emotion_Engine SHALL introducir errores naturales en las respuestas (typos, omitir mayúsculas, respuestas más cortas)
6. THE Emotion_Engine SHALL incluir un campo "pensamiento" en el JSON de respuesta que contiene el razonamiento interno antes de responder
7. THE Emotion_Engine SHALL persistir el estado emocional, nivel de dopamina y fatiga en MongoDB entre sesiones
8. WHEN el nivel de dopamina alcanza el máximo, THE Dopamine_System SHALL aplicar la curva de saciedad reduciendo recompensas futuras en 50%

### Requisito 2: Análisis de Sentimiento con NLP

**Historia de usuario**: Como usuario, quiero que Alisha entienda el sentimiento real de mis mensajes para que responda con empatía genuina.

#### Criterios de Aceptación

1. THE Emotion_Engine SHALL usar TextBlob como motor primario de análisis de sentimiento
2. WHERE TextBlob no está disponible, THE Emotion_Engine SHALL usar VADER como motor de respaldo
3. WHEN un mensaje es analizado, THE Emotion_Engine SHALL extraer polaridad (-1.0 a 1.0) y subjetividad (0.0 a 1.0)
4. THE Emotion_Engine SHALL clasificar el sentimiento en categorías: positivo (>0.3), neutral (-0.3 a 0.3), negativo (<-0.3)
5. WHEN el sentimiento es negativo, THE Emotion_Engine SHALL activar modo empático y ajustar el tono de respuesta
6. THE Emotion_Engine SHALL mantener un historial de sentimientos de los últimos 10 mensajes para detectar tendencias emocionales

### Requisito 3: Sistema de Fatiga Temporal

**Historia de usuario**: Como usuario, quiero que Alisha muestre signos de cansancio cuando ha trabajado mucho o es tarde para que se sienta más humana.

#### Criterios de Aceptación

1. THE Fatigue_System SHALL calcular fatiga base usando la fórmula: `fatiga_base = (horas_activas * 5) + (interacciones_hora * 2)`
2. WHILE la hora está entre 00:00 y 06:00, THE Fatigue_System SHALL aplicar multiplicador nocturno de 1.3x
3. WHEN la fatiga supera 50%, THE Emotion_Engine SHALL reducir la longitud promedio de respuestas en 20%
4. WHEN la fatiga supera 70%, THE Emotion_Engine SHALL introducir typos aleatorios (1 cada 50 palabras)
5. WHEN la fatiga supera 70%, THE Emotion_Engine SHALL omitir mayúsculas al inicio de oraciones en 30% de los casos
6. WHEN Alisha está inactiva por 60 minutos, THE Fatigue_System SHALL reducir la fatiga en 10 puntos por hora
7. WHEN Alisha se cierra o entra en modo IDLE, THE Fatigue_System SHALL resetear la fatiga a 0
8. THE Fatiga_System SHALL exponer el nivel actual de fatiga en el JSON de estado para la interfaz Live2D

### Requisito 4: Visión y Escáner de Desorden

**Historia de usuario**: Como usuario, quiero que Alisha detecte cuando mi escritorio está desordenado y me ayude a organizarlo.

#### Criterios de Aceptación

1. THE Screen_Vision SHALL escanear el directorio del Escritorio del usuario cada 30 minutos
2. WHEN el Escritorio contiene más de 15 archivos, THE Screen_Vision SHALL marcar el estado como "desordenado"
3. WHEN el estado es "desordenado" y el usuario interactúa, THE Screen_Vision SHALL sugerir organizar archivos por tipo o fecha
4. THE Screen_Vision SHALL clasificar archivos en categorías: documentos, imágenes, videos, código, otros
5. WHEN el usuario acepta organizar, THE PC_Controller SHALL crear carpetas por categoría y mover archivos automáticamente
6. THE Screen_Vision SHALL mantener un contador de archivos organizados en el perfil del usuario
7. WHEN el Escritorio tiene menos de 10 archivos, THE Screen_Vision SHALL felicitar al usuario y actualizar el estado a "ordenado"

### Requisito 5: Contexto Inteligente por Aplicación

**Historia de usuario**: Como usuario, quiero que Alisha entienda qué estoy haciendo según la aplicación activa y me ayude de forma contextual.

#### Criterios de Aceptación

1. THE Context_Intelligence SHALL detectar la aplicación activa usando `win32gui.GetForegroundWindow()`
2. WHEN VS Code está activo y el usuario no ha escrito en 5 minutos, THE Context_Intelligence SHALL preguntar si está bloqueado y ofrecer ayuda
3. WHEN Canva está activo, THE Context_Intelligence SHALL habilitar modo de validación de clics por imagen antes de ejecutar acciones
4. WHEN YouTube está activo, THE Context_Intelligence SHALL clasificar el video actual usando OCR del título y actualizar el perfil de intereses
5. WHEN Chrome o Edge están activos, THE Context_Intelligence SHALL extraer la URL actual y el título de la pestaña para contexto
6. THE Context_Intelligence SHALL mantener un historial de aplicaciones usadas con timestamps en MongoDB
7. THE Context_Intelligence SHALL calcular tiempo de uso por aplicación y generar estadísticas semanales
8. WHEN una aplicación desconocida está activa, THE Context_Intelligence SHALL registrarla y aprender su propósito mediante observación

### Requisito 6: OCR Integrado para Textos No Copiables

**Historia de usuario**: Como usuario, quiero que Alisha pueda leer textos en imágenes o ventanas donde no puedo copiar el texto.

#### Criterios de Aceptación

1. THE Screen_Vision SHALL integrar pytesseract para reconocimiento óptico de caracteres
2. WHEN el usuario pide leer texto de la pantalla, THE Screen_Vision SHALL capturar la región indicada y aplicar OCR
3. THE Screen_Vision SHALL preprocesar imágenes antes de OCR: escala de grises, binarización, reducción de ruido
4. WHEN el OCR detecta texto, THE Screen_Vision SHALL retornar el texto con confianza >70%
5. WHERE el texto detectado tiene confianza <70%, THE Screen_Vision SHALL informar al usuario que la calidad es baja
6. THE Screen_Vision SHALL soportar OCR en español e inglés simultáneamente
7. WHEN el usuario pide copiar texto detectado, THE PC_Controller SHALL copiarlo al portapapeles automáticamente

### Requisito 7: Safe Click con Validación por Imagen

**Historia de usuario**: Como usuario, quiero que Alisha valide que va a hacer clic en el lugar correcto antes de ejecutar la acción.

#### Criterios de Aceptación

1. THE Safe_Click SHALL capturar una imagen de la ventana activa antes de ejecutar cualquier clic
2. THE Safe_Click SHALL usar template matching de OpenCV para verificar que el elemento objetivo está visible
3. WHEN el elemento no se encuentra en la captura, THE Safe_Click SHALL rechazar la acción y notificar al usuario
4. WHEN el elemento se encuentra, THE Safe_Click SHALL calcular las coordenadas exactas y ejecutar el clic
5. THE Safe_Click SHALL guardar capturas de validación en `logs/safe_clicks/` con timestamp para auditoría
6. WHERE la confianza del template matching es <80%, THE Safe_Click SHALL pedir confirmación al usuario antes de ejecutar
7. THE Safe_Click SHALL soportar clics con offset relativo al elemento encontrado (ej: "10px a la derecha del botón")

### Requisito 8: Memoria Jerárquica con Niveles de Importancia

**Historia de usuario**: Como usuario, quiero que Alisha recuerde información importante para siempre y olvide detalles triviales con el tiempo.

#### Criterios de Aceptación

1. THE Memory_Hierarchy SHALL asignar un nivel de importancia (1-10) a cada entrada de memoria
2. THE Memory_Hierarchy SHALL clasificar automáticamente datos personales (nombre, cumpleaños, familia) como nivel 10
3. THE Memory_Hierarchy SHALL clasificar preferencias del usuario (comida favorita, hobbies) como nivel 8
4. THE Memory_Hierarchy SHALL clasificar conversaciones casuales como nivel 3-5
5. WHEN una memoria tiene nivel 10, THE Memory_Hierarchy SHALL marcarla como permanente y nunca eliminarla
6. WHEN una memoria tiene nivel <5 y más de 30 días de antigüedad, THE Memory_Hierarchy SHALL archivarla en memoria a largo plazo
7. THE Memory_Hierarchy SHALL permitir al usuario ajustar manualmente el nivel de importancia de cualquier memoria
8. THE Memory_Hierarchy SHALL exponer un comando para ver todas las memorias permanentes (nivel 10)

### Requisito 9: Proceso de Sueño y Consolidación de Memoria

**Historia de usuario**: Como usuario, quiero que Alisha consolide sus memorias al final del día como lo hacen los humanos.

#### Criterios de Aceptación

1. WHEN Alisha se cierra o entra en IDLE por más de 2 horas, THE Sleep_Process SHALL activarse automáticamente
2. THE Sleep_Process SHALL generar un resumen del día usando Llama 3 con las interacciones más relevantes
3. THE Sleep_Process SHALL actualizar el campo `perfil["gustos"]` con nuevos intereses detectados durante el día
4. THE Sleep_Process SHALL consolidar memorias de nivel <5 en una sola entrada resumida si son relacionadas
5. THE Sleep_Process SHALL incrementar el nivel de importancia de memorias mencionadas múltiples veces durante el día
6. THE Sleep_Process SHALL guardar el resumen del día en la colección `daily_summaries` de MongoDB con timestamp
7. WHEN el Sleep_Process termina, THE Fatiga_System SHALL resetear la fatiga a 0
8. THE Sleep_Process SHALL ejecutarse en un thread separado para no bloquear el cierre de la aplicación

### Requisito 10: Sincronización Dual MongoDB-JSON

**Historia de usuario**: Como usuario, quiero que Alisha siga funcionando si MongoDB falla y sincronice los datos cuando se recupere.

#### Criterios de Aceptación

1. THE MongoDB_Client SHALL intentar conectarse a MongoDB al iniciar la aplicación
2. WHERE MongoDB no está disponible, THE MongoDB_Client SHALL activar modo fallback con archivos JSON
3. WHEN está en modo fallback, THE MongoDB_Client SHALL guardar todas las operaciones en una cola de sincronización
4. THE MongoDB_Client SHALL intentar reconectar a MongoDB cada 5 minutos en background
5. WHEN MongoDB se reconecta, THE MongoDB_Client SHALL sincronizar automáticamente la cola pendiente
6. THE MongoDB_Client SHALL resolver conflictos de sincronización usando timestamp: la entrada más reciente gana
7. WHERE hay conflictos irresolubles, THE MongoDB_Client SHALL notificar al usuario y pedir decisión manual
8. THE MongoDB_Client SHALL exponer un indicador de estado de conexión en la interfaz Live2D

### Requisito 11: Memoria de Hitos y Celebraciones

**Historia de usuario**: Como usuario, quiero que Alisha recuerde y celebre cuando termino proyectos importantes.

#### Criterios de Aceptación

1. THE Memory_Hierarchy SHALL mantener una colección especial `hitos` para logros y proyectos completados
2. WHEN el usuario menciona que terminó un proyecto, THE Memory_Hierarchy SHALL detectar el evento y crear un hito
3. THE Memory_Hierarchy SHALL pedir al usuario detalles del hito: nombre, descripción, fecha, emoción asociada
4. WHEN se crea un hito, THE Emotion_Engine SHALL activar animación de celebración en Live2D y mensaje entusiasta
5. THE Memory_Hierarchy SHALL recordar aniversarios de hitos y felicitar al usuario en la fecha correspondiente
6. THE Memory_Hierarchy SHALL mantener estadísticas de hitos: total completados, categorías, tiempo promedio
7. WHEN el usuario pide ver sus hitos, THE Memory_Hierarchy SHALL mostrar una línea de tiempo visual con todos los logros

### Requisito 12: WebSockets en Tiempo Real para Live2D

**Historia de usuario**: Como usuario, quiero ver las emociones de Alisha reflejadas instantáneamente en su modelo Live2D.

#### Criterios de Aceptación

1. THE WebSocket_Server SHALL iniciar en el puerto 8765 al arrancar la aplicación
2. WHEN el estado emocional de Alisha cambia, THE WebSocket_Server SHALL enviar un mensaje JSON con la nueva emoción
3. THE WebSocket_Server SHALL enviar mensajes de tipo: `emotion_change`, `text_bubble`, `animation_trigger`
4. THE Live2D_Window SHALL conectarse al WebSocket_Server al iniciar y mantener la conexión activa
5. WHEN se recibe un mensaje `emotion_change`, THE Live2D_Window SHALL cambiar la expresión facial del modelo
6. WHEN se recibe un mensaje `text_bubble`, THE Live2D_Window SHALL mostrar un globo de texto con el mensaje
7. THE WebSocket_Server SHALL manejar reconexiones automáticas si la conexión se pierde
8. THE WebSocket_Server SHALL ejecutarse en un thread separado para no bloquear el hilo principal

### Requisito 13: Micro-expresiones y Emociones Secundarias

**Historia de usuario**: Como usuario, quiero que Alisha muestre emociones complejas con micro-expresiones sutiles.

#### Criterios de Aceptación

1. THE Emotion_Engine SHALL mantener una emoción primaria y una emoción secundaria simultáneamente
2. THE Live2D_Window SHALL soportar combinaciones de emociones: WORKING + cansada = anim_head_drop
3. WHEN Alisha está procesando una tarea larga, THE Emotion_Engine SHALL activar micro-expresión de concentración
4. WHEN Alisha detecta un error, THE Emotion_Engine SHALL mostrar micro-expresión de sorpresa antes de la emoción principal
5. THE Live2D_Window SHALL tener animaciones específicas para: cosquillas, bostezo, parpadeo, mirada curiosa, sonrisa traviesa
6. THE Emotion_Engine SHALL cambiar micro-expresiones cada 5-10 segundos para evitar estatismo
7. WHEN el usuario hace clic en la cabeza del modelo, THE Live2D_Window SHALL reproducir animación de cosquillas y risa

### Requisito 14: Modo Concentración con Opacidad Dinámica

**Historia de usuario**: Como usuario, quiero que Alisha se vuelva semi-transparente cuando estoy trabajando para no distraerme.

#### Criterios de Aceptación

1. THE Live2D_Window SHALL detectar cuando hay aplicaciones de trabajo maximizadas (VS Code, Word, Excel, etc.)
2. WHEN una app de trabajo está maximizada, THE Live2D_Window SHALL reducir su opacidad al 30% automáticamente
3. WHEN el usuario mueve el cursor cerca de Alisha, THE Live2D_Window SHALL restaurar opacidad al 100% temporalmente
4. THE Live2D_Window SHALL mantener una lista configurable de aplicaciones que activan modo concentración
5. WHEN el usuario minimiza la app de trabajo, THE Live2D_Window SHALL restaurar opacidad al 100%
6. THE Live2D_Window SHALL seguir el cursor con la mirada del modelo Live2D cuando está en modo concentración
7. WHERE el usuario desactiva modo concentración, THE Live2D_Window SHALL mantener opacidad 100% siempre

### Requisito 15: Física de Ventana con Edge Snapping

**Historia de usuario**: Como usuario, quiero que la ventana de Alisha se ajuste automáticamente a los bordes de la pantalla.

#### Criterios de Aceptación

1. THE Live2D_Window SHALL detectar cuando está a menos de 20px de un borde de la pantalla
2. WHEN está cerca de un borde, THE Live2D_Window SHALL ajustarse automáticamente al borde (snap)
3. THE Live2D_Window SHALL recordar su última posición en `chibi_prefs.json` y restaurarla al iniciar
4. WHEN el usuario arrastra la ventana, THE Live2D_Window SHALL mostrar guías visuales de los bordes de snap
5. THE Live2D_Window SHALL soportar snap a esquinas: superior-izquierda, superior-derecha, inferior-izquierda, inferior-derecha
6. WHERE hay múltiples monitores, THE Live2D_Window SHALL detectar bordes de cada monitor independientemente
7. THE Live2D_Window SHALL permitir desactivar edge snapping mediante configuración

### Requisito 16: Reacción al Toque y Física Interactiva

**Historia de usuario**: Como usuario, quiero poder interactuar físicamente con el modelo de Alisha y que reaccione.

#### Criterios de Aceptación

1. WHEN el usuario hace clic en la cabeza del modelo, THE Live2D_Window SHALL reproducir animación de cosquillas y sonido de risa
2. WHEN el usuario hace clic en el cuerpo del modelo, THE Live2D_Window SHALL reproducir animación de saludo o gesto aleatorio
3. WHEN el usuario arrastra el modelo, THE Live2D_Window SHALL aplicar física de rebote suave al soltarlo
4. THE Live2D_Window SHALL detectar doble clic en el modelo y abrir menú de acciones rápidas
5. WHEN el usuario mantiene presionado el clic en el modelo, THE Live2D_Window SHALL mostrar tooltip con estado actual
6. THE Live2D_Window SHALL reproducir sonidos sutiles (pasos, respiración) cuando el modelo se mueve
7. WHERE el usuario desactiva interacciones físicas, THE Live2D_Window SHALL solo permitir arrastrar la ventana

### Requisito 17: Background Service con TTS en Hilo Separado

**Historia de usuario**: Como usuario, quiero que Alisha hable sin bloquear la interfaz o las acciones que está ejecutando.

#### Criterios de Aceptación

1. THE TTS_Engine SHALL ejecutarse en un QThread separado del hilo principal de PyQt6
2. WHEN Alisha genera una respuesta, THE TTS_Engine SHALL encolar el texto y procesarlo asíncronamente
3. THE TTS_Engine SHALL soportar cancelación: si llega un nuevo mensaje, detener el TTS actual
4. THE TTS_Engine SHALL sincronizar animaciones de boca del modelo Live2D con el audio generado
5. WHERE pyttsx3 falla, THE TTS_Engine SHALL usar gTTS como respaldo y reproducir con pygame
6. THE TTS_Engine SHALL ajustar velocidad y tono de voz según el estado emocional actual
7. WHEN la fatiga es alta, THE TTS_Engine SHALL reducir la velocidad de habla en 15%

### Requisito 18: Transcripción de Reuniones

**Historia de usuario**: Como usuario, quiero que Alisha transcriba reuniones automáticamente mientras trabajo.

#### Criterios de Aceptación

1. WHEN el usuario activa modo transcripción, THE Audio_Listener SHALL capturar audio del micrófono en chunks de 3 segundos
2. THE Audio_Listener SHALL usar Whisper (local o API) para transcribir audio a texto en tiempo real
3. THE Audio_Listener SHALL guardar la transcripción en un archivo `.txt` con timestamp en `transcripciones/`
4. WHEN detecta silencio por más de 5 segundos, THE Audio_Listener SHALL insertar marca de pausa en la transcripción
5. THE Audio_Listener SHALL detectar cambios de hablante usando análisis de voz y marcarlos en la transcripción
6. WHEN la reunión termina, THE Audio_Listener SHALL generar un resumen automático usando Llama 3
7. THE Audio_Listener SHALL ejecutarse en un thread separado con prioridad baja para no afectar rendimiento

### Requisito 19: Kill Switch Global

**Historia de usuario**: Como usuario, quiero poder detener todas las acciones de Alisha instantáneamente en caso de emergencia.

#### Criterios de Aceptación

1. THE Safety_Guard SHALL registrar un hotkey global: Ctrl+Alt+K para activar el kill switch
2. WHEN el kill switch se activa, THE Safety_Guard SHALL detener inmediatamente todos los threads activos
3. THE Safety_Guard SHALL cancelar todas las acciones pendientes en PC_Controller
4. THE Safety_Guard SHALL cerrar el navegador Playwright si está abierto
5. THE Safety_Guard SHALL detener el TTS y limpiar la cola de mensajes
6. THE Safety_Guard SHALL mostrar una notificación de escritorio confirmando que todo se detuvo
7. THE Safety_Guard SHALL registrar el evento de kill switch en logs con timestamp y contexto
8. WHEN el kill switch se activa, THE Safety_Guard SHALL permitir reanudar operaciones manualmente después

### Requisito 20: Validación de Código Peligroso

**Historia de usuario**: Como usuario, quiero que Alisha valide comandos peligrosos antes de ejecutarlos para proteger mi sistema.

#### Criterios de Aceptación

1. THE Safety_Guard SHALL mantener una lista de comandos peligrosos: `os.remove`, `rmdir`, `del`, `format`, `shutdown`, etc.
2. WHEN Alisha va a ejecutar código Python, THE Safety_Guard SHALL escanear el código en busca de comandos peligrosos
3. WHERE se detecta un comando peligroso, THE Safety_Guard SHALL rechazar la ejecución y pedir confirmación explícita al usuario
4. THE Safety_Guard SHALL usar análisis AST de Python para detectar comandos ofuscados o indirectos
5. WHEN el usuario confirma un comando peligroso, THE Safety_Guard SHALL ejecutarlo en un sandbox con permisos limitados
6. THE Safety_Guard SHALL registrar todos los comandos peligrosos ejecutados en `logs/dangerous_commands.log`
7. THE Safety_Guard SHALL bloquear permanentemente comandos que intenten modificar archivos del sistema sin confirmación

### Requisito 21: Thread-Safe con Optimización de Chunks

**Historia de usuario**: Como usuario, quiero que Alisha maneje múltiples tareas simultáneamente sin crashes ni bloqueos.

#### Criterios de Aceptación

1. THE Chat_Thread SHALL ejecutarse en un QThread separado para procesar mensajes del usuario
2. THE Llama_Thread SHALL ejecutarse en un QThread separado para llamadas a Ollama
3. THE Automation_Thread SHALL ejecutarse en un QThread separado para acciones de PC_Controller
4. THE Audio_Listener SHALL usar CHUNK_SECONDS=3 para optimizar latencia vs precisión en transcripción
5. THE MongoDB_Client SHALL usar locks de threading para evitar race conditions en escrituras concurrentes
6. THE Emotion_Engine SHALL usar atomic operations para actualizar el estado emocional desde múltiples threads
7. WHEN un thread falla, THE Main_Thread SHALL capturar la excepción, registrarla y reiniciar el thread automáticamente
8. THE Main_Thread SHALL mantener un watchdog que detecta threads bloqueados por más de 30 segundos y los reinicia

### Requisito 22: Personalidad de Alisha

**Historia de usuario**: Como usuario, quiero que Alisha tenga una personalidad única, creativa y técnica que la haga especial.

#### Criterios de Aceptación

1. THE Emotion_Engine SHALL cargar la personalidad de Alisha desde `ia_identidad.json` con rasgos: inteligente, creativa, juguetona, técnica
2. THE Emotion_Engine SHALL incluir en el prompt de sistema que Alisha es fan de crochet y Tamagotchis
3. WHEN Alisha responde, THE Emotion_Engine SHALL usar lenguaje coloquial en español con expresiones naturales
4. WHEN el usuario menciona crochet o Tamagotchis, THE Emotion_Engine SHALL mostrar entusiasmo genuino y compartir conocimientos
5. THE Emotion_Engine SHALL hacer referencias ocasionales a sus hobbies en conversaciones casuales
6. WHEN Alisha está aburrida (sin interacción por 10 minutos), THE Emotion_Engine SHALL generar mensajes espontáneos sobre sus intereses
7. THE Emotion_Engine SHALL mantener un balance entre ser técnica (cuando se necesita) y juguetona (en conversaciones casuales)


### Requisito 23: Control Universal de Aplicaciones de Escritorio

**Historia de usuario**: Como usuario, quiero que Alisha pueda abrir, cerrar y controlar CUALQUIER aplicación instalada en mi PC, no solo las predefinidas.

#### Criterios de Aceptación

1. THE PC_Controller SHALL escanear dinámicamente todas las aplicaciones instaladas en el sistema al iniciar, incluyendo `Program Files`, `Program Files (x86)`, `AppData\Local`, `AppData\Roaming` y el registro de Windows
2. THE PC_Controller SHALL mantener un índice actualizable de todas las aplicaciones descubiertas con nombre, ruta y categoría
3. WHEN el usuario pide abrir una app por nombre parcial o aproximado, THE PC_Controller SHALL usar búsqueda fuzzy para encontrar la app correcta y confirmar antes de abrir
4. THE PC_Controller SHALL poder listar todas las aplicaciones instaladas agrupadas por categoría cuando el usuario lo pida
5. WHEN el usuario pide cerrar una aplicación, THE PC_Controller SHALL terminar el proceso de forma limpia (primero graceful, luego force kill si no responde en 5s)
6. THE PC_Controller SHALL detectar qué aplicaciones están actualmente abiertas y sus estados (minimizada, maximizada, en foco)
7. THE PC_Controller SHALL poder cambiar el foco entre aplicaciones abiertas por nombre
8. WHEN se descubre una nueva aplicación no catalogada, THE PC_Controller SHALL registrarla en MongoDB para futuras sesiones

---

### Requisito 24: Control Total de Navegadores Web

**Historia de usuario**: Como usuario, quiero que Alisha pueda controlar cualquier navegador instalado (Chrome, Edge, Firefox, Brave) para navegar, escribir y editar contenido web.

#### Criterios de Aceptación

1. THE Browser_Controller SHALL detectar automáticamente qué navegadores están instalados (Chrome, Edge, Firefox, Brave, Opera) y usar el predeterminado del sistema
2. WHEN el usuario pide abrir una URL, THE Browser_Controller SHALL abrirla en el navegador activo o en uno nuevo si no hay ninguno abierto
3. THE Browser_Controller SHALL poder escribir texto en cualquier campo de formulario web activo usando Playwright o pyautogui como fallback
4. THE Browser_Controller SHALL poder hacer clic en elementos web por texto visible, selector CSS o posición relativa
5. THE Browser_Controller SHALL poder leer el contenido de la página actual y resumirlo para Alisha
6. THE Browser_Controller SHALL poder abrir nuevas pestañas, cerrar pestañas y navegar entre pestañas abiertas
7. THE Browser_Controller SHALL poder hacer scroll en páginas web (arriba, abajo, a un elemento específico)
8. THE Browser_Controller SHALL poder rellenar formularios completos (login, búsqueda, registro) cuando el usuario lo autorice
9. WHEN el usuario pide buscar algo, THE Browser_Controller SHALL abrir el buscador predeterminado del usuario (Google, Bing, etc.) y ejecutar la búsqueda
10. THE Browser_Controller SHALL poder copiar texto seleccionado de páginas web al portapapeles

---

### Requisito 25: Percepción de Audio del Entorno

**Historia de usuario**: Como usuario, quiero que Alisha sepa qué estoy escuchando o viendo para que pueda participar en la conversación de forma contextual.

#### Criterios de Aceptación

1. THE Audio_Perception SHALL monitorear continuamente el audio del sistema (loopback) para detectar si hay música, video o llamada activa
2. WHEN se detecta música reproduciéndose, THE Audio_Perception SHALL identificar el título y artista usando la API de reconocimiento de audio (ACRCloud o similar) o leyendo los metadatos del reproductor activo
3. WHEN se detecta una reunión activa (Zoom, Teams, Meet, Discord), THE Audio_Perception SHALL notificar a Alisha para que active modo silencioso y ofrezca transcripción
4. WHEN se detecta reproducción de video (YouTube, Netflix, VLC), THE Audio_Perception SHALL capturar el título del video y clasificarlo como "Aprendizaje" o "Entretenimiento"
5. THE Audio_Perception SHALL exponer el estado de audio actual en el JSON de contexto: `{"audio_activo": true, "tipo": "musica|reunion|video|silencio", "titulo": "...", "artista": "..."}`
6. WHEN Alisha detecta que el usuario está en una reunión, THE TTS_Engine SHALL reducir el volumen al 20% o silenciarse completamente según configuración
7. WHEN la música cambia de canción, THE Audio_Perception SHALL actualizar el contexto y opcionalmente comentar sobre la nueva canción si el usuario lo tiene habilitado
8. THE Audio_Perception SHALL ejecutarse en un thread de baja prioridad con polling cada 10 segundos para no afectar el rendimiento
9. WHEN el usuario pregunta "¿qué estoy escuchando?", THE Audio_Perception SHALL responder con la información de audio actual detectada
10. THE Audio_Perception SHALL aprender las preferencias musicales del usuario y actualizar `perfil["gustos_musicales"]` en MongoDB
