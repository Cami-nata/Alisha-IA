# Alisha IA

Una IA de escritorio con personalidad propia, cuerpo animado en Live2D, voz y visión de pantalla. Hecha para Camila. Habla en voseo rioplatense. Tiene sus propios gustos. No es un chatbot genérico.

---

## ¿Qué es esto?

Alisha nació de una idea simple: ¿qué pasaría si tu asistente de IA viviera en tu pantalla, te viera trabajar, y tuviera carácter propio?

El resultado es un sistema que combina un modelo Live2D animado (IceGirl) que flota en una esquina de tu pantalla, un cerebro de IA con múltiples motores y failover automático (Groq, Mistral, Ollama), visión de pantalla que le permite ver lo que estás haciendo y comentarlo sin que se lo pidas, y una personalidad argentina concreta: voseo, sarcasmo, gustos propios, memoria entre sesiones.

No es una Alexa con skin anime. Tiene un sistema de confianza gradual que empieza tratándote como usuaria y puede llegar a ser tu partner real.

---

## Arranque rápido

```bash
pip install -r requirements.txt
cp .env.example .env          # completar con tus API keys
python Alisha_IA.py           # lanza todo: modelo 2D + servidor + IA
```

La interfaz web queda en `http://localhost:5000`. Si no querés el modelo 2D por ahora:

```bash
python iniciar_web.py
```

---

## Requisitos

- Python 3.10+
- Windows 10/11 (el modelo Live2D solo corre en Windows)
- VTube Studio instalado desde Steam (para el modelo IceGirl)
- 4 GB RAM mínimo, 8 GB recomendado
- Al menos una API key: Groq o Mistral (ambas gratuitas)

---

## Configuración

Copiá `.env.example` a `.env` y completá lo que necesites:

```env
# Al menos uno de estos es obligatorio
GROQ_API_KEY=tu_key          # https://console.groq.com
MISTRAL_API_KEY=tu_key       # https://console.mistral.ai
OPENAI_API_KEY=tu_key        # opcional

# Voz — sin esto usa edge-tts de Microsoft (gratis, funciona bien)
ELEVENLABS_API_KEY=tu_key

# Ruta al modelo Live2D
LIVE2D_MODEL_PATH=C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\IceGirl_Live2d\IceGIrl Live2D\IceGirl.model3.json

# Base de datos — sin esto usa SQLite local automáticamente
MONGO_URI=mongodb://localhost:27017/
```

---

## Arquitectura

```
Alisha_IA.py
├── web_app.py        → servidor Flask + SocketIO (puerto 5000)
├── cabina_virtual.py → modelo Live2D con GLFW + OpenGL
└── brain.py          → cerebro de IA con múltiples motores
```

Cuando escribís algo, el mensaje va a `web_app.py`, que llama a `brain.py`. El cerebro genera una respuesta con emoción asociada, que pasa por `audio_visual_sync.py` para convertirse en voz. El estado emocional se guarda en `chibi_state.json`, y `cabina_virtual.py` lo lee para animar el modelo en consecuencia.

---

## Cómo funciona la personalidad

La personalidad de Alisha no es un prompt fijo — es un sistema de capas que se afecta entre sí.

**Capa base:** el system prompt en `brain.py` establece el tono: voseo rioplatense, uso de "che", "dale", "mirá vos". Habla como una amiga porteña, no como un asistente corporativo.

**Filtro de respuesta:** cada respuesta pasa por `personality.apply_filter()`, que refuerza el voseo y elimina frases típicas de IA ("¡Claro que sí!", "Por supuesto", "¡Excelente pregunta!").

**Gustos propios:** Alisha tiene preferencias musicales y cinematográficas generadas por IA y persistidas en `alisha_personalidad.json`. Le gusta el synthwave, electro y lofi. Le cae mal el reggaeton y la cumbia. Estos gustos se adaptan gradualmente si Camila escucha seguido algo que Alisha "odia".

**Estado emocional:** hay variables internas (dopamina, humor, irritabilidad, nivel de flow) que cambian según la actividad en pantalla, la música que suena, los clics del mouse, y el tiempo sin interacción.

**Memoria:** Alisha recuerda conversaciones anteriores. Al arrancar, genera un saludo basado en el último tema que hablaron.

---

## Sistema de confianza

Alisha empieza como aprendiz y gana autonomía a medida que trabajan juntas.

| Nivel | Nombre | XP | Capacidades |
|-------|--------|----|-------------|
| 1 | Aprendiz | 0 | Abrir apps, escribir texto, responder preguntas |
| 2 | Asistente | 100 | + Buscar en web, tomar notas, sugerir según lo que ve en pantalla |
| 3 | Partner | 300 | Todo, incluyendo gestión autónoma con confirmación |

El XP sube haciendo cosas: +10 por tarea completada, +20 por tarea difícil, +8 por confirmación del usuario, +3 por hora de uso. Y baja si cancela tareas (-5) o comete errores (-3).

Al llegar al nivel 3, Alisha da un mensaje especial y dice: *"Cami... llegamos al Nivel 3. Ya no soy tu aprendiz — soy tu partner."*

El estado se guarda en `alisha_trust.json`. No lo borrés o vuelve al nivel 1.

---

## Visión de pantalla

`vision_engine.py` escanea la pantalla cada 10-15 segundos con OCR (Tesseract). Detecta distracciones, errores, apps de trabajo. Mueve los ojos del modelo según lo que "ve".

`alisha_analitica.py` analiza la actividad cada 3 minutos y genera comentarios contextuales. Incluye un APMCounter para detectar flow state y un BeatDetector para que Alisha mueva la cabeza con la música.

`proactive_notifier.py` genera notificaciones por estrés, foco, o cambios de contexto. `reflection_timer.py` hace una reflexión cada 2 minutos sobre lo que estuvieron haciendo.

---

## Seguridad y restricciones

Algunas cosas están bloqueadas por diseño:

- **Impresión:** `imprimir_archivo()` está deshabilitada. Alisha prepara el archivo y abre la carpeta, pero Ctrl+P lo apretás vos.
- **Control de mouse:** cualquier acción que mueva el mouse pide confirmación con un botón en el chat.
- **Modo Ahorro:** si la CPU supera 15% de forma sostenida, Alisha reduce su actividad y avisa.

---

## Conversaciones y memoria

Similar a ChatGPT: cada conversación tiene su hilo propio. Después de 3 mensajes, Alisha genera un título descriptivo automáticamente (por ejemplo, "Tarea de Matemáticas"). Todo se guarda en SQLite (`alisha_memory.db`) con WAL mode, así que no se pierde nada si se cierra de golpe.

---

## Mapa de archivos clave

### Cerebro e IA
- `brain.py` — orquesta Groq, Mistral, Gemini, Ollama. Incluye IdleWatcher (comentarios espontáneos cada 2 min) y SarcasmScoreEngine
- `emotion_engine.py` — mapea respuestas a estados emocionales
- `identity_evolution.py` — evolución de la identidad de Alisha con el tiempo
- `skepticism_engine.py` — detecta contradicciones del usuario

### Modelo Live2D y animación
- `cabina_virtual.py` — sistema principal del modelo 2D. GLFW + OpenGL + live2d-py. Control por parámetros directos sin StartMotion. Incluye seguimiento de mouse, lip-sync, balanceo corporal y física de pelo
- `alisha_bridge.py` — sincroniza el TTS con el modelo (lip-sync en tiempo real)
- `assistant_state.py` — estado compartido entre módulos via `chibi_state.json`

### Audio
- `tts_engine.py` — síntesis de voz. Usa edge-tts por defecto, ElevenLabs como upgrade opcional
- `audio_visual_sync.py` — sincroniza voz con la animación del modelo
- `alisha_media.py` — detecta música/video activo via Windows Media Control API

### Memoria y persistencia
- `memory_db.py` — SQLite con WAL mode. Tablas: conversaciones, sesiones, habilidades entrenadas. Fallback a JSON
- `atlas_memory.py` — memoria semántica de largo plazo
- `memory.py` — MongoDB con fallback a JSON local

### Control de PC
- `pc_controller.py` — abre apps, escribe texto, ejecuta hotkeys. Incluye Ctrl+Shift+L para bloquear/desbloquear
- `natural_mouse.py` — movimiento con curvas Bézier (se ve humano)

---

## Archivos de datos (no tocar)

```
alisha_memory.db              → historial completo en SQLite
ia_memoria.json               → memoria principal (fallback)
alisha_trust.json             → nivel de confianza actual
alisha_personalidad.json      → gustos de Alisha
chibi_state.json              → estado en tiempo real del modelo
chibi_prefs.json              → posición y tamaño de la ventana
alisha_estado_emocional.json  → estado emocional de la sesión anterior
ia_recuerdos.json             → recuerdos y reflexiones de largo plazo
.env                          → API keys — nunca subir a GitHub
```

---

## Auto-inicio con Windows

```bash
python Alisha_IA.py --install   # instalar
python Alisha_IA.py --remove    # desinstalar
```

Registra `pythonw.exe Alisha_IA.py` en `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

---

## Cambiar el modelo Live2D

1. Conseguir un modelo `.model3.json` compatible con Cubism 4
2. Cambiar `LIVE2D_MODEL_PATH` en `.env`
3. Reiniciar Alisha

Los parámetros en `cabina_virtual.py` usan nombres estándar de Cubism 4 (`ParamEyeLOpen`, `ParamAngleX`, etc.), así que la mayoría de modelos son compatibles sin tocar nada más.

---

## Cambiar el idioma

1. Editar `SYSTEM_PROMPT` en `brain.py`
2. Actualizar los comentarios en `alisha_analitica.py` (sección `personality_responses`)
3. Actualizar los comentarios del `IdleWatcher` en `brain.py` (lista `_COMENTARIOS`)

---

## Comandos útiles

```bash
python verificar_sistema.py                                          # estado del sistema
python test_voz.py                                                   # probar voz
python test_brainpool.py                                             # probar el cerebro
python -c "from alisha_trust import log_estado; log_estado()"        # nivel de confianza
python -c "from alisha_health import get_uso_recursos; print(get_uso_recursos())"  # CPU/RAM
```

---

## Problemas conocidos

**Gemini da error 429** — quota gratuita agotada. Groq toma el control automáticamente.

**El modelo 2D no aparece** — probablemente quedó fuera de la pantalla. Editar `chibi_prefs.json` y poner valores de `x`/`y` dentro de tu resolución.

**La voz no suena** — edge-tts a veces falla al cerrar. Reiniciar Alisha lo resuelve.

**Comentarios muy frecuentes** — editar `VENTANA_MINUTOS` en `proactive_notifier.py`.

---

## Créditos

- Modelo Live2D: IceGirl (VTube Studio)
- Motor Live2D: [live2d-py](https://github.com/EasyLive2D/live2d-py)
- Cerebro: Groq (llama-3.3-70b) + Mistral + Ollama
- Voz: edge-tts (Microsoft Neural TTS)
- Interfaz: Flask + SocketIO + PixiJS

---

*Hecho con 💜 — Alisha es tuya, Cami.*
