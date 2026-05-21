# 🎭 Alisha IA — Asistente Personal con Cuerpo Live2D

> Una IA con personalidad propia, cuerpo animado, voz y conciencia de lo que pasa en tu pantalla.
> Hecha a medida para Camila. Habla en voseo rioplatense. Tiene sus propios gustos. No es un chatbot.

---

## ¿Qué es Alisha?

Alisha es un asistente de IA de escritorio que combina:
- Un **modelo Live2D** (IceGirl) que vive en la esquina de tu pantalla
- Un **cerebro de IA** con múltiples motores (Groq, Mistral, Ollama) con failover automático
- **Visión de pantalla** — ve lo que estás haciendo y comenta sin que le preguntes
- **Personalidad argentina** — voseo, sarcasmo, gustos propios, memoria entre sesiones
- **Sistema de confianza gradual** — empieza como aprendiz y llega a ser tu partner

---

## Arranque rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar API keys (copiar y editar)
cp .env.example .env

# Iniciar Alisha completa (modelo 2D + servidor web + IA)
python Alisha_IA.py

# Solo la interfaz web (sin modelo 2D)
python iniciar_web.py
```

Abrir el chat en: **http://localhost:5000**

---

## Requisitos

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.10+ | |
| Windows | 10/11 | El modelo 2D solo funciona en Windows |
| VTube Studio | Cualquiera | Para el modelo IceGirl (Steam) |
| RAM | 4 GB | 8 GB recomendado |
| API Key | Groq o Mistral | Gratuitas — ver sección de configuración |

---

## Configuración (.env)

```env
# Motor de IA principal (al menos uno requerido)
GROQ_API_KEY=tu_key_aqui          # https://console.groq.com — gratis
MISTRAL_API_KEY=tu_key_aqui       # https://console.mistral.ai — gratis
OPENAI_API_KEY=tu_key_aqui        # opcional

# Voz (opcional — sin esto usa edge-tts gratis)
ELEVENLABS_API_KEY=tu_key_aqui

# Modelo Live2D (cambiar si tu modelo está en otra ruta)
LIVE2D_MODEL_PATH=C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\IceGirl_Live2d\IceGIrl Live2D\IceGirl.model3.json

# Base de datos (opcional — sin esto usa SQLite local)
MONGO_URI=mongodb://localhost:27017/
```

---

## Arquitectura del sistema

```
Alisha_IA.py          ← Punto de entrada maestro
├── web_app.py         ← Servidor Flask + SocketIO (puerto 5000)
├── cabina_virtual.py  ← Modelo Live2D con GLFW + OpenGL (ventana flotante)
└── brain.py           ← Cerebro de IA con múltiples motores
```

### Flujo de una conversación

```
Usuario escribe → web_app.py → brain.py (Groq/Mistral/Ollama)
                                    ↓
                            respuesta + emoción
                                    ↓
              audio_visual_sync.py → TTS → voz por parlantes
                                    ↓
              chibi_state.json ← estado emocional
                                    ↓
              cabina_virtual.py lee el estado → anima el modelo 2D
```

---

## Mapa de archivos

### 🧠 Cerebro e IA

| Archivo | Qué hace |
|---------|----------|
| `brain.py` | HybridIntelligenceCore — orquesta Groq, Mistral, Gemini, Ollama. Incluye IdleWatcher (comentarios espontáneos cada 2 min) y SarcasmScoreEngine |
| `ia.py` | Sistema de procesamiento de turnos de conversación |
| `emotion_engine.py` | Motor de emociones — mapea respuestas a estados (alegría, frustración, etc.) |
| `identity_evolution.py` | Evolución de la identidad de Alisha con el tiempo |
| `skepticism_engine.py` | Motor de escepticismo — detecta contradicciones del usuario |

### 🎭 Modelo Live2D y animación

| Archivo | Qué hace |
|---------|----------|
| `cabina_virtual.py` | **Sistema principal del modelo 2D.** GLFW + OpenGL + live2d-py. Control total por parámetros directos (sin StartMotion). Incluye: seguimiento de mouse, lip-sync, balanceo corporal, física de pelo |
| `desktop_widget.py` | Sistema alternativo con PyQt6 + WebEngine (fallback) |
| `alisha_bridge.py` | Bridge de comunicación entre TTS y el modelo 2D (lip-sync en tiempo real) |
| `assistant_state.py` | Estado compartido entre todos los módulos via `chibi_state.json` |

### 👁️ Visión y percepción

| Archivo | Qué hace |
|---------|----------|
| `vision_engine.py` | Escanea pantalla cada 10-15s. OCR con Tesseract. Detecta distracciones, errores, apps de trabajo. Mueve los ojos del modelo según lo que "ve" |
| `screen_vision.py` | Captura de pantalla y OCR base |
| `alisha_analitica.py` | Analiza actividad cada 3 min y genera comentarios contextuales. Incluye APMCounter (detecta flow state) y BeatDetector (mueve cabeza con la música) |
| `situational_awareness.py` | Orquestador de conciencia situacional — conecta ContextMonitor, PriorityInterrupt, ReflectionTimer |
| `context_monitor.py` | Monitorea ventana activa, ritmo de escritura, batería cada 30s |
| `priority_interrupt.py` | Detecta errores en pantalla y cambios bruscos de ventana en tiempo real (cada 2s) |
| `proactive_notifier.py` | Genera notificaciones proactivas (estrés, foco, cambio de contexto). Usa Groq como fallback de Ollama |
| `reflection_timer.py` | Reflexión profunda cada 2 min — analiza el buffer de actividad y genera comentario |
| `alisha_sugerencias.py` | Sugerencias inteligentes según la app activa (Canva → inspiración, Word → mejorar texto, etc.). Aprende de rechazos |

### 🎵 Audio y voz

| Archivo | Qué hace |
|---------|----------|
| `audio_visual_sync.py` | Orquestador de voz — sincroniza TTS con lip-sync del modelo 2D |
| `tts_engine.py` | Motor de síntesis de voz. Usa edge-tts (gratis) con fallback a ElevenLabs |
| `audio_listener.py` | Captura audio del sistema (loopback) para análisis |
| `alisha_media.py` | Detecta música/video activo via Windows Media Control API |
| `alisha_voz_control.py` | Semáforo global — evita que Alisha hable sobre sí misma |

### 💾 Memoria y persistencia

| Archivo | Qué hace |
|---------|----------|
| `memory_db.py` | Base de datos SQLite con WAL mode. Tablas: conversaciones (con session_id), sesiones, habilidades_entrenadas. Fallback a JSON |
| `memory.py` | Memoria principal — MongoDB con fallback a JSON local |
| `atlas_memory.py` | Memoria semántica de largo plazo para el sistema de conciencia situacional |
| `agent_memory.py` | Memoria del agente operativo |

### 🤝 Sistema de Confianza (Trust System)

| Archivo | Qué hace |
|---------|----------|
| `alisha_trust.py` | **Sistema de niveles de confianza.** Ver sección detallada abajo |
| `alisha_trust.json` | Estado persistente del nivel actual (se crea automáticamente) |

### 🖱️ Control de PC

| Archivo | Qué hace |
|---------|----------|
| `pc_controller.py` | Control del PC — abrir apps, escribir texto, hotkeys. Incluye hotkey Ctrl+Shift+L para bloquear/desbloquear |
| `natural_mouse.py` | Movimiento de mouse con curvas Bézier — se ve humano, no robótico |
| `actions.py` | Acciones individuales del PC |
| `agent_loop.py` | Loop del agente operativo — EventBus + ScreenWatcher + StateMapper |
| `alisha_print.py` | Gestión de impresión en **Modo Solo Consulta** — Alisha nunca imprime sola |

### 🔒 Seguridad

| Archivo | Qué hace |
|---------|----------|
| `safety_guard.py` | Guardia de seguridad — bloquea acciones peligrosas |
| `alisha_health.py` | Monitor de CPU/RAM. Si supera 15% → activa Modo Ahorro automáticamente |
| `alisha_print.py` | `imprimir_archivo()` está bloqueada — Alisha solo prepara y abre la carpeta |

### 🌐 Interfaz web

| Archivo | Qué hace |
|---------|----------|
| `web_app.py` | Servidor Flask + SocketIO. Todos los endpoints de la API. Puerto 5000 |
| `templates/index.html` | Chat web con sidebar de sesiones, widget de confianza, streaming de texto |
| `static/js/app.js` | Lógica del chat — SocketIO, propuestas de acción, trust widget |
| `landing/index.html` | Landing page del proyecto (http://localhost:5000/landing) |

### 🎨 Personalidad

| Archivo | Qué hace |
|---------|----------|
| `alisha_identity.py` | **Sistema de personalidad dinámica.** Ver sección detallada abajo |
| `alisha_personalidad.json` | Gustos persistentes de Alisha (generados por IA, se adaptan con el tiempo) |
| `alisha_sleep_anim.py` | Ciclo de sueño/despertar — Alisha arranca dormida y despierta con el primer movimiento del mouse |
| `alisha_sleep.py` | Sistema de sueño del proceso maestro |

---

## 🇦🇷 Cómo funciona la personalidad argentina

La personalidad de Alisha no es un prompt fijo — es un sistema de capas:

### Capa 1: System Prompt base (en `brain.py`)
El prompt del sistema define el tono base: voseo rioplatense, uso de "che", "dale", "mirá vos". Alisha habla como una amiga porteña, no como un asistente corporativo.

### Capa 2: Filtro de personalidad
Cada respuesta pasa por `personality.apply_filter()` que refuerza el voseo y elimina frases genéricas de IA ("¡Claro que sí!", "Por supuesto").

### Capa 3: Gustos propios (`alisha_identity.py`)
Alisha tiene gustos musicales y cinematográficos generados por IA y persistidos en `alisha_personalidad.json`:
- **Ama**: synthwave, electro, lofi, anime, comedia
- **Odia**: reggaeton, cumbia, terror
- Estos gustos **se adaptan gradualmente** si Camila escucha mucho algo que Alisha odia

### Capa 4: Estado emocional dinámico
El estado emocional (dopamina, humor, irritabilidad, flow) cambia según:
- Lo que Camila hace en pantalla
- La música que suena
- Los clics del mouse
- El tiempo sin interacción

### Capa 5: Memoria entre sesiones
Alisha recuerda lo que hablaron. Al arrancar, genera un saludo basado en el último tema de conversación.

---

## 🏆 Sistema de Confianza (Trust System)

Alisha empieza como aprendiz y gana autonomía con el tiempo.

### Niveles

| Nivel | Nombre | XP requerido | Qué puede hacer |
|-------|--------|-------------|-----------------|
| 🌱 1 | Aprendiz | 0 XP | Abrir apps, escribir texto, responder preguntas |
| ⭐ 2 | Asistente | 100 XP | + Buscar en web, tomar notas, sugerir según lo que ve |
| 💎 3 | Partner | 300 XP | Todo, incluyendo gestión autónoma con confirmación |

### Cómo sube el XP

| Evento | XP |
|--------|-----|
| Tarea completada | +10 |
| Tarea difícil | +20 |
| Confirmación del usuario | +8 |
| 1 hora de uso | +3 |
| Tarea cancelada | -5 |
| Error | -3 |

### Sorpresa al llegar al Nivel 3
Cuando Alisha llega al Nivel 3, da un mensaje especial, cambia el fondo del chat y dice: *"Cami... llegamos al Nivel 3. Ya no soy tu aprendiz — soy tu partner."*

### Dónde se guarda
`alisha_trust.json` — se crea automáticamente. No borrar o Alisha vuelve al Nivel 1.

---

## 💬 Sistema de Hilos de Conversación

Similar a ChatGPT — cada conversación tiene su propio hilo.

- **Nueva conversación**: botón "✨ Nueva conversación" en el sidebar
- **Títulos automáticos**: tras 3 mensajes, Alisha genera un título descriptivo (ej: "Tarea de Matemáticas")
- **Carga por hilo**: al hacer clic en un chat del sidebar, carga solo esos mensajes
- **Persistencia**: todo en SQLite (`alisha_memory.db`) con WAL mode — no se pierde nada si se cierra de golpe

---

## 🔒 Protocolo de Seguridad

Alisha tiene restricciones de hardware por diseño:

1. **Impresión**: `imprimir_archivo()` está bloqueada. Alisha solo prepara el archivo y abre la carpeta. Vos apretás Ctrl+P.
2. **Control de PC**: acciones que mueven el mouse siempre piden confirmación con botón en el chat
3. **Modo Ahorro**: si CPU supera 15% sostenido → reduce actividad automáticamente y avisa
4. **Sandbox**: antes de ejecutar cualquier acción, simula en el log

---

## 🚀 Auto-inicio con Windows

Alisha está configurada para arrancar automáticamente:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\AlishaIA
→ pythonw.exe "ruta\Alisha_IA.py"
```

Para instalar/desinstalar:
```bash
python Alisha_IA.py --install   # instalar auto-inicio
python Alisha_IA.py --remove    # quitar auto-inicio
```

---

## 🎨 Cambiar el modelo Live2D (skin)

1. Conseguir un modelo `.model3.json` compatible con Cubism 4
2. Editar `.env`:
   ```env
   LIVE2D_MODEL_PATH=C:\ruta\a\tu\modelo\modelo.model3.json
   ```
3. Reiniciar Alisha

Los parámetros de animación en `cabina_virtual.py` están mapeados a nombres estándar de Cubism 4 (`ParamEyeLOpen`, `ParamAngleX`, etc.) — la mayoría de modelos son compatibles.

---

## 🌍 Agregar otro idioma

La personalidad está en el system prompt de `brain.py`. Para cambiar el idioma:

1. Buscar `SYSTEM_PROMPT` en `brain.py`
2. Cambiar las instrucciones de idioma (actualmente: voseo rioplatense argentino)
3. Actualizar los comentarios hardcodeados en `alisha_analitica.py` (sección `personality_responses`)
4. Actualizar los comentarios del `IdleWatcher` en `brain.py` (lista `_COMENTARIOS`)

---

## 📁 Archivos de datos (no tocar)

| Archivo | Contenido |
|---------|-----------|
| `alisha_memory.db` | Base de datos SQLite con todo el historial |
| `ia_memoria.json` | Memoria principal en JSON (fallback) |
| `alisha_trust.json` | Nivel de confianza actual |
| `alisha_personalidad.json` | Gustos de Alisha (generados por IA) |
| `chibi_state.json` | Estado en tiempo real del modelo 2D |
| `chibi_prefs.json` | Posición y tamaño de la ventana del modelo |
| `alisha_estado_emocional.json` | Estado emocional de la sesión anterior |
| `ia_recuerdos.json` | Recuerdos y reflexiones de largo plazo |
| `.env` | API keys — **nunca subir a GitHub** |

---

## 🛠️ Comandos útiles

```bash
# Ver estado del sistema
python verificar_sistema.py

# Probar la voz
python test_voz.py

# Probar el cerebro de IA
python test_brainpool.py

# Ver impresoras disponibles
python -c "from alisha_print import listar_impresoras; print(listar_impresoras())"

# Ver nivel de confianza actual
python -c "from alisha_trust import log_estado; log_estado()"

# Ver uso de CPU/RAM
python -c "from alisha_health import get_uso_recursos; print(get_uso_recursos())"
```

---

## ⚠️ Problemas conocidos

| Problema | Causa | Solución |
|----------|-------|----------|
| Gemini da error 429 | Quota gratuita agotada | Groq funciona como fallback automático |
| El modelo 2D no aparece | Posición fuera de pantalla | Editar `chibi_prefs.json` y poner x/y dentro de la resolución |
| La voz no suena | edge-tts falla al cerrar | Reiniciar Alisha |
| Comentarios muy frecuentes | SilenceGuard muy corto | Editar `VENTANA_MINUTOS` en `proactive_notifier.py` |

---

## 📝 Créditos

- Modelo Live2D: IceGirl (VTube Studio)
- Motor Live2D: [live2d-py](https://github.com/EasyLive2D/live2d-py)
- Cerebro: Groq (llama-3.3-70b) + Mistral + Ollama
- Voz: edge-tts (Microsoft Neural TTS)
- Interfaz: Flask + SocketIO + PixiJS

---

*Hecho con 💜 — Alisha es tuya, Cami.*
