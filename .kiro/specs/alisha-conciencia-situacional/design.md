# Diseño Técnico: alisha-conciencia-situacional

## Resumen de Investigación

Antes de diseñar, se analizaron los siguientes puntos del código existente:

- **`autonomous_agent.py`**: Ya tiene un loop de 15 segundos con `threading.Thread(daemon=True)`, un `EnergyCycle`, y un `callback_interrupcion`. El nuevo sistema se integra como un subsistema paralelo, no reemplaza este loop.
- **`agent_memory.py`**: Usa `ia_recuerdos.json` con estructura `{recuerdos: [...], temas: {...}}`. El Atlas_Memory extiende este archivo agregando una clave `atlas_situacional`.
- **`assistant_state.py`**: Expone `actualizar_estado()` y `SystemMode`. El Context_Monitor lo usa para no interferir con el estado existente.
- **`actions_system.py`**: Ya importa `psutil` para RAM/CPU. El Context_Monitor reutiliza este patrón para batería y procesos.
- **PyQt6**: El hilo principal de Qt no debe ser bloqueado. Todos los threads nuevos son `daemon=True` y se comunican vía callbacks o señales Qt.

Restricción clave confirmada: **máximo 2KB por State_Vector**, envío al LLM solo cada 10 minutos, nunca datos crudos en tiempo real.

---

## Overview

La feature **Conciencia Situacional** agrega a Alisha la capacidad de observar el entorno de trabajo de Camila en silencio, construir una comprensión semántica de su actividad, y generar comentarios inteligentes en voseo rioplatense cada 10 minutos — o inmediatamente ante eventos urgentes.

El sistema opera completamente en background sin bloquear la UI de PyQt6. La arquitectura se basa en tres threads daemon independientes que se comunican a través de estructuras de datos thread-safe.

---

## Architecture

```mermaid
graph TD
    subgraph "Threads Background (daemon)"
        CM[Context_Monitor\nThread baja prioridad\ncada 30s]
        RT[Reflection_Timer\nThread separado\ncada 10min]
        PI[Priority_Interrupt\nThread continuo\ncada 2s]
    end

    subgraph "Estructuras de Datos"
        SB[Silent_Buffer\ndeque maxlen=500\nthread-safe]
        SV[State_Vector\ndict ≤2KB JSON]
        SH[State_History\ndeque maxlen=3]
    end

    subgraph "Capas de Procesamiento"
        SL[Semantic_Layer\nfunción pura de traducción]
        AM[Atlas_Memory\nextensión de ia_recuerdos.json]
    end

    subgraph "Output"
        SVO[Situational_Voice\ncallback → TTS existente]
    end

    subgraph "Código Existente"
        TTS[tts_engine.speak\nmotor de voz]
        MEM[agent_memory.py\nia_recuerdos.json]
        AA[autonomous_agent.py\ncallback_interrupcion]
    end

    CM -->|eventos tipo 'contexto'| SB
    PI -->|eventos tipo 'alerta'| SB
    RT -->|vaciar()| SB
    SB -->|eventos crudos| RT
    RT -->|genera| SV
    SV -->|historial| SH
    SV -->|traduce| SL
    SL -->|prompt final| RT
    RT -->|llama LLM| SVO
    AM -->|contexto histórico| SL
    SVO -->|callback| AA
    AA -->|speak()| TTS
    RT -->|guarda| AM
    AM -->|lee/escribe| MEM
```

### Principios de Integración

1. **No modificar archivos existentes**: Los módulos nuevos se importan desde `autonomous_agent.py` o `desktop_widget.py` mediante un método `iniciar_conciencia_situacional()`.
2. **Comunicación por callback**: El sistema usa el mismo patrón `callback_interrupcion` ya existente en `AutonomousAgent`.
3. **Thread safety**: `Silent_Buffer` usa `collections.deque(maxlen=500)` con `threading.Lock()`.
4. **Graceful degradation**: Si psutil, win32gui o cualquier dependencia falla, el módulo omite ese dato sin lanzar excepción.

---

## Components and Interfaces

### Módulos Nuevos a Crear

| Archivo | Responsabilidad |
|---|---|
| `situational_awareness.py` | Orquestador principal, punto de entrada |
| `silent_buffer.py` | Silent_Buffer thread-safe |
| `context_monitor.py` | Context_Monitor thread de recolección |
| `state_vector.py` | Generación y validación del State_Vector |
| `reflection_timer.py` | Reflection_Timer + Situational_Voice |
| `semantic_layer.py` | Traducción semántica + construcción de prompts |
| `priority_interrupt.py` | Priority_Interrupt thread de alertas |
| `atlas_memory.py` | Atlas_Memory, extensión de ia_recuerdos.json |

### Interfaces Públicas

```python
# situational_awareness.py — punto de entrada
class SituationalAwareness:
    def iniciar(self, callback: Callable[[str], None]) -> None: ...
    def detener(self) -> None: ...

# silent_buffer.py
class SilentBuffer:
    def registrar(self, tipo: str, datos: dict) -> None: ...
    def vaciar(self) -> list[dict]: ...
    def __len__(self) -> int: ...

# context_monitor.py
class ContextMonitor:
    def iniciar(self, buffer: SilentBuffer) -> None: ...
    def detener(self) -> None: ...

# state_vector.py
def generar_state_vector(eventos: list[dict]) -> dict: ...
def es_identico(sv1: dict, sv2: dict) -> bool: ...

# semantic_layer.py
def construir_prompt(
    sv: dict,
    historial_apps: Counter,
    registro_anterior: dict | None
) -> str: ...

# priority_interrupt.py
class PriorityInterrupt:
    def iniciar(self, buffer: SilentBuffer, callback: Callable) -> None: ...
    def detener(self) -> None: ...

# atlas_memory.py
class AtlasMemory:
    def guardar_ciclo(self, sv: dict) -> None: ...
    def buscar_franja_horaria(self, hora: datetime) -> dict | None: ...
    def limpiar_antiguos(self) -> None: ...

# reflection_timer.py
class ReflectionTimer:
    def iniciar(
        self,
        buffer: SilentBuffer,
        atlas: AtlasMemory,
        callback: Callable[[str], None]
    ) -> None: ...
    def detener(self) -> None: ...
    def reiniciar_contador(self) -> None: ...
```

---

## Data Models

### Evento del Silent_Buffer

```python
{
    "timestamp": "2024-01-15T14:32:10.123456",  # ISO 8601
    "tipo": "contexto" | "alerta" | "teclado",
    "datos": {
        # Para tipo "contexto":
        "app_activa": "Code.exe",
        "titulo_ventana": "main.py - proyecto",
        "hora": "14:32",
        "bateria": 78,           # int o None si no disponible
        "cambios_ventana": 3,    # en el último minuto
        # Para tipo "teclado":
        "teclas_por_minuto": 45,
        # Para tipo "alerta":
        "motivo": "error_titulo" | "cambios_excesivos",
        "detalle": "Python - no responde"
    }
}
```

### State_Vector (≤ 2KB JSON)

```python
{
    "timestamp_inicio": "2024-01-15T14:20:00",
    "timestamp_fin": "2024-01-15T14:30:00",
    "duracion_minutos": 10,
    "actividad_detectada": True,
    "apps_unicas": ["Code.exe", "chrome.exe"],   # lista deduplicada
    "titulo_mas_frecuente": "main.py - proyecto",
    "total_cambios_ventana": 12,
    "cambios_ventana_por_minuto": 1.2,           # total / duracion
    "ritmo_escritura_promedio": 45,              # teclas/min
    "hora_del_dia": "14:30",
    "bateria": 78,                               # None si no disponible
    "app_dominante": "Code.exe"                  # la más frecuente
}
```

### Registro Atlas (en ia_recuerdos.json, clave `atlas_situacional`)

```python
{
    "atlas_situacional": [
        {
            "timestamp": "2024-01-15T14:30:00",
            "hora_franja": "14:30",              # para búsqueda ±30min
            "apps_unicas": ["Code.exe"],
            "app_dominante": "Code.exe",
            "ritmo_escritura_promedio": 45,
            "resumen_semantico": "Camila estaba en modo técnico"
        }
        # máximo 7 días de registros
    ]
}
```

### Historial de Frecuencia de Apps (en memoria de sesión)

```python
# collections.Counter en SemanticLayer
app_frequency: Counter = Counter({
    "Code.exe": 8,
    "chrome.exe": 3,
    "explorer.exe": 1
})
```

---

## Correctness Properties

*Una propiedad es una característica o comportamiento que debe mantenerse verdadero en todas las ejecuciones válidas del sistema — esencialmente, una declaración formal sobre lo que el sistema debe hacer. Las propiedades sirven como puente entre especificaciones legibles por humanos y garantías de corrección verificables por máquina.*

### Property 1: Invariante de capacidad del Silent_Buffer

*Para cualquier* secuencia de eventos insertados en el Silent_Buffer, la cantidad de eventos almacenados nunca debe exceder 500, y los eventos retenidos deben ser siempre los más recientes (política FIFO).

**Validates: Requirements 1.3, 1.4**

---

### Property 2: Round-trip del método vaciar()

*Para cualquier* conjunto de eventos almacenados en el Silent_Buffer, llamar a `vaciar()` debe retornar exactamente esos eventos en orden de inserción, y el buffer debe quedar con longitud 0 inmediatamente después.

**Validates: Requirements 1.5**

---

### Property 3: Integridad de campos del evento registrado

*Para cualquier* evento registrado en el Silent_Buffer con tipo y datos arbitrarios, el evento almacenado debe contener los campos `timestamp`, `tipo` y `datos`, donde `timestamp` es un string ISO 8601 válido.

**Validates: Requirements 1.2**

---

### Property 4: Corrección del cálculo de ritmo de escritura

*Para cualquier* lista de timestamps de teclas presionadas y un período de tiempo dado, el ritmo calculado en teclas por minuto debe ser igual a `len(timestamps) / duracion_minutos`, con tolerancia de ±0.01.

**Validates: Requirements 2.2**

---

### Property 5: Resiliencia ante datos no disponibles

*Para cualquier* combinación de datos del sistema no disponibles (batería, título de ventana, app activa), el Context_Monitor no debe lanzar excepción y debe omitir los campos faltantes del snapshot.

**Validates: Requirements 2.5**

---

### Property 6: Completitud y tamaño del State_Vector

*Para cualquier* lista no vacía de eventos del Silent_Buffer, el State_Vector generado debe: (a) contener todos los campos requeridos por el modelo de datos, (b) ser serializable a JSON sin error, y (c) tener un tamaño en bytes menor o igual a 2048.

**Validates: Requirements 3.2, 3.3**

---

### Property 7: Corrección del campo cambios_ventana_por_minuto

*Para cualquier* State_Vector generado con `total_cambios_ventana = N` y `duracion_minutos = D` (D > 0), el campo `cambios_ventana_por_minuto` debe ser igual a `N / D` con tolerancia de ±0.01.

**Validates: Requirements 3.5**

---

### Property 8: Invariante del prompt — instrucciones obligatorias

*Para cualquier* State_Vector con `actividad_detectada = True`, el prompt construido por la Semantic_Layer debe contener simultáneamente: (a) la instrucción de voseo rioplatense, (b) la prohibición de verbos literales, y (c) la prohibición de lenguaje técnico.

**Validates: Requirements 7.3, 10.1, 10.2**

---

### Property 9: Traducción semántica por categoría de app

*Para cualquier* State_Vector cuya `app_dominante` pertenezca a una categoría semántica conocida (diseño, código, texto, navegador), el prompt generado debe contener la traducción semántica correspondiente a esa categoría.

**Validates: Requirements 7.1, 7.2**

---

### Property 10: Prompt de empatía ante condiciones nocturnas

*Para cualquier* State_Vector que cumpla simultáneamente: batería ≤ 20%, hora entre 22:00 y 02:00, y app dominante en categoría de trabajo, el prompt generado debe incluir el texto de empatía por cansancio.

**Validates: Requirements 7.4**

---

### Property 11: Detección de inactividad en historial de 3 ciclos

*Para cualquier* secuencia de 3 State_Vectors consecutivos donde la `app_dominante` es idéntica y `total_cambios_ventana` es 0 en todos, la función de detección de inactividad debe retornar `True`.

**Validates: Requirements 5.4**

---

### Property 12: Omisión de envío por ciclos idénticos

*Para cualquier* par de State_Vectors donde `app_dominante`, `titulo_mas_frecuente` y `ritmo_escritura_promedio` son idénticos, la función de comparación debe retornar que el ciclo debe ser omitido.

**Validates: Requirements 5.2**

---

### Property 13: Invariante de retención de 7 días en Atlas_Memory

*Para cualquier* secuencia de registros guardados en Atlas_Memory con fechas variadas, después de ejecutar `limpiar_antiguos()`, solo deben permanecer los registros con timestamp dentro de los últimos 7 días.

**Validates: Requirements 9.5, 9.6**

---

### Property 14: Round-trip de persistencia en Atlas_Memory

*Para cualquier* State_Vector guardado en Atlas_Memory, al leer el registro guardado debe contener los campos `timestamp`, `hora_franja`, `apps_unicas`, `app_dominante` y `resumen_semantico` con valores consistentes con el State_Vector original.

**Validates: Requirements 9.1**

---

### Property 15: Prompt de comparación temporal con registro anterior

*Para cualquier* par (registro_anterior, State_Vector_actual) donde ambos tienen datos válidos, el prompt generado debe incluir tanto el resumen del día anterior como el resumen actual.

**Validates: Requirements 9.3**

---

### Property 16: Detección de palabras clave de alta prioridad

*Para cualquier* string de título de ventana, la función de detección del Priority_Interrupt debe retornar `True` si y solo si el título contiene al menos una de las palabras clave definidas ("error", "fallo", "no responde", "detuvo"), sin distinguir mayúsculas/minúsculas.

**Validates: Requirements 6.1**

---

### Property 17: Detección de cambios de ventana excesivos

*Para cualquier* lista de timestamps de cambios de ventana, la función de detección debe retornar `True` si y solo si hay 20 o más timestamps dentro de cualquier ventana de 60 segundos consecutivos.

**Validates: Requirements 6.3**

---

### Property 18: Invariante del historial de State_Vectors

*Para cualquier* secuencia de N ciclos de reflexión (N > 3), el historial de State_Vectors mantenido por el Reflection_Timer debe contener exactamente 3 elementos (los más recientes).

**Validates: Requirements 5.3**

---

### Property 19: Personalidad basada en app dominante en sesión

*Para cualquier* historial de sesión donde VS Code (o cualquier editor de código) aparece como app dominante en los últimos 5 ciclos, el prompt generado debe incluir la referencia afectiva al código.

**Validates: Requirements 8.2**

---

### Property 20: Curiosidad ante app nueva

*Para cualquier* State_Vector cuya `app_dominante` no aparece en el historial de frecuencia de apps de la sesión actual, el prompt generado debe incluir la expresión de curiosidad genuina.

**Validates: Requirements 8.5**

---

## Error Handling

### Estrategia General

Todos los módulos nuevos siguen el principio de **graceful degradation**: ningún error interno debe propagarse al hilo principal de PyQt6 ni interrumpir la experiencia de Camila.

| Escenario | Comportamiento |
|---|---|
| psutil no disponible | Omitir campos de batería/CPU del snapshot |
| win32gui no disponible | Usar título de ventana vacío |
| LLM no responde en 15s | `asyncio.wait_for` con timeout, omitir ciclo silenciosamente |
| ia_recuerdos.json corrupto | Inicializar Atlas_Memory con lista vacía, no lanzar excepción |
| State_Vector > 2KB | Truncar `apps_unicas` y `titulo_mas_frecuente` hasta cumplir el límite |
| Thread del Context_Monitor falla | Reiniciar automáticamente con backoff de 30s |
| Priority_Interrupt durante ciclo activo | Usar `threading.Event` para señalizar al Reflection_Timer que reinicie |

### Manejo de Excepciones por Módulo

```python
# Patrón estándar en todos los threads
def _loop(self) -> None:
    while self._running:
        try:
            self._tick()
        except Exception as e:
            # Log silencioso, nunca propagar
            pass
        time.sleep(self._intervalo)
```

---

## Testing Strategy

### Enfoque Dual

Se usa una combinación de tests unitarios con ejemplos específicos y tests basados en propiedades (PBT) para las funciones puras del sistema.

**Librería PBT elegida**: `hypothesis` (Python) — madura, bien integrada con pytest, soporta generadores de datos estructurados.

### Tests Unitarios (pytest)

Cubren:
- Integración entre componentes (Context_Monitor → Silent_Buffer)
- Comportamiento del Reflection_Timer con mocks del LLM
- Casos edge: buffer vacío, LLM timeout, ia_recuerdos.json corrupto
- Mensaje exacto del Priority_Interrupt ante cambios excesivos

### Tests de Propiedades (hypothesis)

Cada propiedad del diseño se implementa como un test de hypothesis con mínimo 100 iteraciones. Configuración base:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@settings(max_examples=100)
@given(st.lists(st.text(), min_size=501, max_size=1000))
def test_property_1_buffer_capacity(eventos):
    # Feature: alisha-conciencia-situacional, Property 1: buffer capacity invariant
    buffer = SilentBuffer()
    for e in eventos:
        buffer.registrar("contexto", {"app": e})
    assert len(buffer) <= 500
```

### Cobertura por Módulo

| Módulo | Tipo de Test | Properties |
|---|---|---|
| `silent_buffer.py` | PBT + Unit | 1, 2, 3 |
| `context_monitor.py` | Unit + PBT | 4, 5 |
| `state_vector.py` | PBT | 6, 7 |
| `semantic_layer.py` | PBT | 8, 9, 10, 11, 12, 19, 20 |
| `atlas_memory.py` | PBT + Unit | 13, 14, 15 |
| `priority_interrupt.py` | PBT + Unit | 16, 17 |
| `reflection_timer.py` | Unit | 18 |

### Notas sobre PBT

- Los tests de `semantic_layer.py` son todos sobre funciones puras (construcción de prompts), ideales para PBT.
- Los tests de threading (Context_Monitor, Reflection_Timer) usan mocks y son example-based.
- El LLM se mockea en todos los tests; no se hacen llamadas reales a Ollama en el test suite.
