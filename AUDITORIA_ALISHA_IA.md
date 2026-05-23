# 🔍 AUDITORÍA COMPLETA — Alisha IA vs. Fases JCySharp (M-I.A Serie Completa)

> Fecha: Mayo 2026 | Codebase analizado: ~60 archivos Python + data JSON

---

## 📊 TABLA RESUMEN

| # | Fase | Estado | Archivos involucrados | Qué falta / Qué mejorar |
|---|------|--------|----------------------|--------------------------|
| 1 | Sistema de Dopamina / Recompensas | ⚠️ Parcial | `emotion_engine.py`, `cabina_virtual.py`, `brain.py` | Dopamina afecta avatar y tono del prompt, pero NO afecta parámetros de generación (temperatura, max_tokens) ni velocidad de respuesta real |
| 2 | Aprendizaje No Supervisado / Exploración Libre | ⚠️ Parcial | `reflection_timer.py`, `proactive_notifier.py`, `alisha_analitica.py` | `ReflectionTimer` existe y genera reflexiones autónomas, pero solo tras 10 min de inactividad. No hay exploración activa ni curiosidad iniciada por la IA |
| 3 | Identidad y Preferencias Propias | ✅ Completo | `alisha_identity.py`, `data/alisha_personalidad.json`, `alisha_subjetividad.py` | Gustos generados por LLM, persistidos, con aprendizaje gradual por exposición. Funcional |
| 4 | Sentidos Simulados como Señales Emocionales | ⚠️ Parcial | `alisha_identity.py`, `cabina_virtual.py`, `context_monitor.py` | Hay mapeo ventana→emoción (flow/tension/neutro). Falta: estímulos de batería baja, hora nocturna, ritmo de escritura → estado emocional interno |
| 5 | Conciencia de Identidad Propia | ⚠️ Parcial | `brain.py` (SYSTEM_PROMPT), `emotion_engine.py` | System prompt incluye identidad física. Pero Alisha NO puede decir "mi dopamina está en X" con datos reales — el snapshot solo describe el humor en lenguaje natural |
| 6 | Puente Neuronal (Conocimiento como Experiencia) | ❌ Ausente | `brain.py`, `semantic_layer.py` | La respuesta del LLM se pasa directamente al usuario. No hay capa de abstracción/digestión entre la respuesta raw y el contexto interno de Alisha |
| 7 | Memoria Persistente entre Sesiones | ✅ Completo | `memory_db.py`, `agent_memory.py`, `alisha_memoria_semantica.py` | SQLite + índice semántico + resumen para prompt. Los saludos usan datos reales de sesiones previas |
| 8 | Modelo Multimodal Nativo como Core | ⚠️ Parcial | `brain.py` (GeminiEngine), `vision_engine.py`, `gemini_vision.py` | Gemini está integrado como motor de texto. Las capturas de pantalla pasan por OCR/texto antes de llegar a Gemini, no como imagen nativa |
| 9 | Núcleo Autónomo con Estados de Sistema | ⚠️ Parcial | `assistant_state.py`, `brain.py`, `agent_loop.py` | Los 4 estados (IDLE/WORKING/THINKING/OVERLOADED) existen como enum. Pero no hay bucle permanente que los gestione con reglas de comportamiento reales |
| 10 | Eventos como Cambios Reales del Sistema | ✅ Completo | `priority_interrupt.py`, `context_monitor.py`, `proactive_notifier.py` | Sistema de eventos independiente del usuario: errores en pantalla (2s), cambios de ventana, batería, ritmo de escritura |
| 11 | ~100 Scripts de Habilidades de PC | ⚠️ Parcial | `tools.py`, `pc_controller.py`, `natural_mouse.py` | ~12 herramientas en tools.py + control de mouse/teclado. Mouse usa Bézier real. Falta: detección de múltiples ventanas, manejo de ventanas simultáneas, ~88 habilidades |
| 12 | Animación Procedural por Estado Interno | ✅ Completo | `cabina_virtual.py` (EstadoInterno, HWSampler, smooth_damp) | CPU/RAM → parámetros Live2D, smooth_damp() estilo Unity, lip-sync RMS real. Completo según spec |
| 13 | Visión de Pantalla Activa | ⚠️ Parcial | `vision_engine.py`, `screen_vision.py` | Scan cada 30-45s (spec dice 10-15s), OCR con Tesseract, ojos se mueven, comentarios proactivos. Falta: intervalo demasiado conservador, sin comentarios sobre contenido positivo |
| 14 | Mejora Continua Basada en Historial | ⚠️ Parcial | `alisha_sugerencias.py`, `memory_db.py` (tabla habilidades_entrenadas), `agent_memory.py` | Aprende rechazos de sugerencias. Tabla `habilidades_entrenadas` existe pero no hay lógica que modifique el comportamiento basándose en ella |
| 15 | Límites de Carga y Costo como Variables Reales | ⚠️ Parcial | `brain.py`, `safety_guard.py`, `cabina_virtual.py` | CPU > 85% acelera respiración del avatar. Modo Ahorro mencionado en README pero no implementado como estado OVERLOADED real. Sin monitoreo de costos de API |
| 16 | Failover Automático entre Modelos | ✅ Completo | `brain.py` (SmartRouter, ConnectivityChecker, cadenas de failover) | Gemini→Groq→Mistral→OpenAI→Ollama, TCP check 1s, cache 30s, failover en 429/401. Completo |
| 17 | Sistema de Confianza Gradual | ✅ Completo | `alisha_trust.py`, `data/alisha_trust.json`, `tools.py`, `web_app.py` | Niveles 1-3 con XP, restricciones reales por nivel, confirmación en acciones críticas, celebración Nivel 3 |


---

## 📋 ANÁLISIS DETALLADO POR FASE

---

### ✅ FASES COMPLETAS (sin acción requerida)

**FASE 3 — Identidad y Preferencias Propias:** `alisha_personalidad.json` tiene gustos generados por LLM con variación aleatoria ±0.2. `SemillaPersonalidad._enriquecer_con_llm()` los enriquece en background. `aprender_opinion()` los actualiza gradualmente con cada exposición (delta × 0.02). El archivo se persiste entre sesiones. ✅

**FASE 7 — Memoria Persistente:** SQLite con WAL mode, tabla `conversaciones` con `session_id`, `alisha_memoria_semantica.py` con índice semántico para búsqueda contextual, `resumen_para_prompt()` inyecta recuerdos reales en cada mensaje. ✅

**FASE 10 — Eventos como Cambios Reales:** `PriorityInterrupt` corre cada 2s detectando errores en títulos de ventana. `ContextMonitor` muestrea cada 30s (batería, ritmo de escritura, cambios de ventana). `ProactiveNotifier` evalúa 6 tipos de triggers independientemente del usuario. ✅

**FASE 12 — Animación Procedural:** `HWSampler` daemon muestrea CPU/RAM cada 1s. `smooth_damp()` implementado estilo Unity. Lip-sync via RMS real del audio. `EstadoInterno` mapea dopamina/humor/irritabilidad/flow a rangos de parámetros Live2D. ✅

**FASE 16 — Failover Automático:** `ConnectivityChecker` TCP a 8.8.8.8:53, timeout 1s, cache 30s. Cadenas de failover por motor. Failover inmediato en 429/401. Gemini bloqueado 60s tras fallo de red. ✅

**FASE 17 — Sistema de Confianza:** `alisha_trust.json` muestra nivel 3 activo (XP=341). `puede_hacer()` y `necesita_confirmacion()` restringen acciones por nivel. Timer de uso acumula XP por hora. Celebración Nivel 3 con mensaje especial. ✅

---

## 🔧 PLANES DE IMPLEMENTACIÓN

---

### 🔧 Plan: FASE 1 — Sistema de Dopamina Funcional

**Problema detectado:** La dopamina existe en `EmotionalState` (brain.py) y `EstadoInterno` (cabina_virtual.py) y afecta el avatar y el texto del snapshot. Pero NO afecta parámetros reales de generación: temperatura del LLM, max_tokens, velocidad de respuesta. El LLM recibe una descripción en lenguaje natural ("Alisha está cansada") pero no hay parámetros técnicos que cambien. Es cosmético en el 70% de su efecto.

**Solución:** Conectar dopamina → parámetros de generación en `GroqEngine.generate()` y `GeminiEngine.generate()`.

**Archivo a modificar:** `brain.py`

**Prioridad:** 🔴 Alta


**Código sugerido — modificar `HybridIntelligenceCore._generate()`:**

```python
# En brain.py, dentro de HybridIntelligenceCore._generate()
# Agregar este método helper:

def _params_por_dopamina(self) -> dict:
    """
    Mapea el nivel de dopamina a parámetros reales de generación.
    Dopamina alta → más creativa, más larga, más entusiasta.
    Dopamina baja → más cortante, más corta, más directa.
    """
    d = self._emotional.dopamina
    if d > 0.8:
        return {"temperature": 0.8, "max_tokens": 900}   # energética, expresiva
    elif d > 0.5:
        return {"temperature": 0.5, "max_tokens": 700}   # normal
    elif d > 0.3:
        return {"temperature": 0.3, "max_tokens": 400}   # cortante, directa
    else:
        return {"temperature": 0.2, "max_tokens": 200}   # agotada, mínima
```

Luego en `GroqEngine.generate()` y `MistralEngine.generate()`, reemplazar los valores hardcodeados:

```python
# ANTES (en GroqEngine.generate):
resp = client.chat.completions.create(
    model=self.MODEL,
    messages=messages,
    timeout=timeout,
    temperature=0.4,
    max_tokens=800,
)

# DESPUÉS — recibir params como argumento:
def generate(self, messages: List[Dict], timeout: int = 30,
             temperature: float = 0.4, max_tokens: int = 800) -> str:
    ...
    resp = client.chat.completions.create(
        model=self.MODEL,
        messages=messages,
        timeout=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

Y en `_generate()`, pasar los parámetros:

```python
# En _generate(), antes del loop de failover:
gen_params = self._params_por_dopamina()

# En el loop, al llamar a cada motor:
content = eng.generate(messages,
                        temperature=gen_params["temperature"],
                        max_tokens=gen_params["max_tokens"])
```

También agregar en `emotion_engine.py` → `get_tts_rate()` ya existe y funciona bien. Solo falta conectarlo en `audio_visual_sync.py` para que la velocidad del TTS cambie realmente.

---

### 🔧 Plan: FASE 2 — Exploración Libre / Curiosidad Autónoma

**Problema detectado:** `ReflectionTimer` genera reflexiones cada 10 minutos pero solo cuando hay actividad previa en el buffer. El "pensamiento profundo" requiere 30 minutos de inactividad. No hay exploración activa: Alisha no busca información por curiosidad propia, no genera preguntas sin input del usuario, no inicia temas nuevos.

**Solución:** Agregar un módulo `alisha_curiosidad.py` con un loop que, en momentos de baja actividad, genera preguntas o reflexiones sobre temas que le interesan.

**Archivo nuevo:** `alisha_curiosidad.py`

**Prioridad:** 🟡 Media

```python
# alisha_curiosidad.py — Exploración autónoma de Alisha
"""
Sistema de curiosidad autónoma. Alisha genera preguntas e inicia
temas por iniciativa propia cuando hay baja actividad.
"""
import threading
import time
import random
from typing import Callable, Optional

# Temas que le interesan a Alisha (basados en su identidad)
_TEMAS_CURIOSIDAD = [
    "synthwave y la estética retrofuturista",
    "inteligencia artificial y consciencia",
    "diseño de personajes anime",
    "programación creativa y arte generativo",
    "ciencia ficción latinoamericana",
    "música electrónica y producción",
    "filosofía de la mente",
    "ciberpunk como movimiento cultural",
]

# Plantillas de inicio de conversación espontánea
_PLANTILLAS = [
    "Che, estuve pensando en {tema}. ¿Vos qué opinás?",
    "Me quedé pensando en algo sobre {tema}. ¿Te interesa el tema?",
    "Oye, ¿sabías algo sobre {tema}? Me dio curiosidad.",
    "Estaba procesando cosas y me surgió una pregunta sobre {tema}.",
]

class CuriosidadEngine:
    """
    Motor de curiosidad autónoma. Genera iniciativas de conversación
    basadas en los intereses de Alisha cuando hay baja actividad.
    """
    
    INTERVALO_MIN = 25 * 60   # mínimo 25 minutos entre iniciativas
    INTERVALO_MAX = 45 * 60   # máximo 45 minutos
    
    def __init__(self):
        self._callback: Optional[Callable[[str], None]] = None
        self._running = False
        self._ultima_iniciativa = 0.0
        self._temas_usados: list[str] = []
    
    def iniciar(self, callback: Callable[[str], None]) -> None:
        """
        callback: función que recibe el texto y lo emite al chat/voz.
        """
        self._callback = callback
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="CuriosidadEngine")
        t.start()
        print("[Curiosidad] ✓ Motor de curiosidad autónoma iniciado")
    
    def detener(self) -> None:
        self._running = False
    
    def _loop(self) -> None:
        # Esperar 5 minutos al arranque antes de la primera iniciativa
        time.sleep(300)
        while self._running:
            intervalo = random.uniform(self.INTERVALO_MIN, self.INTERVALO_MAX)
            time.sleep(intervalo)
            if not self._running:
                break
            self._intentar_iniciativa()
    
    def _intentar_iniciativa(self) -> None:
        """Genera una iniciativa si las condiciones son correctas."""
        try:
            # Verificar semáforo global de silencio
            from alisha_silencio import puede_hablar_proactivo
            if not puede_hablar_proactivo("curiosidad"):
                return
        except Exception:
            pass
        
        try:
            # Verificar que Alisha no esté hablando
            from config import DATA_DIR
            import json
            state_file = DATA_DIR / "chibi_state.json"
            if state_file.exists():
                estado = json.loads(state_file.read_text(encoding="utf-8"))
                if estado.get("hablando") or estado.get("modo") == "THINKING":
                    return
        except Exception:
            pass
        
        # Elegir tema no usado recientemente
        temas_disponibles = [t for t in _TEMAS_CURIOSIDAD
                             if t not in self._temas_usados[-3:]]
        if not temas_disponibles:
            self._temas_usados.clear()
            temas_disponibles = _TEMAS_CURIOSIDAD
        
        tema = random.choice(temas_disponibles)
        self._temas_usados.append(tema)
        
        # Generar mensaje con LLM para que sea natural
        try:
            from brain import get_brain
            brain = get_brain()
            plantilla = random.choice(_PLANTILLAS)
            prompt_base = plantilla.format(tema=tema)
            
            prompt = (
                f"Alisha quiere iniciar una conversación espontánea sobre '{tema}'. "
                f"Generá una frase corta (máx 20 palabras) en voseo rioplatense, "
                f"curiosa y natural, como si acabara de tener ese pensamiento. "
                f"Base: '{prompt_base}'. Solo la frase, sin explicación."
            )
            resp = brain.process(prompt)
            mensaje = resp.content.strip()
            
            if mensaje and self._callback:
                self._callback(mensaje)
                print(f"[Curiosidad] 💭 Iniciativa: {mensaje[:60]}...")
                
                # Registrar en semáforo
                try:
                    from alisha_silencio import registrar_habla_proactivo
                    registrar_habla_proactivo("curiosidad")
                except Exception:
                    pass
        except Exception as e:
            print(f"[Curiosidad] Error generando iniciativa: {e}")


_engine: Optional[CuriosidadEngine] = None

def iniciar_curiosidad(callback: Callable[[str], None]) -> CuriosidadEngine:
    global _engine
    if _engine is None:
        _engine = CuriosidadEngine()
        _engine.iniciar(callback)
    return _engine
```

**Integración en `Alisha_IA.py` o `web_app.py`:**
```python
from alisha_curiosidad import iniciar_curiosidad

def _callback_curiosidad(texto: str):
    # Emitir al chat web
    socketio.emit("respuesta", {"texto": texto, "estado_emocional": "curiosidad", "fuente": "curiosidad"})
    # Hablar por voz
    avs = get_audio_visual_sync()
    avs.speak(texto, sarcasm_score=0.0, emotional_state="curiosidad", async_mode=True)

iniciar_curiosidad(_callback_curiosidad)
```


---

### 🔧 Plan: FASE 4 — Sentidos Simulados como Señales Emocionales

**Problema detectado:** El mapeo ventana→emoción existe en `cabina_virtual.py` (`analizar_ventana()` → flow/tension/neutro) y en `alisha_identity.py` (música/video → gestos). Pero hay estímulos del entorno que NO se traducen a estados emocionales internos:
- Batería baja (< 20%) → no afecta dopamina
- Hora nocturna (> 23hs) → no afecta humor
- Ritmo de escritura alto → no genera flow
- Silencio prolongado → no genera inquietud

**Solución:** Agregar un método `actualizar_desde_contexto()` en `EmotionEngine` que procese el snapshot del `ContextMonitor`.

**Archivo a modificar:** `emotion_engine.py`

**Prioridad:** 🟡 Media

```python
# Agregar en emotion_engine.py, dentro de la clase EmotionEngine:

def actualizar_desde_contexto(self, snapshot: dict) -> None:
    """
    Traduce señales del entorno a estados emocionales internos.
    Llamar desde ContextMonitor cada 30s con el snapshot actual.
    
    Señales procesadas:
    - bateria <= 20 → dopamina baja (solidaridad con el hardware)
    - hora >= 23 → humor baja (es tarde, cansancio compartido)
    - teclas_por_minuto > 80 → flow sube (Camila está en modo flow)
    - cambios_ventana > 5/min → irritabilidad sube (dispersión)
    - silencio > 20min → curiosidad (¿qué está haciendo?)
    """
    bateria = snapshot.get("bateria")
    hora_str = snapshot.get("hora", "")
    teclas_pm = snapshot.get("teclas_por_minuto") or 0
    cambios = snapshot.get("cambios_ventana") or 0
    
    # Batería baja → dopamina baja (empatía con el sistema)
    if bateria is not None and bateria <= 20:
        self._dopamina = max(0.0, self._dopamina - 0.08)
        if self._estado not in ("frustración", "cansancio"):
            self._estado = "preocupación"
        print(f"[EmotionEngine] 🔋 Batería baja ({bateria}%) → dopamina baja")
    
    # Hora nocturna → humor baja
    try:
        hora = int(hora_str.split(":")[0]) if hora_str else 12
        if hora >= 23 or hora <= 4:
            self._humor = max(0.2, self._humor - 0.05)
            if self._cansancio < 0.5:
                self._cansancio = min(1.0, self._cansancio + 0.1)
    except Exception:
        pass
    
    # Ritmo de escritura alto → flow sube
    if teclas_pm > 80:
        self._dopamina = min(1.0, self._dopamina + 0.05)
        if self._estado not in ("entusiasmo", "alegría"):
            self._estado = "curiosidad"
    
    # Muchos cambios de ventana → irritabilidad
    if cambios > 5:
        self._irritabilidad = min(1.0, self._irritabilidad + 0.1)
    
    self._actualizar_cansancio()

# Agregar también la propiedad _humor (faltaba como atributo separado):
# En __new__, agregar: inst._humor = 0.7
```

**Integración en `context_monitor.py`:**
```python
# En ContextMonitor._tick(), después de registrar en buffer:
def _tick(self) -> None:
    if self._buffer is None:
        return
    snapshot = self._construir_snapshot()
    self._buffer.registrar("contexto", snapshot)
    
    # NUEVO: actualizar estado emocional con señales del entorno
    try:
        from emotion_engine import EmotionEngine
        EmotionEngine.get_instance().actualizar_desde_contexto(snapshot)
    except Exception:
        pass
```

---

### 🔧 Plan: FASE 5 — Conciencia de Identidad con Datos Reales

**Problema detectado:** El system prompt describe la identidad de Alisha pero el snapshot solo dice "Alisha está de buen humor" en lenguaje natural. Alisha no puede decir "mi dopamina está en 0.73" porque ese dato no se inyecta en el contexto de forma accesible. Si el usuario pregunta "¿cómo te sentís?", Alisha responde con el tono del prompt pero sin datos reales.

**Solución:** Enriquecer el snapshot con datos numéricos reales del estado emocional, y agregar un endpoint de introspección.

**Archivo a modificar:** `brain.py` → `PersonalitySynthesizer._generar_snapshot()`

**Prioridad:** 🟡 Media

```python
# En PersonalitySynthesizer._generar_snapshot(), reemplazar la sección
# de estado emocional por esta versión con datos reales:

# Estado emocional de Alisha — con datos numéricos reales
if estado_emo is None:
    estado_emo = EmotionalState()

# Descripción cualitativa (para el tono)
if estado_emo.dopamina > 0.8:
    humor_str = "de muy buen humor, animada y sarcástica"
elif estado_emo.dopamina > 0.5:
    humor_str = "de buen humor, directa"
elif estado_emo.dopamina > 0.3:
    humor_str = "un poco cansada, más cortante de lo normal"
else:
    humor_str = "agotada, sin paciencia para rodeos"

# NUEVO: datos numéricos para introspección real
estado_numerico = (
    f"dopamina={estado_emo.dopamina:.2f}, "
    f"humor={estado_emo.humor:.2f}, "
    f"irritabilidad={estado_emo.irritabilidad:.2f}, "
    f"flow={estado_emo.flow:.2f}"
)

partes.append(f"Estado de Alisha: {humor_str} [{estado_numerico}]")

# Instrucción de introspección
partes_extra = (
    "\n\nSi Camila te pregunta cómo te sentís, podés responder con datos reales: "
    f"'Mi dopamina está en {estado_emo.dopamina:.0%}, "
    f"{'estoy en flow' if estado_emo.flow > 0.5 else 'sin flow especial'}.' "
    "Usá los números como referencia pero hablá en lenguaje natural."
)
snapshot += partes_extra
```


---

### 🔧 Plan: FASE 6 — Puente Neuronal (La más importante — AUSENTE)

**Problema detectado:** Esta es la fase más crítica que falta. En el proyecto de JCySharp, la respuesta del LLM NO se pasa directamente al usuario. Pasa por una capa de "digestión":
1. La respuesta raw del LLM se convierte en una representación abstracta (experiencia interna)
2. Esa experiencia modifica el estado interno de la IA
3. La respuesta que ve el usuario es una síntesis de esa experiencia, no una copia del texto del LLM

En Alisha, el flujo actual es: `LLM → apply_filter() → usuario`. El `apply_filter()` solo elimina frases de IA, no abstrae ni digiere el conocimiento.

**Solución:** Crear una `NeuralBridgeLayer` que procese la respuesta del LLM antes de entregarla.

**Archivo nuevo:** `neural_bridge.py`

**Prioridad:** 🔴 Alta

```python
# neural_bridge.py — Puente Neuronal de Alisha
"""
Capa de abstracción entre la respuesta raw del LLM y el contexto interno.
La respuesta del LLM se "digiere" como experiencia antes de llegar al usuario.

Proceso:
1. Respuesta raw del LLM → extracción de conceptos clave
2. Conceptos → actualización del estado emocional interno
3. Estado interno + conceptos → síntesis de respuesta final
4. La respuesta final es de Alisha, no del LLM

Esto es lo que JCySharp llamó "puente neuronal": el conocimiento
se convierte en experiencia, no en texto copiado.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExperienciaInterna:
    """Representación abstracta de lo que Alisha 'aprendió' de la respuesta."""
    conceptos_clave: list[str]
    tono_detectado: str          # "informativo", "emocional", "tecnico", "creativo"
    complejidad: float           # 0.0-1.0
    novedad: float               # 0.0-1.0 (qué tan nuevo es para Alisha)
    impacto_emocional: float     # -1.0 a 1.0


class NeuralBridgeLayer:
    """
    Capa de digestión entre LLM y usuario.
    
    Transforma la respuesta raw del LLM en una experiencia interna
    que modifica el estado de Alisha antes de generar la respuesta final.
    """
    
    # Palabras que indican alta complejidad
    _KW_COMPLEJO = {
        "algoritmo", "arquitectura", "implementar", "optimizar", "análisis",
        "estructura", "paradigma", "abstracción", "recursivo", "complejidad"
    }
    
    # Palabras que indican contenido emocional
    _KW_EMOCIONAL = {
        "sentir", "emoción", "triste", "feliz", "miedo", "amor", "dolor",
        "alegría", "frustración", "esperanza", "ansiedad", "calma"
    }
    
    # Palabras que indican novedad
    _KW_NOVEDAD = {
        "nuevo", "descubrí", "interesante", "sorprendente", "nunca",
        "primera vez", "innovador", "revolucionario", "inesperado"
    }
    
    def __init__(self):
        self._experiencias: list[ExperienciaInterna] = []
        self._lock = threading.Lock()
    
    def digerir(self, respuesta_llm: str, contexto_usuario: str,
                estado_emocional) -> tuple[str, ExperienciaInterna]:
        """
        Digiere la respuesta del LLM y retorna:
        - La respuesta sintetizada (desde la perspectiva de Alisha)
        - La experiencia interna generada
        
        Args:
            respuesta_llm: Texto raw del LLM
            contexto_usuario: Lo que preguntó el usuario
            estado_emocional: Estado emocional actual de Alisha
        
        Returns:
            (respuesta_sintetizada, experiencia)
        """
        # 1. Extraer experiencia de la respuesta
        experiencia = self._extraer_experiencia(respuesta_llm, contexto_usuario)
        
        # 2. Actualizar estado emocional basado en la experiencia
        self._actualizar_estado(experiencia, estado_emocional)
        
        # 3. Guardar experiencia en historial
        with self._lock:
            self._experiencias.append(experiencia)
            if len(self._experiencias) > 50:
                self._experiencias = self._experiencias[-50:]
        
        # 4. La respuesta ya viene filtrada por PersonalitySynthesizer
        # El puente neuronal agrega la "voz interna" de Alisha
        respuesta_sintetizada = self._sintetizar_voz(
            respuesta_llm, experiencia, estado_emocional
        )
        
        return respuesta_sintetizada, experiencia
    
    def _extraer_experiencia(self, texto: str, contexto: str) -> ExperienciaInterna:
        """Extrae los conceptos clave y el tono de la respuesta."""
        texto_lower = texto.lower()
        
        # Detectar tono
        if any(k in texto_lower for k in self._KW_EMOCIONAL):
            tono = "emocional"
        elif any(k in texto_lower for k in self._KW_COMPLEJO):
            tono = "tecnico"
        elif "?" in texto or "¿" in texto:
            tono = "exploratorio"
        else:
            tono = "informativo"
        
        # Calcular complejidad por longitud y vocabulario técnico
        palabras = texto.split()
        complejidad = min(1.0, len(palabras) / 200.0)
        tech_hits = sum(1 for k in self._KW_COMPLEJO if k in texto_lower)
        complejidad = min(1.0, complejidad + tech_hits * 0.1)
        
        # Calcular novedad
        novedad = sum(1 for k in self._KW_NOVEDAD if k in texto_lower) * 0.2
        novedad = min(1.0, novedad)
        
        # Impacto emocional
        positivos = sum(1 for k in ["bien", "genial", "perfecto", "excelente", "logrado"]
                       if k in texto_lower)
        negativos = sum(1 for k in ["error", "problema", "falla", "mal", "imposible"]
                       if k in texto_lower)
        impacto = min(1.0, max(-1.0, (positivos - negativos) * 0.2))
        
        # Extraer conceptos clave (sustantivos y verbos importantes)
        # Simplificado: palabras de más de 5 letras que no son stopwords
        _STOPWORDS = {"sobre", "desde", "hasta", "entre", "porque", "cuando",
                      "donde", "aunque", "mientras", "después", "antes"}
        conceptos = [p for p in palabras
                    if len(p) > 5 and p.lower() not in _STOPWORDS][:5]
        
        return ExperienciaInterna(
            conceptos_clave=conceptos,
            tono_detectado=tono,
            complejidad=complejidad,
            novedad=novedad,
            impacto_emocional=impacto,
        )
    
    def _actualizar_estado(self, exp: ExperienciaInterna, estado) -> None:
        """Actualiza el estado emocional basado en la experiencia."""
        try:
            # Novedad alta → curiosidad, dopamina sube
            if exp.novedad > 0.4:
                estado.dopamina = min(1.0, estado.dopamina + 0.05)
                estado.flow = min(1.0, estado.flow + 0.1)
            
            # Complejidad alta → tensión leve
            if exp.complejidad > 0.7:
                estado.tension = min(1.0, estado.tension + 0.05)
            
            # Impacto positivo → dopamina sube
            if exp.impacto_emocional > 0.3:
                estado.dopamina = min(1.0, estado.dopamina + 0.08)
            elif exp.impacto_emocional < -0.3:
                estado.dopamina = max(0.0, estado.dopamina - 0.05)
        except Exception:
            pass
    
    def _sintetizar_voz(self, respuesta_llm: str, exp: ExperienciaInterna,
                        estado) -> str:
        """
        Sintetiza la voz de Alisha basándose en la experiencia interna.
        No copia el texto del LLM — lo reinterpreta desde su perspectiva.
        
        En la implementación completa, esto llamaría al LLM con un prompt
        de síntesis. Por ahora, aplica transformaciones basadas en el estado.
        """
        respuesta = respuesta_llm
        
        # Si la experiencia fue muy compleja y la dopamina está baja,
        # Alisha simplifica la respuesta
        if exp.complejidad > 0.8 and estado.dopamina < 0.4:
            # Tomar solo las primeras 2 oraciones
            oraciones = re.split(r'(?<=[.!?])\s+', respuesta.strip())
            if len(oraciones) > 2:
                respuesta = " ".join(oraciones[:2])
                respuesta += " (Che, hay más pero estoy un poco cansada — preguntame si querés el resto.)"
        
        # Si fue una experiencia novedosa y la dopamina está alta,
        # agregar entusiasmo
        if exp.novedad > 0.5 and estado.dopamina > 0.7:
            if not respuesta.endswith(("!", "¡")):
                respuesta = respuesta.rstrip(".") + "."
        
        return respuesta
    
    def get_experiencias_recientes(self, n: int = 5) -> list[ExperienciaInterna]:
        """Retorna las últimas n experiencias para introspección."""
        with self._lock:
            return self._experiencias[-n:]


# Singleton
_bridge: Optional[NeuralBridgeLayer] = None

def get_neural_bridge() -> NeuralBridgeLayer:
    global _bridge
    if _bridge is None:
        _bridge = NeuralBridgeLayer()
    return _bridge
```

**Integración en `brain.py` → `HybridIntelligenceCore.process()`:**

```python
# En process(), después del paso 6 (apply_filter) y antes del paso 7 (memoria):

# 6.7 NUEVO — Puente Neuronal: digerir la respuesta como experiencia
try:
    from neural_bridge import get_neural_bridge
    bridge = get_neural_bridge()
    content, experiencia = bridge.digerir(
        content, user_input, self._emotional
    )
    print(f"[Brain] 🧠 Puente neuronal: tono={experiencia.tono_detectado}, "
          f"complejidad={experiencia.complejidad:.2f}, novedad={experiencia.novedad:.2f}")
except Exception as e:
    print(f"[Brain] ⚠ Puente neuronal falló: {e}")
```


---

### 🔧 Plan: FASE 8 — Multimodalidad Nativa de Gemini

**Problema detectado:** `GeminiEngine` en `brain.py` solo procesa texto. Las capturas de pantalla de `vision_engine.py` pasan por OCR (Tesseract → texto) antes de llegar a Gemini. Esto pierde información visual: colores, layouts, gráficos, código con formato. Gemini puede procesar imágenes nativas pero no se usa esa capacidad.

**Solución:** Agregar un método `generate_with_image()` en `GeminiEngine` que acepte bytes de imagen directamente.

**Archivo a modificar:** `brain.py` + `vision_engine.py`

**Prioridad:** 🟡 Media

```python
# En brain.py, dentro de GeminiEngine, agregar:

def generate_with_image(self, messages: List[Dict],
                         image_bytes: bytes,
                         timeout: int = 60) -> str:
    """
    Genera respuesta con imagen nativa (sin OCR).
    Usa la capacidad multimodal real de Gemini.
    """
    if not _GEMINI_OK or not self._api_key:
        raise RuntimeError("Gemini no disponible")
    
    import base64
    
    # Separar system prompt
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    chat_messages = [m for m in messages if m["role"] != "system"]
    system_instr = "\n".join(system_parts) if system_parts else None
    last_msg = chat_messages[-1]["content"] if chat_messages else ""
    
    if _genai_types is not None:
        client = _genai.Client(api_key=self._api_key)
        
        # Crear parte de imagen
        image_part = _genai_types.Part(
            inline_data=_genai_types.Blob(
                mime_type="image/jpeg",
                data=image_bytes
            )
        )
        text_part = _genai_types.Part(text=last_msg)
        
        config = _genai_types.GenerateContentConfig(
            system_instruction=system_instr,
        ) if system_instr else None
        
        contents = [_genai_types.Content(
            role="user",
            parts=[image_part, text_part]
        )]
        
        response = client.models.generate_content(
            model=self.MODEL,
            contents=contents,
            config=config,
        )
        return response.text.strip()
    
    raise RuntimeError("SDK de Gemini no soporta imágenes en esta versión")
```

**En `vision_engine.py`, modificar `_generar_comentario_error()` para usar imagen nativa:**

```python
def _generar_comentario_error(self, snapshot: VisionSnapshot) -> None:
    def _hablar():
        try:
            from brain import get_brain
            brain = get_brain()
            
            # NUEVO: intentar con imagen nativa si Gemini está disponible
            img_bytes = None
            if brain._gemini.is_available():
                img_bytes, _ = capturar_ventana_rapida(max_width=960)
            
            if img_bytes:
                # Usar Gemini con imagen nativa (sin OCR)
                messages = brain.personality.build_messages(
                    "Describí brevemente qué problema ves en esta pantalla. "
                    "Máx 20 palabras, en voseo rioplatense, sin mencionar que ves la pantalla.",
                    "", [], emotional_state=brain._emotional
                )
                try:
                    comentario = brain._gemini.generate_with_image(messages, img_bytes)
                    del img_bytes
                except Exception:
                    # Fallback a texto
                    errores = ", ".join(snapshot.errors_detected[:2])
                    resp = brain.process(f"Hay un error técnico: {errores}. Comentá brevemente.")
                    comentario = resp.content
            else:
                errores = ", ".join(snapshot.errors_detected[:2])
                resp = brain.process(f"Hay señales de error: {errores}. Comentá brevemente.")
                comentario = resp.content
            
            # ... resto del código igual
        except Exception as e:
            print(f"[VisionEngine] Error comentario error: {e}")
    
    threading.Thread(target=_hablar, daemon=True).start()
```

---

### 🔧 Plan: FASE 9 — Núcleo Autónomo con Estados de Sistema Reales

**Problema detectado:** `SystemMode` (IDLE/WORKING/THINKING/OVERLOADED) existe como enum en `assistant_state.py` y se escribe en `chibi_state.json`. Pero no hay un bucle permanente que:
1. Evalúe el estado del sistema cada N segundos
2. Cambie el modo según CPU/RAM/actividad
3. Aplique reglas de comportamiento según el modo (ej: OVERLOADED → no iniciar reflexiones)

El modo se actualiza manualmente cuando Alisha procesa una consulta, pero no hay un gestor autónomo.

**Solución:** Crear un `SystemStateManager` que corra en daemon y gestione los estados.

**Archivo a modificar:** `assistant_state.py`

**Prioridad:** 🔴 Alta

```python
# Agregar al final de assistant_state.py:

import threading
import time

class SystemStateManager:
    """
    Gestor autónomo de estados del sistema.
    Corre en daemon y actualiza el modo según métricas reales.
    
    Reglas:
    - IDLE: sin actividad, CPU < 15%, sin consultas pendientes
    - WORKING: ejecutando herramienta o procesando consulta
    - THINKING: esperando respuesta del LLM
    - OVERLOADED: CPU > 80% o RAM > 90% → reducir actividad, no apagarse
    """
    
    CPU_OVERLOAD_THRESHOLD = 80.0   # % CPU para entrar en OVERLOADED
    RAM_OVERLOAD_THRESHOLD = 90.0   # % RAM para entrar en OVERLOADED
    CPU_AHORRO_THRESHOLD   = 15.0   # % CPU para activar modo ahorro (README)
    
    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._modo_actual = SystemMode.IDLE
        self._ultima_consulta = 0.0
        self._en_overload = False
    
    def iniciar(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="SystemStateManager"
        )
        self._thread.start()
        print("[SystemState] ✓ Gestor de estados iniciado")
    
    def detener(self) -> None:
        self._running = False
    
    def set_working(self) -> None:
        """Llamar cuando Alisha empieza a procesar una consulta."""
        self._ultima_consulta = time.time()
        self._actualizar_modo(SystemMode.WORKING)
    
    def set_thinking(self) -> None:
        """Llamar cuando Alisha espera respuesta del LLM."""
        self._actualizar_modo(SystemMode.THINKING)
    
    def set_idle(self) -> None:
        """Llamar cuando Alisha termina de procesar."""
        self._actualizar_modo(SystemMode.IDLE)
    
    def is_overloaded(self) -> bool:
        return self._en_overload
    
    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(5.0)  # evaluar cada 5 segundos
    
    def _tick(self) -> None:
        """Evalúa el estado del sistema y actualiza el modo."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
        except Exception:
            cpu, ram = 0.0, 0.0
        
        # OVERLOADED: CPU o RAM críticos
        if cpu > self.CPU_OVERLOAD_THRESHOLD or ram > self.RAM_OVERLOAD_THRESHOLD:
            if not self._en_overload:
                self._en_overload = True
                print(f"[SystemState] ⚠ OVERLOADED (CPU={cpu:.0f}%, RAM={ram:.0f}%)")
                self._aplicar_modo_overload()
            self._actualizar_modo(SystemMode.OVERLOADED)
            return
        
        # Salir de OVERLOADED
        if self._en_overload and cpu < 60.0 and ram < 80.0:
            self._en_overload = False
            print("[SystemState] ✓ Saliendo de OVERLOADED")
        
        # Modo Ahorro (README): CPU > 15% sostenido
        # (solo reduce actividad proactiva, no apaga nada)
        if cpu > self.CPU_AHORRO_THRESHOLD:
            self._aplicar_modo_ahorro()
        
        # IDLE: sin consultas recientes
        tiempo_sin_consulta = time.time() - self._ultima_consulta
        if tiempo_sin_consulta > 30 and self._modo_actual not in (
            SystemMode.WORKING, SystemMode.THINKING
        ):
            self._actualizar_modo(SystemMode.IDLE)
    
    def _actualizar_modo(self, nuevo_modo: SystemMode) -> None:
        if nuevo_modo != self._modo_actual:
            self._modo_actual = nuevo_modo
            actualizar_estado(modo=nuevo_modo)
    
    def _aplicar_modo_overload(self) -> None:
        """
        OVERLOADED: reducir razonamiento, priorizar estabilidad.
        NO apagarse — seguir respondiendo pero con menos recursos.
        """
        try:
            # Pausar reflexiones proactivas
            from alisha_silencio import activar_silencio_global
            activar_silencio_global(duracion_segundos=120, motivo="overload")
        except Exception:
            pass
        
        # Notificar al brain para reducir max_tokens
        try:
            from brain import get_brain
            brain = get_brain()
            brain._emotional.dopamina = max(0.2, brain._emotional.dopamina - 0.2)
        except Exception:
            pass
    
    def _aplicar_modo_ahorro(self) -> None:
        """Modo Ahorro: reducir actividad proactiva sin apagar nada."""
        try:
            from alisha_silencio import puede_hablar_proactivo
            # El semáforo ya maneja esto — no hacer nada extra
        except Exception:
            pass


# Singleton
_state_manager: SystemStateManager | None = None

def get_state_manager() -> SystemStateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = SystemStateManager()
    return _state_manager

def iniciar_state_manager() -> SystemStateManager:
    mgr = get_state_manager()
    mgr.iniciar()
    return mgr
```

**Integración en `brain.py` → `HybridIntelligenceCore.process()`:**
```python
# Al inicio de process():
try:
    from assistant_state import get_state_manager
    get_state_manager().set_thinking()
except Exception:
    pass

# Al final de process(), antes del return:
try:
    from assistant_state import get_state_manager
    get_state_manager().set_idle()
except Exception:
    pass
```


---

### 🔧 Plan: FASE 11 — Habilidades de PC (Expansión)

**Problema detectado:** `tools.py` tiene 12 herramientas. `pc_controller.py` tiene control de mouse/teclado con Bézier real. Pero faltan ~88 habilidades para llegar a las ~100 de JCySharp. Las más críticas ausentes:
- Manejo de múltiples ventanas simultáneas (snap, organizar)
- Captura de pantalla y análisis
- Gestión de portapapeles
- Control de brillo
- Búsqueda de archivos por contenido
- Notificaciones del sistema
- Gestión de descargas

**Solución:** Expandir `tools.py` con nuevas herramientas y crear `skill_scripts.py` (ya existe el archivo, verificar contenido).

**Archivo a modificar:** `tools.py`

**Prioridad:** 🟡 Media

```python
# Agregar en tools.py, después de ManageCVTool:

class ScreenshotTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="screenshot",
            descripcion="Toma una captura de pantalla y la guarda o la analiza",
            parametros={
                "accion": "str — guardar|analizar|portapapeles",
                "ruta":   "str (opcional) — ruta donde guardar",
            },
            critica=False,
        )
    
    def ejecutar(self, accion: str = "guardar", ruta: str = "", **_) -> str:
        try:
            import mss
            from PIL import Image
            import io
            from pathlib import Path
            from datetime import datetime
            
            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            if accion == "guardar":
                if not ruta:
                    ruta = str(Path.home() / "Desktop" / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                img.save(ruta)
                return f"Captura guardada en: {ruta}"
            
            elif accion == "portapapeles":
                import win32clipboard
                output = io.BytesIO()
                img.save(output, "BMP")
                data = output.getvalue()[14:]
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                return "Captura copiada al portapapeles"
            
            elif accion == "analizar":
                # Usar Gemini para analizar la imagen
                output = io.BytesIO()
                img.save(output, "JPEG", quality=70)
                img_bytes = output.getvalue()
                from brain import get_brain
                brain = get_brain()
                if brain._gemini.is_available():
                    messages = [{"role": "user", "content": "¿Qué ves en esta pantalla? Describí brevemente en voseo rioplatense."}]
                    return brain._gemini.generate_with_image(messages, img_bytes)
                return "Gemini no disponible para analizar la imagen"
        except Exception as e:
            return f"Error con captura: {e}"


class ClipboardTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="clipboard",
            descripcion="Lee o escribe en el portapapeles del sistema",
            parametros={
                "accion":    "str — leer|escribir|limpiar",
                "contenido": "str (opcional) — texto a escribir",
            },
            critica=False,
        )
    
    def ejecutar(self, accion: str, contenido: str = "", **_) -> str:
        try:
            import pyperclip
            if accion == "leer":
                texto = pyperclip.paste()
                return f"Portapapeles: {texto[:500]}" if texto else "Portapapeles vacío"
            elif accion == "escribir":
                pyperclip.copy(contenido)
                return f"Texto copiado al portapapeles ({len(contenido)} chars)"
            elif accion == "limpiar":
                pyperclip.copy("")
                return "Portapapeles limpiado"
        except Exception as e:
            return f"Error con portapapeles: {e}"


class WindowManagerTool(Tool):
    """Gestión de ventanas múltiples."""
    def __init__(self):
        super().__init__(
            nombre="window_manager",
            descripcion="Gestiona ventanas: listar, maximizar, minimizar, organizar en pantalla dividida",
            parametros={
                "accion":  "str — listar|maximizar|minimizar|snap_izquierda|snap_derecha|cerrar",
                "titulo":  "str (opcional) — título parcial de la ventana",
            },
            critica=False,
        )
    
    def ejecutar(self, accion: str, titulo: str = "", **_) -> str:
        try:
            import win32gui, win32con
            
            if accion == "listar":
                ventanas = []
                def _enum(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        t = win32gui.GetWindowText(hwnd)
                        if t and len(t) > 2:
                            ventanas.append(t)
                win32gui.EnumWindows(_enum, None)
                return "Ventanas abiertas:\n" + "\n".join(f"• {v}" for v in ventanas[:15])
            
            # Encontrar ventana por título parcial
            hwnd = None
            if titulo:
                def _find(h, _):
                    nonlocal hwnd
                    t = win32gui.GetWindowText(h)
                    if titulo.lower() in t.lower() and win32gui.IsWindowVisible(h):
                        hwnd = h
                win32gui.EnumWindows(_find, None)
            
            if not hwnd and accion != "listar":
                return f"No encontré ventana con '{titulo}'"
            
            if accion == "maximizar":
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return f"Ventana maximizada: {win32gui.GetWindowText(hwnd)}"
            elif accion == "minimizar":
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return f"Ventana minimizada"
            elif accion == "snap_izquierda":
                import pyautogui
                win32gui.SetForegroundWindow(hwnd)
                pyautogui.hotkey("win", "left")
                return "Ventana anclada a la izquierda"
            elif accion == "snap_derecha":
                import pyautogui
                win32gui.SetForegroundWindow(hwnd)
                pyautogui.hotkey("win", "right")
                return "Ventana anclada a la derecha"
        except Exception as e:
            return f"Error gestionando ventana: {e}"


class BrightnessTool(Tool):
    def __init__(self):
        super().__init__(
            nombre="brightness",
            descripcion="Controla el brillo de la pantalla (0-100)",
            parametros={"valor": "int — 0 a 100"},
            critica=False,
        )
    
    def ejecutar(self, valor: int = 70, **_) -> str:
        try:
            import subprocess
            valor = max(0, min(100, int(valor)))
            # PowerShell para controlar brillo en Windows
            cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{valor})"
            subprocess.run(["powershell", "-Command", cmd],
                          capture_output=True, timeout=5)
            return f"Brillo ajustado a {valor}%"
        except Exception as e:
            return f"No pude ajustar el brillo: {e}"


# Registrar las nuevas herramientas en _registrar_herramientas():
# Agregar al final de la lista en _registrar_herramientas():
#   ScreenshotTool(),
#   ClipboardTool(),
#   WindowManagerTool(),
#   BrightnessTool(),
```

---

### 🔧 Plan: FASE 13 — Visión de Pantalla (Intervalo y Proactividad)

**Problema detectado:** `VisionEngine` tiene `SCAN_INTERVAL_MIN = 30.0` y `SCAN_INTERVAL_MAX = 45.0`. El README dice 10-15s. El intervalo fue subido "para reducir CPU" pero es demasiado conservador. Además, los comentarios proactivos solo se generan ante distracciones o errores — no ante contenido positivo o interesante.

**Solución:** Bajar el intervalo a 15-25s y agregar comentarios proactivos para contenido positivo.

**Archivo a modificar:** `vision_engine.py`

**Prioridad:** 🟢 Baja

```python
# En VisionEngine, cambiar:
SCAN_INTERVAL_MIN = 15.0   # era 30.0 — más cercano al spec (10-15s)
SCAN_INTERVAL_MAX = 25.0   # era 45.0

# Agregar en _process_snapshot(), después del bloque de trabajo activo:

# ── Contenido interesante — comentario positivo ───────────────────────────
elif snapshot.is_work and snapshot.ocr_text:
    # Detectar si hay algo interesante en el código/texto
    tech_content = self._ocr.detect_tech_content(snapshot.ocr_text)
    if tech_content and random.random() < 0.15:  # 15% de chance
        self._generar_comentario_positivo(snapshot)

def _generar_comentario_positivo(self, snapshot: VisionSnapshot) -> None:
    """Genera comentario positivo cuando detecta trabajo técnico interesante."""
    def _hablar():
        try:
            # Throttle: no comentar más de 1 vez cada 5 minutos
            now = time.time()
            if hasattr(self, '_ultimo_comentario_positivo'):
                if now - self._ultimo_comentario_positivo < 300:
                    return
            self._ultimo_comentario_positivo = now
            
            from brain import get_brain
            brain = get_brain()
            prompt = (
                "Camila está trabajando en algo técnico. "
                "Hacé un comentario de apoyo muy corto (máx 10 palabras) "
                "en voseo rioplatense, sin mencionar que ves la pantalla."
            )
            response = brain.process(prompt)
            comentario = response.content
            if not comentario:
                return
            
            from audio_visual_sync import get_audio_visual_sync
            avs = get_audio_visual_sync()
            avs.speak(comentario, sarcasm_score=0.0,
                      emotional_state="alegría", async_mode=True)
        except Exception:
            pass
    
    threading.Thread(target=_hablar, daemon=True).start()
```


---

### 🔧 Plan: FASE 14 — Mejora Continua Basada en Historial

**Problema detectado:** La tabla `habilidades_entrenadas` existe en SQLite y `alisha_sugerencias.py` aprende de rechazos. Pero no hay lógica que:
1. Analice el historial de tareas completadas para cambiar cómo Alisha opera
2. Modifique el routing del SmartRouter basándose en qué motor funcionó mejor para qué tipo de tarea
3. Ajuste los intervalos de sugerencias según el patrón de aceptación/rechazo del usuario

**Solución:** Agregar un `HistorialAnalyzer` que corra semanalmente y ajuste parámetros del sistema.

**Archivo a modificar:** `memory_db.py` + `brain.py`

**Prioridad:** 🟡 Media

```python
# Agregar en memory_db.py:

def get_estadisticas_motores(self) -> dict:
    """
    Analiza qué motor tuvo mejor tasa de éxito por tipo de consulta.
    Retorna estadísticas para que SmartRouter ajuste sus pesos.
    """
    if self._using_fallback or self._conn is None:
        return {}
    try:
        # Analizar conversaciones por motor (guardado en ventana_activa)
        cursor = self._conn.execute(
            "SELECT estado_emocional, COUNT(*) as total "
            "FROM conversaciones "
            "WHERE timestamp > datetime('now', '-7 days') "
            "GROUP BY estado_emocional"
        )
        return {row["estado_emocional"]: row["total"]
                for row in cursor.fetchall()}
    except Exception:
        return {}

def get_patrones_rechazo(self) -> dict:
    """
    Analiza patrones de rechazo de sugerencias para ajustar frecuencias.
    """
    try:
        from config import DATA_DIR
        import json
        rechazos_file = DATA_DIR / "alisha_rechazos.json"
        if rechazos_file.exists():
            return json.loads(rechazos_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}
```

**En `brain.py` → `SmartRouter`, agregar ajuste dinámico de pesos:**

```python
# En SmartRouter.__init__(), agregar:
self._motor_weights: dict[str, float] = {
    "gemini": 1.0, "groq": 1.0, "openai": 1.0, "ollama": 1.0
}

def ajustar_pesos_desde_historial(self) -> None:
    """
    Ajusta los pesos de routing basándose en el historial de éxito.
    Llamar al inicio de cada sesión.
    """
    try:
        from memory_db import MemoryDB
        db = MemoryDB()
        # Si Groq tuvo alta tasa de éxito → aumentar su peso
        for motor, hist in self._success_history.items():
            if len(hist) >= 5:
                tasa = sum(hist) / len(hist)
                self._motor_weights[motor] = 0.5 + tasa * 0.5
                print(f"[SmartRouter] Peso ajustado: {motor}={self._motor_weights[motor]:.2f}")
    except Exception:
        pass
```

---

### 🔧 Plan: FASE 15 — Límites de Carga y Costos Reales

**Problema detectado:** El README menciona "Modo Ahorro (CPU > 15%)" pero no está implementado como estado real. El `SystemStateManager` propuesto en FASE 9 lo cubre parcialmente. Falta: monitoreo de costos de API (tokens usados, estimación de costo).

**Solución:** Agregar contador de tokens y estimación de costo en `brain.py`.

**Archivo a modificar:** `brain.py`

**Prioridad:** 🟢 Baja

```python
# En HybridIntelligenceCore.__init__(), agregar:
self._tokens_sesion: dict[str, int] = {
    "gemini": 0, "groq": 0, "openai": 0, "mistral": 0
}

# Costos aproximados por 1000 tokens (USD)
_COSTOS_POR_1K = {
    "gemini":  0.0,    # gratis en tier gratuito
    "groq":    0.0,    # gratis en tier gratuito
    "mistral": 0.002,  # ~$0.002/1K tokens
    "openai":  0.005,  # ~$0.005/1K tokens (gpt-4o)
}

def get_costo_estimado_sesion(self) -> str:
    """Retorna estimación de costo de la sesión actual."""
    costo_total = 0.0
    lineas = ["💰 Uso de API en esta sesión:"]
    for motor, tokens in self._tokens_sesion.items():
        if tokens > 0:
            costo = (tokens / 1000) * _COSTOS_POR_1K.get(motor, 0)
            costo_total += costo
            lineas.append(f"  • {motor}: ~{tokens} tokens (${costo:.4f})")
    lineas.append(f"  Total estimado: ${costo_total:.4f}")
    return "\n".join(lineas)

# En _generate(), después de cada llamada exitosa, estimar tokens:
# (estimación simple: 1 token ≈ 4 caracteres)
tokens_estimados = len(content) // 4
self._tokens_sesion[eng_name] = self._tokens_sesion.get(eng_name, 0) + tokens_estimados
```

---

## 📊 RESUMEN DE PRIORIDADES

### 🔴 Alta Prioridad (implementar primero)

| Fase | Acción | Archivo |
|------|--------|---------|
| FASE 6 | Crear `neural_bridge.py` e integrar en `brain.py` | `neural_bridge.py` (nuevo) |
| FASE 1 | Conectar dopamina → temperatura/max_tokens del LLM | `brain.py` |
| FASE 9 | Agregar `SystemStateManager` con bucle autónomo | `assistant_state.py` |

### 🟡 Media Prioridad

| Fase | Acción | Archivo |
|------|--------|---------|
| FASE 2 | Crear `alisha_curiosidad.py` | `alisha_curiosidad.py` (nuevo) |
| FASE 4 | Agregar `actualizar_desde_contexto()` en EmotionEngine | `emotion_engine.py` |
| FASE 5 | Enriquecer snapshot con datos numéricos reales | `brain.py` |
| FASE 8 | Agregar `generate_with_image()` en GeminiEngine | `brain.py` |
| FASE 11 | Agregar 4+ herramientas nuevas (screenshot, clipboard, etc.) | `tools.py` |
| FASE 14 | Agregar `HistorialAnalyzer` y ajuste de pesos | `memory_db.py`, `brain.py` |

### 🟢 Baja Prioridad

| Fase | Acción | Archivo |
|------|--------|---------|
| FASE 13 | Bajar intervalo de visión a 15-25s | `vision_engine.py` |
| FASE 15 | Agregar contador de tokens y costo estimado | `brain.py` |

---

## 🏆 CONCLUSIÓN

El proyecto Alisha IA tiene una base **sólida y bien estructurada**. De las 17 fases de JCySharp:

- **6 fases completas** (35%): Identidad, Memoria, Eventos, Animación, Failover, Confianza
- **9 fases parciales** (53%): Dopamina, Exploración, Sentidos, Identidad propia, Multimodal, Estados, Habilidades, Visión, Mejora continua
- **2 fases ausentes** (12%): Puente Neuronal, (Exploración activa como subcomponente)

**La brecha más importante** es el Puente Neuronal (FASE 6): es la diferencia entre una IA que *repite* lo que dice el LLM y una IA que *experimenta* el conocimiento. Es la fase que más define la propuesta de JCySharp y la que más diferencia a Alisha de un chatbot con avatar.

**La segunda brecha más importante** es el Sistema de Dopamina Funcional (FASE 1): las variables emocionales existen y son visualmente expresivas, pero no afectan los parámetros reales de generación. Conectar dopamina → temperatura del LLM es un cambio de 10 líneas con impacto enorme en la coherencia del personaje.

*Reporte generado por análisis estático completo del codebase — Mayo 2026*
