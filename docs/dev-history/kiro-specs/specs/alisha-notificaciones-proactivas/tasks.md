# Plan de Implementación: alisha-notificaciones-proactivas

## Overview

Implementación incremental del módulo `proactive_notifier.py` que extiende el sistema de Conciencia Situacional de Alisha para emitir notificaciones proactivas. Se construye de adentro hacia afuera: primero los guards y tipos, luego los triggers, luego los prompts, luego la orquestación central, y finalmente la integración con `ReflectionTimer` y `SituationalAwareness`.

## Tasks

- [x] 1. Crear estructura base: `NotificationType`, `SilenceGuard` y `AntiRepetitionGuard`
  - Crear `proactive_notifier.py` con el enum `NotificationType` (6 valores: task_reminder, night_alert, break_reminder, stress_detector, focus_motivator, context_shift)
  - Implementar `SilenceGuard` con atributo `_ultima_emision: datetime | None = None`, constante `VENTANA_MINUTOS = 30`, métodos `puede_emitir() -> bool` y `registrar_emision() -> None`
  - Implementar `AntiRepetitionGuard` con `__init__(self, ventana: int = 3)` usando `deque(maxlen=ventana)`, métodos `puede_emitir(tipo: str) -> bool`, `registrar_emision(tipo: str) -> None` y propiedad `historial -> list[str]`
  - Todos los errores internos deben ser silenciosos (fail-silent)
  - _Requirements: 1.6, 2.1, 2.2, 2.3, 2.5, 3.1, 3.2, 3.4, 3.5_

  - [ ]* 1.1 Escribir property test para `SilenceGuard` (Property 3)
    - **Property 3: Silence_Guard bloquea dentro de la ventana**
    - Crear `tests/test_proactive_notifier/test_silence_guard.py`
    - Usar `@given(minutos=st.floats(min_value=0, max_value=29.99))` para verificar que `puede_emitir()` retorna False cuando han pasado menos de 30 min
    - Usar `@given(minutos=st.floats(min_value=30.0, max_value=1440.0))` para verificar que retorna True cuando han pasado 30 min o más
    - **Validates: Requirements 2.2, 2.3**

  - [ ]* 1.2 Escribir property test para `AntiRepetitionGuard` (Property 4)
    - **Property 4: Anti_Repetition_Guard — historial circular y bloqueo**
    - Crear `tests/test_proactive_notifier/test_anti_repetition_guard.py`
    - Verificar que `puede_emitir(tipo)` retorna False si y solo si `tipo` está en los últimos N tipos registrados
    - Verificar que el historial contiene exactamente los últimos N tipos (o menos si se emitieron menos de N)
    - Verificar que con `ventana=3` y 4 emisiones, el tipo más antiguo ya no bloquea
    - **Validates: Requirements 3.1, 3.2, 3.4**

- [x] 2. Implementar funciones de evaluación de triggers
  - Implementar `evaluar_task_reminder(recordatorios: list[dict]) -> dict | None` — retorna el recordatorio con fecha más próxima dentro de 2 días; acepta campos `"fecha"`, `"date"`, `"vencimiento"`, `"deadline"`; ignora silenciosamente recordatorios sin fecha parseable
  - Implementar `evaluar_night_alert(sv: dict) -> bool` — True si `hora_del_dia >= 23:00` (usar campo del StateVector)
  - Implementar `evaluar_break_reminder(ultima_inactividad: datetime | None) -> bool` — True si han pasado >= 90 min desde `ultima_inactividad`; retorna False si `ultima_inactividad` es None
  - Implementar `evaluar_stress_detector(sv: dict) -> bool` — True si `cambios_ventana_por_minuto > 3` AND `hora_del_dia >= 22:00` AND (`bateria <= 20` OR `bateria` no está en sv)
  - Implementar `evaluar_focus_motivator(historial_svs: list[dict]) -> bool` — True si los últimos 3 SVs tienen la misma `app_dominante` y `ritmo_escritura_promedio > 20`; retorna False si hay menos de 3 SVs
  - Implementar `evaluar_context_shift(sv: dict, registro_anterior: dict | None) -> bool` — True si `registro_anterior` no es None y `resumen_semantico` difiere del sv actual
  - _Requirements: 4.1–4.6, 5.1, 5.3, 6.1–6.5, 7.1, 7.2, 8.1, 9.1, 9.4_

  - [ ]* 2.1 Escribir property test para `evaluar_task_reminder` (Property 5)
    - **Property 5: Task_Reminder activa con fechas en rango**
    - Crear `tests/test_proactive_notifier/test_task_reminder.py`
    - Verificar que retorna el recordatorio más próximo cuando hay al menos uno dentro de 2 días
    - Verificar que retorna None cuando no hay recordatorios en rango o la lista está vacía
    - **Validates: Requirements 4.2, 4.4**

  - [ ]* 2.2 Escribir property test para `evaluar_night_alert` (Property 6)
    - **Property 6: Night_Alert activa exactamente en horario nocturno**
    - Crear `tests/test_proactive_notifier/test_night_alert.py`
    - Usar `@given` con horas en [23, 23] y [0, 2] para verificar True; horas en [3, 22] para verificar False
    - **Validates: Requirements 5.1**

  - [ ]* 2.3 Escribir property test para `evaluar_break_reminder` (Property 7)
    - **Property 7: Break_Reminder activa exactamente al superar 90 minutos**
    - Crear `tests/test_proactive_notifier/test_break_reminder.py`
    - Usar `@given(minutos=st.floats(min_value=90.0, max_value=480.0))` para verificar True
    - Usar `@given(minutos=st.floats(min_value=0.0, max_value=89.99))` para verificar False
    - **Validates: Requirements 6.2**

  - [ ]* 2.4 Escribir property test para `evaluar_stress_detector` (Property 8)
    - **Property 8: Stress_Detector activa con la conjunción correcta de condiciones**
    - Crear `tests/test_proactive_notifier/test_stress_detector.py`
    - Verificar True solo cuando se cumplen las tres condiciones simultáneamente
    - Verificar False cuando falta cualquiera de las condiciones
    - Verificar que batería None cuenta como condición cumplida
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 2.5 Escribir property test para `evaluar_focus_motivator` (Property 9)
    - **Property 9: Focus_Motivator activa con concentración sostenida**
    - Crear `tests/test_proactive_notifier/test_focus_motivator.py`
    - Verificar True cuando los últimos 3 SVs tienen misma `app_dominante` y `ritmo_escritura_promedio > 20`
    - Verificar False si cualquier condición falla en alguno de los 3 SVs o hay menos de 3
    - **Validates: Requirements 8.1**

  - [ ]* 2.6 Escribir property test para `evaluar_context_shift` (Property 10)
    - **Property 10: Context_Shift activa con resúmenes semánticos diferentes**
    - Crear `tests/test_proactive_notifier/test_context_shift.py`
    - Verificar True cuando ambos resúmenes son strings no vacíos y diferentes
    - Verificar False cuando son iguales o `registro_anterior` es None
    - **Validates: Requirements 9.1**

- [x] 3. Checkpoint — Verificar que todos los tests de triggers pasan
  - Asegurar que todos los tests pasan, consultar al usuario si hay dudas.

- [x] 4. Implementar constructores de prompts
  - Implementar `prompt_task_reminder(recordatorio: dict) -> str` — incluye título y proximidad de la entrega; instrucción de hablar del significado emocional, no de la fecha exacta
  - Implementar `prompt_night_alert() -> str` — instrucción de expresar preocupación por el cansancio, sin mencionar la hora ni la palabra "tarde"
  - Implementar `prompt_break_reminder() -> str` — instrucción de sugerir un descanso sin mencionar minutos ni la palabra "descanso"
  - Implementar `prompt_stress_detector() -> str` — instrucción de expresar preocupación empática sin enumerar señales técnicas
  - Implementar `prompt_focus_motivator() -> str` — instrucción de felicitar por concentración sin mencionar app ni tiempo
  - Implementar `prompt_context_shift(resumen_ayer: str, resumen_hoy: str) -> str` — incluye ambos resúmenes; instrucción de comentar el contraste con curiosidad
  - Todos los prompts deben incluir el bloque de estilo obligatorio: voseo rioplatense, máximo 2 oraciones, prohibido datos técnicos
  - _Requirements: 4.3, 5.2, 6.3, 7.3, 7.4, 8.2, 8.3, 9.2, 9.3, 10.1, 10.2, 10.3_

  - [ ]* 4.1 Escribir property test para el bloque de estilo en todos los prompts (Property 11)
    - **Property 11: Todos los prompts contienen el bloque de estilo obligatorio**
    - Crear `tests/test_proactive_notifier/test_prompt_style.py`
    - Para cada tipo de notificación, verificar que el prompt contiene: instrucción de voseo rioplatense, instrucción de máximo 2 oraciones, instrucción de prohibir datos técnicos
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 5. Implementar `truncar_a_2_oraciones` y llamada al LLM
  - Implementar `truncar_a_2_oraciones(texto: str) -> str` — retorna las primeras 2 oraciones si hay más de 2; retorna el texto sin modificar si hay 2 o menos; manejar puntuación española (`.`, `!`, `?`)
  - Implementar función interna `_llamar_llm(prompt: str) -> str | None` en `ProactiveNotifier` — POST a `http://localhost:11434/api/generate` con modelo `llama3.1`, timeout 15s, retorna None en timeout o error
  - _Requirements: 1.5, 10.4, 10.5_

  - [ ]* 5.1 Escribir property test para `truncar_a_2_oraciones` (Property 12)
    - **Property 12: Truncado a 2 oraciones**
    - Crear `tests/test_proactive_notifier/test_truncar.py`
    - Usar `@given` con textos de N oraciones donde N > 2 para verificar que retorna exactamente 2
    - Verificar que textos con N ≤ 2 oraciones no se modifican
    - **Validates: Requirements 10.4**

- [x] 6. Implementar la clase `ProactiveNotifier` (orquestador central)
  - Implementar `ProactiveNotifier.__init__()` — instancia `SilenceGuard`, `AntiRepetitionGuard(ventana=3)`, inicializa `_ultima_inactividad: datetime | None = None`
  - Implementar `ProactiveNotifier.evaluar(sv, atlas, historial_svs, callback) -> bool`:
    1. Verificar `SilenceGuard.puede_emitir()` — si False, retornar False
    2. Leer `ia_recuerdos.json` y evaluar triggers en orden de prioridad (task_reminder → stress_detector → night_alert → break_reminder → focus_motivator → context_shift)
    3. Para cada trigger que se active, verificar `AntiRepetitionGuard.puede_emitir(tipo)` — si bloqueado, pasar al siguiente
    4. Construir prompt del trigger seleccionado
    5. Llamar al LLM con timeout 15s
    6. Si LLM retorna texto: truncar a 2 oraciones, invocar callback, registrar en guards, retornar True
    7. Si LLM falla o retorna vacío: retornar False
    8. Si ningún trigger pasa los guards: retornar False
  - Implementar `ProactiveNotifier.actualizar_inactividad(sv: dict) -> None` — actualiza `_ultima_inactividad` si `actividad_detectada` es False o `ritmo_escritura_promedio == 0`
  - Todo el método `evaluar()` envuelto en try/except que silencia cualquier excepción
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.1, 4.4, 6.4_

  - [ ]* 6.1 Escribir property test para prioridad de triggers (Property 1)
    - **Property 1: Prioridad de triggers**
    - Crear `tests/test_proactive_notifier/test_priority.py`
    - Construir StateVectors que activen múltiples triggers simultáneamente
    - Verificar que el tipo emitido corresponde al trigger de mayor prioridad no bloqueado por Anti_Repetition_Guard
    - **Validates: Requirements 1.2**

  - [ ]* 6.2 Escribir property test para registro de emisión (Property 2)
    - **Property 2: Registro de emisión**
    - Crear `tests/test_proactive_notifier/test_registro_emision.py`
    - Verificar que después de cualquier emisión, el tipo aparece en el historial del Anti_Repetition_Guard y el timestamp está actualizado en el Silence_Guard
    - **Validates: Requirements 1.6**

- [x] 7. Checkpoint — Verificar que todos los tests del orquestador pasan
  - Asegurar que todos los tests pasan, consultar al usuario si hay dudas.

- [x] 8. Agregar hook `conectar_proactive_notifier` a `ReflectionTimer`
  - En `ReflectionTimer.__init__()`, agregar: `self._proactive_notifier: ProactiveNotifier | None = None`
  - Agregar método `conectar_proactive_notifier(self, notifier: ProactiveNotifier) -> None` que asigna `self._proactive_notifier = notifier`
  - En `ReflectionTimer._tick()`, al inicio (antes del paso 1 actual), agregar el bloque:
    ```python
    if self._proactive_notifier is not None:
        try:
            sv_previo = generar_state_vector(self._buffer.ver_sin_vaciar() if hasattr(self._buffer, 'ver_sin_vaciar') else [])
            emitido = self._proactive_notifier.evaluar(
                sv_previo, self._atlas, list(self._historial_svs), self._callback
            )
            self._proactive_notifier.actualizar_inactividad(sv_previo)
            if emitido:
                return
        except Exception:
            pass
    ```
  - No modificar ninguna otra lógica existente de `reflection_timer.py`
  - _Requirements: 1.2, 6.4_

  - [ ]* 8.1 Escribir tests de integración para `ReflectionTimer` + `ProactiveNotifier`
    - Crear `tests/test_proactive_notifier/test_integration.py`
    - Verificar que `conectar_proactive_notifier()` conecta correctamente el notifier
    - Verificar con mock del LLM que cuando el notifier emite, `_tick()` retorna sin ejecutar la reflexión situacional
    - Verificar que cuando el notifier no emite (Silence_Guard bloqueado), `_tick()` continúa normalmente
    - Verificar que si el notifier lanza excepción, `_tick()` continúa sin error
    - _Requirements: 1.2, 2.4_

- [x] 9. Integrar `ProactiveNotifier` en `SituationalAwareness`
  - En `situational_awareness.py`, agregar import: `from proactive_notifier import ProactiveNotifier`
  - En `SituationalAwareness.__init__()`, agregar: `self._proactive_notifier: ProactiveNotifier | None = None`
  - En `SituationalAwareness.iniciar()`, después de iniciar el `ReflectionTimer`, agregar:
    ```python
    try:
        self._proactive_notifier = ProactiveNotifier()
        if self._reflection_timer is not None:
            self._reflection_timer.conectar_proactive_notifier(self._proactive_notifier)
    except Exception as e:
        logger.debug("ProactiveNotifier no pudo iniciar: %s", e)
        self._proactive_notifier = None
    ```
  - En `SituationalAwareness.detener()`, agregar `self._proactive_notifier = None` al final del método
  - _Requirements: 1.1_

- [x] 10. Crear `tests/test_proactive_notifier/__init__.py` y tests de ejemplo
  - Crear `tests/test_proactive_notifier/__init__.py` (vacío)
  - Crear `tests/test_proactive_notifier/test_integration.py` con tests de ejemplo:
    - Smoke test: verificar que `proactive_notifier` importa sin error
    - Verificar que el callback es llamado con el texto del LLM (mock de requests)
    - Verificar que el callback NO es llamado cuando el LLM hace timeout (mock de requests)
    - Verificar que el prompt de Night_Alert no contiene la hora exacta ni la palabra "tarde"
    - Verificar que el prompt de Break_Reminder no contiene "descanso" ni números de minutos
    - Verificar que `ProactiveNotifier` + `ReflectionTimer` funcionan juntos con mock del LLM
  - _Requirements: 1.3, 1.4, 1.5, 5.2, 6.3_

- [x] 11. Checkpoint final — Verificar que toda la suite de tests pasa
  - Ejecutar `python -m pytest tests/test_proactive_notifier/ -v` y asegurar que todos los tests pasan.
  - Consultar al usuario si hay algún test fallando o comportamiento inesperado.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints garantizan validación incremental antes de continuar
- Los property tests usan Hypothesis con `@settings(max_examples=100)`
- El módulo `proactive_notifier.py` vive en la raíz del proyecto (junto a `reflection_timer.py`)
- Los tests viven en `tests/test_proactive_notifier/`
- `reflection_timer.py` solo recibe el hook mínimo; no se modifica ninguna lógica existente
