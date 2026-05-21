# Requirements Document

## Introduction

Este documento describe las mejoras incrementales sobre el proyecto **Alisha IA** — un asistente de escritorio con avatar Live2D, backend Flask/SocketIO, TTS neuronal y múltiples módulos de IA. Las mejoras están diseñadas para no romper la funcionalidad existente y se aplican sobre los archivos clave: `cabina_virtual.py`, `tts_engine.py`, `mongodb_client.py`, `memory_db.py`, `document_intelligence.py`, `tools.py`, `agent_loop.py` y `brain.py`.

Las cinco áreas de mejora son:
1. **Avatar fluido y orgánico** — movimientos suavizados, micro-variaciones naturales
2. **Sincronización de voz (Lip-Sync)** — boca proporcional al volumen real del audio
3. **Estructura de Historial y Archivos** — sesiones limpias en MongoDB, PDFs con Gemini Vision
4. **Automatización y Control** — Function Calling estructurado con confirmación visual
5. **Modo Híbrido Offline/Online** — alternancia automática Gemini/Ollama, ventana nativa

---

## Glossary

- **Avatar_Engine**: el motor de renderizado Live2D en `cabina_virtual.py` que controla los parámetros del modelo IceGirl.
- **Lerp**: interpolación lineal entre dos valores — `a + (b - a) * t`.
- **SmoothDamp**: algoritmo de amortiguación estilo Unity que converge sin oscilación.
- **ParamMouthOpen**: parámetro Live2D que controla la apertura de la boca (rango 0.0–1.0).
- **mouth_amplitude**: campo en `chibi_state.json` que comunica la amplitud de boca entre procesos.
- **TTS_Engine**: el motor de síntesis de voz en `tts_engine.py` (edge-tts / ElevenLabs / pyttsx3).
- **Lip_Sync_Thread**: hilo daemon que emite valores de `mouth_amplitude` durante la reproducción de audio.
- **RMS**: Root Mean Square — medida de energía de una señal de audio.
- **SmartRouter**: componente en `brain.py` que decide qué motor de IA usar según el contexto.
- **MongoDB_Client**: el cliente singleton en `mongodb_client.py` con auto-healing y reintentos.
- **MemoryDB**: la base de datos SQLite en `memory_db.py` con fallback a JSON.
- **Tool**: clase base en `tools.py` que representa una herramienta ejecutable por Alisha.
- **Safety_Guard**: módulo `safety_guard.py` que verifica acciones críticas antes de ejecutarlas.
- **chibi_state.json**: archivo JSON en `DATA_DIR` que actúa como canal de comunicación entre procesos.
- **GLFW_Time**: tiempo en segundos retornado por `glfw.get_time()` — base para animaciones.
- **Connectivity_Checker**: componente nuevo en `brain.py` que detecta disponibilidad de internet.
- **Native_Window**: ventana de escritorio nativa (usando `pywebview`) que reemplaza `webbrowser.open()`.
- **Session_ID**: identificador entero de sesión de chat, almacenado en `sesiones` (SQLite) y en documentos MongoDB.

---

## Requirements

---

### Requirement 1: Avatar Fluido — Suavizado de Parámetros Live2D

**User Story:** Como usuaria, quiero que el avatar de Alisha se mueva de forma fluida y orgánica, sin saltos ni movimientos robóticos, para que la experiencia visual sea natural y agradable.

#### Acceptance Criteria

1. WHEN el Avatar_Engine actualiza un parámetro Live2D en cada frame, THE Avatar_Engine SHALL aplicar SmoothDamp con `smooth_time` configurable (valor por defecto: 0.12 segundos) en lugar de asignación directa.

2. WHEN la diferencia entre el valor actual y el valor objetivo de cualquier parámetro Live2D supera 0.01, THE Avatar_Engine SHALL garantizar que el cambio por frame no exceda `max_speed * dt` (donde `max_speed` por defecto es 8.0 unidades/segundo).

3. WHILE el avatar está en estado idle — definido como: el flag `hablando` es `False` Y han transcurrido al menos 2.0 segundos desde la última interacción del usuario — THE Avatar_Engine SHALL aplicar micro-variaciones continuas a los parámetros de respiración (`ParamBreath`) y mirada (`ParamEyeBallX`, `ParamEyeBallY`) usando funciones seno basadas en `GLFW_Time` con amplitudes entre 0.02 y 0.15 unidades; IF el flag `hablando` es `True` o IF han transcurrido menos de 2.0 segundos desde la última interacción, THEN THE Avatar_Engine SHALL congelar esos parámetros en su último valor calculado sin aplicar nuevas variaciones.

4. WHEN el Avatar_Engine calcula micro-variaciones de respiración, THE Avatar_Engine SHALL usar una frecuencia base de 0.18 Hz (ciclo de ~5.5 segundos) con un desplazamiento de fase generado aleatoriamente en el rango [0, 2π) radianes una única vez al inicio de cada sesión.

5. WHEN el Avatar_Engine calcula micro-variaciones de mirada, THE Avatar_Engine SHALL combinar exactamente dos frecuencias que difieran en al menos 0.01 Hz (ej: 0.07 Hz y 0.13 Hz) para producir una señal que no se repita dentro de una ventana de 60 segundos.

6. THE Avatar_Engine SHALL mantener todos los valores de parámetros Live2D dentro del rango mínimo y máximo declarado por la definición del parámetro en el modelo cargado, aplicando clamp antes de cada llamada a `SetParameterValue`.

7. IF el modelo Live2D no está cargado o `live2d.v3` lanza una excepción al actualizar un parámetro, THEN THE Avatar_Engine SHALL capturar la excepción, registrarla en stdout con prefijo `[Avatar]` y continuar el loop sin interrumpir el renderizado.

---

### Requirement 2: Micro-Variaciones Orgánicas — Balanceo Corporal

**User Story:** Como usuaria, quiero que el cuerpo del avatar tenga un balanceo sutil y continuo que refleje el estado emocional de Alisha, para que se sienta viva incluso cuando no está hablando.

#### Acceptance Criteria

1. WHILE el avatar está activo y `flow ∈ [0.0, 1.0]` y `dopamina ∈ [0.0, 1.0]`, THE Avatar_Engine SHALL calcular la amplitud del balanceo corporal (`ParamBodyAngleZ`) usando la fórmula `amplitud = 1.5 + flow * 2.0 + dopamina * 0.8`, aplicando clamp al resultado en el rango [1.5, 5.0] antes de asignarlo al parámetro.

2. WHILE el avatar está activo y `flow ∈ [0.0, 1.0]`, THE Avatar_Engine SHALL calcular la velocidad del balanceo usando la fórmula `velocidad = 0.20 + flow * 0.25` Hz, con resultado garantizado en el rango [0.20, 0.45] Hz.

3. WHEN el estado emocional cambia, THE Avatar_Engine SHALL hacer una transición suave del balanceo usando Lerp con factor `t = dt * 2.0` por frame, garantizando que el delta de amplitud entre frames consecutivos no exceda 0.15 unidades.

4. THE Avatar_Engine SHALL garantizar que `amplitud_balanceo()` retorne siempre un valor en el rango [1.5, 5.0] para cualquier combinación de `flow ∈ [0.0, 1.0]` y `dopamina ∈ [0.0, 1.0]`, aplicando un clamp al resultado de la fórmula antes de retornarlo.

---

### Requirement 3: Corrección de Mezcla de Texturas OpenGL

**User Story:** Como usuaria, quiero que el avatar no tenga partes que se transparenten incorrectamente (especialmente las mangas y bordes blancos), para que el modelo se vea limpio sobre cualquier fondo.

#### Acceptance Criteria

1. WHEN el Avatar_Engine inicializa la ventana GLFW, THE Avatar_Engine SHALL configurar el color key con los valores exactos R=0, G=255, B=0 (COLORREF `0x0000FF00`) via `SetLayeredWindowAttributes` con flag `LWA_COLORKEY`.

2. IF `SetLayeredWindowAttributes` retorna 0 (fallo) durante la inicialización, THEN THE Avatar_Engine SHALL registrar el error en stdout con prefijo `[Avatar] Error color key:` y abortar la inicialización de la ventana sin continuar el loop de renderizado.

3. WHEN el Avatar_Engine renderiza el modelo Live2D, THE Avatar_Engine SHALL limpiar el framebuffer con color verde puro `(0.0, 1.0, 0.0, 1.0)` antes de cada frame para garantizar que las zonas sin modelo sean transparentes.

4. WHEN el Avatar_Engine evalúa si el píxel bajo el cursor es transparente, THE Avatar_Engine SHALL clasificar el píxel como "zona transparente" si y solo si: `r < 30 AND g ∈ [225, 255] AND b < 30`; si la condición se cumple, THE Avatar_Engine SHALL activar el modo click-through; si no se cumple, THE Avatar_Engine SHALL desactivar el modo click-through.

5. IF `glReadPixels` lanza una excepción durante la evaluación de click-through, THEN THE Avatar_Engine SHALL mantener el estado de click-through anterior (activado o desactivado) sin modificarlo, hasta que `glReadPixels` tenga éxito en un frame posterior.

---

### Requirement 4: Lip-Sync — Amplitud Proporcional al Volumen Real

**User Story:** Como usuaria, quiero que la boca del avatar se abra de forma proporcional al volumen real del audio generado por TTS, para que el lip-sync se vea natural y sincronizado.

#### Acceptance Criteria

1. WHEN el TTS_Engine genera audio MP3, THE TTS_Engine SHALL pre-calcular un array de amplitudes RMS usando `numpy` con chunks de 40ms (25 fps) antes de iniciar la reproducción.

2. WHEN el TTS_Engine calcula la amplitud RMS de un chunk de audio, THE TTS_Engine SHALL normalizar el valor al rango [0.0, 1.0] usando la fórmula `amp = min(1.0, rms / 8000.0)`, donde 8000.0 es el valor de normalización calibrado para edge-tts.

3. WHILE el audio está reproduciéndose, THE Lip_Sync_Thread SHALL escribir `mouth_amplitude` en `chibi_state.json` con una frecuencia de 25 Hz (cada 40ms).

4. WHEN el audio termina o WHEN se recibe una señal de stop, THE TTS_Engine SHALL emitir `mouth_amplitude = 0.0` dentro de los 40ms siguientes al evento de cierre.

5. IF `pydub` o `numpy` no están disponibles, THEN THE TTS_Engine SHALL usar una animación sinusoidal de fallback con el valor exacto calculado por la fórmula: `amp = abs(sin(t * 8.0)) * 0.6 + 0.1` donde `t` es el tiempo en segundos desde el inicio de la reproducción.

6. WHERE el lip-sync está activo y el audio está reproduciéndose, WHEN el TTS_Engine inicia la reproducción, THE TTS_Engine SHALL iniciar el Lip_Sync_Thread dentro de los 40ms siguientes al inicio de la reproducción.

7. THE TTS_Engine SHALL garantizar que todos los valores emitidos de `mouth_amplitude` estén en el rango [0.0, 1.0].

8. IF la escritura en `chibi_state.json` lanza una excepción durante el Lip_Sync_Thread, THEN THE TTS_Engine SHALL continuar la reproducción de audio sin interrumpirla, descartando silenciosamente el valor de amplitud que no pudo escribirse.

---

### Requirement 5: Lip-Sync — Lectura en cabina_virtual.py sin Latencia

**User Story:** Como usuaria, quiero que el avatar lea el valor de `mouth_amplitude` desde `chibi_state.json` con la menor latencia posible, para que el movimiento de boca esté sincronizado con el audio.

#### Acceptance Criteria

1. WHEN el Avatar_Engine lee `chibi_state.json` en cada frame, THE Avatar_Engine SHALL aplicar Lerp al parámetro `ParamMouthOpen` con factor `t = min(1.0, dt * 20.0)` para suavizar la transición entre valores discretos de 40ms.

2. WHEN el Avatar_Engine lee `mouth_amplitude` desde `chibi_state.json`, THE Avatar_Engine SHALL usar el valor directamente como target de `ParamMouthOpen` sin escalar, ya que el rango [0.0, 1.0] es compatible con el parámetro Live2D.

3. IF `chibi_state.json` no existe o contiene JSON inválido cuando el Avatar_Engine intenta leerlo, THEN THE Avatar_Engine SHALL usar `mouth_amplitude = 0.0` como valor target y dejar que `ParamMouthOpen` converja gradualmente a 0.0 usando el mecanismo de Lerp normal, sin lanzar excepción.

4. THE Avatar_Engine SHALL leer `chibi_state.json` como máximo una vez por frame (60 fps) para evitar contención de I/O con el Lip_Sync_Thread.

---

### Requirement 6: Historial de Conversaciones por Sesión en MongoDB

**User Story:** Como usuaria, quiero que el historial de conversaciones esté organizado por sesiones en MongoDB, para poder revisar conversaciones anteriores de forma ordenada.

#### Acceptance Criteria

1. THE MongoDB_Client SHALL almacenar todos los mensajes de conversación en la colección `"conversaciones"` con los campos: `session_id` (int), `timestamp` (ISO 8601), `entrada` (str, máx. 10.000 chars), `respuesta` (str, máx. 10.000 chars), `estado_emocional` (str, uno de: `"alegría"`, `"entusiasmo"`, `"curiosidad"`, `"preocupación"`, `"frustración"`, `"cansancio"`, `"nostalgia"`, `"neutral"`).

2. WHEN se inicia una nueva sesión de chat, THE MemoryDB SHALL crear un registro en la tabla `sesiones` de SQLite y retornar un `Session_ID` entero en el rango [1, 2.147.483.647] que se usará para agrupar todos los mensajes de esa sesión.

3. WHEN se guarda un mensaje de conversación, THE MongoDB_Client SHALL incluir el `Session_ID` activo en el documento, de forma que todos los mensajes de una sesión compartan el mismo `session_id`.

4. WHEN se consulta el historial de una sesión, THE MongoDB_Client SHALL retornar únicamente los documentos de la colección `"conversaciones"` que tengan el `session_id` solicitado, ordenados por `timestamp` ascendente.

5. IF MongoDB Atlas no está disponible, THEN THE MemoryDB SHALL persistir el mensaje en SQLite con el mismo `session_id`, de forma que el mensaje sea recuperable mediante `load_by_session(session_id)` sin retornar error.

6. WHEN el MongoDB_Client se inicializa y el índice `{session_id: 1, timestamp: 1}` no existe en la colección `"conversaciones"`, THE MongoDB_Client SHALL crear dicho índice compuesto.

---

### Requirement 7: Procesamiento de PDFs Locales con Gemini Vision

**User Story:** Como usuaria, quiero que Alisha pueda procesar PDFs locales extrayendo tanto texto como imágenes, para que pueda analizar documentos completos incluyendo gráficos y tablas.

#### Acceptance Criteria

1. WHEN el DocumentIntelligence recibe la ruta de un archivo PDF, THE DocumentIntelligence SHALL extraer el texto de cada página usando `PyMuPDF` (`fitz`) con el método `page.get_text()`.

2. WHEN una página de PDF contiene una o más imágenes y `GeminiVision` está disponible, THE DocumentIntelligence SHALL extraer cada imagen usando `page.get_images()` y enviarla a `GeminiVision`, obteniendo una descripción textual por imagen.

3. WHEN el DocumentIntelligence combina el contenido de una página, THE DocumentIntelligence SHALL concatenar el texto extraído (si no es cadena vacía) con las descripciones de imágenes disponibles; IF el texto extraído es cadena vacía, THEN solo se incluirán las descripciones de imágenes con el formato `[Imagen {n}]\n{descripcion}`.

4. IF `PyMuPDF` no está instalado, THEN THE DocumentIntelligence SHALL usar el método `analizar_documento()` de `file_analyzer.py` como fallback sin lanzar excepción.

5. IF `GeminiVision` no está disponible o lanza excepción al procesar una imagen, THEN THE DocumentIntelligence SHALL incluir el placeholder `[Imagen {n}: no disponible]` en el contenido y continuar procesando las páginas e imágenes restantes del documento.

6. THE DocumentIntelligence SHALL truncar el contenido total combinado a 15.000 caracteres, descartando el contenido que exceda ese límite.

7. IF la ruta del archivo PDF no existe o no es accesible, THEN THE DocumentIntelligence SHALL retornar una cadena con el formato `[Error: archivo no encontrado o inaccesible: {ruta}]` sin lanzar excepción.

---

### Requirement 8: Function Calling Estructurado sin Coordenadas Ciegas

**User Story:** Como usuaria, quiero que Alisha use Function Calling estructurado con parámetros explícitos para controlar el sistema, en lugar de intentar adivinar coordenadas del mouse, para que las acciones sean confiables y predecibles.

#### Acceptance Criteria

1. THE Tool SHALL definir sus parámetros usando nombres semánticos explícitos (ej: `app`, `proceso`, `ruta`, `accion`) y nunca aceptar parámetros de coordenadas absolutas (`x`, `y`, `pos_x`, `pos_y`) como entrada directa del LLM; IF el LLM pasa un parámetro de coordenada, THEN THE Tool SHALL ignorarlo y retornar un mensaje indicando que las coordenadas no son un parámetro válido.

2. WHEN el LLM solicita ejecutar una herramienta, THE agent_loop SHALL parsear el nombre de la herramienta y sus parámetros desde el texto de respuesta del LLM usando el formato `TOOL_CALL: nombre(param1=valor1, param2=valor2)`; IF el formato no coincide, THEN THE agent_loop SHALL omitir la ejecución y continuar sin lanzar excepción.

3. WHEN una Tool tiene `critica=True`, THE ejecutar_herramienta SHALL invocar el `confirmar_callback` con un mensaje que incluya el nombre de la herramienta y los valores de sus parámetros antes de ejecutarla, y SHALL bloquear la ejecución si el callback retorna `False`.

4. IF el Safety_Guard verifica una acción y la ruta o proceso coincide exactamente con una entrada de las listas de rutas del sistema operativo protegidas o procesos protegidos (ambas listas definidas explícitamente en `safety_guard.py`), THEN THE Safety_Guard SHALL retornar `(False, razon)`; rutas que no coincidan exactamente con esas listas no serán bloqueadas.

5. IF el LLM genera un `TOOL_CALL` con un nombre de herramienta desconocido, THEN THE ejecutar_herramienta SHALL retornar el mensaje `"Che, no conozco la herramienta '{nombre}'. ¿Está bien escrito?"` sin lanzar excepción.

6. WHEN una herramienta se ejecuta, THE Tool SHALL completar su ejecución o lanzar excepción dentro de 30 segundos; IF el timeout se excede, THEN THE ejecutar_herramienta SHALL retornar un mensaje en voseo rioplatense que nombre la herramienta e indique que fue cancelada, sin lanzar excepción.

---

### Requirement 9: Detección de Conectividad para Alternancia Gemini/Ollama

**User Story:** Como usuaria, quiero que Alisha cambie automáticamente entre Gemini (con internet) y Ollama (sin internet) sin que yo tenga que hacer nada, para que siempre tenga una respuesta disponible.

#### Acceptance Criteria

1. THE Connectivity_Checker SHALL verificar la disponibilidad de internet intentando una conexión TCP a `8.8.8.8:53` con timeout de 2 segundos, sin depender de requests HTTP.

2. WHEN el SmartRouter selecciona un motor de IA, THE SmartRouter SHALL consultar al Connectivity_Checker antes de seleccionar Gemini o Groq; IF `Connectivity_Checker.is_online()` retorna `False`, THEN THE SmartRouter SHALL seleccionar Ollama independientemente del contenido de la consulta.

3. WHEN el Connectivity_Checker detecta que el estado de conectividad cambió respecto al estado anterior (de online a offline o viceversa), THE SmartRouter SHALL registrar el cambio en stdout con el formato `[SmartRouter] Conectividad: {online|offline}`; si el estado no cambió, no se registra nada.

4. THE Connectivity_Checker SHALL cachear el resultado de la última verificación durante 30 segundos; durante ese período, `is_online()` retornará el valor cacheado sin realizar una nueva conexión TCP.

5. IF Gemini lanza una excepción de red durante la generación de una respuesta, THEN THE SmartRouter SHALL marcar Gemini como no disponible durante 60 segundos y reenviar la consulta a Ollama en el mismo turno, independientemente del estado de `Connectivity_Checker`.

6. WHEN Ollama no está disponible localmente (conexión a `localhost:11434` rechazada o timeout), THE SmartRouter SHALL retornar un mensaje de fallback en voseo rioplatense indicando que no hay conexión disponible, sin lanzar excepción.

---

### Requirement 10: Ventana Nativa de Escritorio sin Navegador

**User Story:** Como usuaria, quiero que la interfaz de chat de Alisha se abra en una ventana nativa de escritorio en lugar de en el navegador, para tener una experiencia más integrada y sin barras de navegador.

#### Acceptance Criteria

1. WHEN Alisha inicia la interfaz de chat y `pywebview` está instalado, THE Native_Window SHALL abrir la URL `http://localhost:5000` en una ventana nativa usando `pywebview.create_window()` en lugar de `webbrowser.open()`.

2. IF `pywebview` no está instalado cuando Alisha inicia la interfaz de chat, THEN THE Native_Window SHALL usar `webbrowser.open("http://localhost:5000")` como fallback e imprimir en stdout: `[Chat] pywebview no disponible — abriendo en navegador`.

3. WHEN la Native_Window se crea con `pywebview`, THE Native_Window SHALL configurarse con los parámetros: `title="Alisha IA"`, `frameless=False`, y sin barra de navegación ni barra de dirección visibles.

4. IF el servidor Flask no está disponible en `localhost:5000` después de 15 segundos de espera, THEN THE Native_Window SHALL imprimir en stdout `[Chat] Servidor no disponible tras 15s` y retornar sin lanzar excepción; IF cualquier otro error ocurre durante la creación de la ventana, THEN THE Native_Window SHALL imprimir el mensaje de error en stdout y retornar sin lanzar excepción.

5. THE Native_Window SHALL ejecutarse en un hilo daemon separado para no bloquear el loop de renderizado GLFW de `cabina_virtual.py`.

---

## Propiedades de Corrección

### P1 — SmoothDamp converge sin oscilación

Para cualquier valor inicial `current`, valor objetivo `target`, velocidad inicial `vel=[0.0]`, `smooth_time=0.12` y `dt=0.016` (60fps):
- Después de aplicar SmoothDamp repetidamente, `current` debe converger a `target` en menos de 120 frames.
- El valor de salida nunca debe superar `target` si `current < target` (sin overshoot).

```python
# Propiedad: SmoothDamp converge sin overshoot
from hypothesis import given, strategies as st
from cabina_virtual import smooth_damp

@given(
    current=st.floats(min_value=-1.0, max_value=1.0),
    target=st.floats(min_value=-1.0, max_value=1.0),
)
def test_smooth_damp_converges(current, target):
    vel = [0.0]
    for _ in range(120):  # 2 segundos a 60fps
        current = smooth_damp(current, target, vel, 0.12, 0.016)
    assert abs(current - target) < 0.001
```

### P2 — Amplitud de boca siempre en rango [0.0, 1.0]

Para cualquier array de samples de audio (numpy float32), el valor de `mouth_amplitude` calculado por el TTS_Engine debe estar siempre en [0.0, 1.0]:

```python
# Propiedad: normalización RMS produce valores en rango válido
from hypothesis import given, strategies as st
import numpy as np

@given(st.lists(st.floats(min_value=-32768.0, max_value=32767.0), min_size=1, max_size=1000))
def test_mouth_amplitude_range(samples):
    arr = np.array(samples, dtype=np.float32)
    rms = float(np.sqrt(np.mean(arr ** 2)))
    amp = min(1.0, rms / 8000.0)
    assert 0.0 <= amp <= 1.0
```

### P3 — Amplitud de balanceo siempre en rango [1.5, 5.0]

Para cualquier valor de `flow` en [0.0, 1.0] y `dopamina` en [0.0, 1.0]:

```python
# Propiedad: amplitud_balanceo siempre en rango válido
from hypothesis import given, strategies as st
from cabina_virtual import EstadoInterno

@given(
    flow=st.floats(min_value=0.0, max_value=1.0),
    dopamina=st.floats(min_value=0.0, max_value=1.0),
)
def test_amplitud_balanceo_range(flow, dopamina):
    ei = EstadoInterno()
    ei.flow = flow
    ei.dopamina = dopamina
    amp = ei.amplitud_balanceo()
    assert 1.5 <= amp <= 5.0
```

### P4 — SmartRouter selecciona Ollama cuando no hay internet

Para cualquier query, si `Connectivity_Checker.is_online()` retorna `False`, el SmartRouter debe seleccionar `"ollama"` como motor:

```python
# Propiedad: sin internet → siempre Ollama
from hypothesis import given, strategies as st
from unittest.mock import patch
from brain import SmartRouter

@given(st.text(min_size=1, max_size=200))
def test_router_offline_uses_ollama(query):
    router = SmartRouter()
    with patch('brain.ConnectivityChecker.is_online', return_value=False):
        decision = router.analyze(query)
    assert decision.engine == "ollama"
```

### P5 — Mensajes de sesión agrupados correctamente

Para cualquier lista de mensajes insertados con el mismo `session_id`, la consulta por ese `session_id` debe retornar exactamente esos mensajes:

```python
# Propiedad: round-trip insert/query por session_id
from hypothesis import given, strategies as st
from memory_db import MemoryDB

@given(
    session_id=st.integers(min_value=1, max_value=9999),
    n_mensajes=st.integers(min_value=1, max_value=10),
)
def test_session_grouping(session_id, n_mensajes):
    db = MemoryDB(":memory:")
    for i in range(n_mensajes):
        db.save_conversation(f"entrada_{i}", f"respuesta_{i}", "neutral", session_id)
    resultado = db.load_by_session(session_id)
    assert len(resultado) == n_mensajes
    assert all(r.get("session_id") == session_id for r in resultado)
```
