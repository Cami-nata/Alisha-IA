# 📋 Pendiente: Autoconciencia de Alisha — `self_awareness.py`

> Extraído de `.kiro/specs/ia-asistente-mejorado` (Fase 11, Tarea 20) antes de eliminar el spec.
> Estado: ❌ No implementado. El `self_awareness.py` actual es una versión parcial que no cumple estos requisitos.

---

## Contexto

La idea es que Alisha sepa **qué puede y qué no puede hacer** — no solo como texto en el system prompt, sino como un módulo que consulta sus capacidades reales en tiempo de ejecución y las inyecta en el contexto.

Esto es diferente a la memoria episódica (`agent_memory.py`) y al estado emocional (`emotion_engine.py`). Es **metacognición**: la IA tiene un modelo de sí misma.

---

## Requisito original (EARS format)

### Tarea 20 — Crear `self_awareness.py`

- [ ] **20.1** Implementar `cargar_aprendizaje_rl() -> dict`
  - Lee `models/self_awareness.json` si existe (generado por el simulador RL)
  - Si no existe, retorna dict vacío sin error

- [ ] **20.2** Implementar `obtener_capacidades() -> dict`
  - Combina habilidades del historial RL + capacidades del asistente
  - Fuentes: acciones disponibles en `tools.py`, expertise técnico de `ia_identidad.json`, habilidades entrenadas de `memory_db.py` (tabla `habilidades_entrenadas`)
  - Retorna estructura: `{"puede": [...], "no_puede": [...], "aprendiendo": [...]}`

- [ ] **20.3** Implementar `sabe_hacer(tarea: str) -> tuple[bool, str]`
  - Retorna `(puede_hacerlo, explicacion)` basado en capacidades conocidas
  - Ejemplo: `sabe_hacer("abrir Chrome")` → `(True, "Tengo la herramienta app_open")`
  - Ejemplo: `sabe_hacer("editar video")` → `(False, "No tengo herramientas de edición de video todavía")`

- [ ] **20.4** Implementar `obtener_limitaciones() -> list[str]`
  - Lista de cosas que Alisha sabe que no puede hacer bien todavía
  - Se construye dinámicamente desde: herramientas ausentes, errores frecuentes en historial, rechazos de sugerencias en `alisha_rechazos.json`

- [ ] **20.5** Integrar en `brain.py` → `PersonalitySynthesizer._generar_snapshot()`
  - Incluir sección de autoconciencia en el snapshot:
    ```
    [CAPACIDADES: puede=abrir_apps,buscar_web,leer_archivos | limitaciones=editar_video,control_brillo_avanzado]
    ```
  - Esto permite que Alisha responda honestamente cuando le preguntan qué puede hacer

- [ ] **20.6** Integrar en `web_app.py` → `_inicializar()`
  - Cargar autoconciencia al arrancar
  - Actualizar tras cada sesión (cuando se agregan nuevas habilidades entrenadas)

---

## Diferencia con el `self_awareness.py` actual

El archivo `self_awareness.py` que existe en el proyecto actualmente es una versión parcial que solo maneja datos del simulador RL (que fue abandonado). No implementa `sabe_hacer()`, `obtener_limitaciones()` ni la integración con `tools.py` y `memory_db.py`.

---

## Archivos a modificar cuando se implemente

| Archivo | Cambio |
|---------|--------|
| `self_awareness.py` | Reescribir completo con las 6 funciones |
| `brain.py` | Agregar capacidades al snapshot en `_generar_snapshot()` |
| `web_app.py` | Llamar `cargar_autoconciencia()` en `_inicializar()` |
| `memory_db.py` | Exponer `listar_habilidades()` para que self_awareness las lea |

---

## Prioridad sugerida

🟡 Media — No es bloqueante para el funcionamiento actual de Alisha, pero mejora significativamente la coherencia de sus respuestas cuando le preguntan sobre sus capacidades.

---

*Extraído el 2026-05-23 durante limpieza de specs huérfanos.*
