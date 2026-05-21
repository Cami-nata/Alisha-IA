# Plan de Implementación: alisha-escepticismo-ironia

## Overview

Implementar `skepticism_engine.py` como módulo Python independiente con integración opcional fail-silent en `ia.py`. El módulo detecta contradicciones entre lo que Camila dice y lo que hace (apps activas), escala el sarcasmo por sesión, ajusta la dopamina del EmotionEngine y persiste el estado en `ia_recuerdos.json`.

## Tasks

- [x] 1. Crear estructura base de `skepticism_engine.py` con listas de palabras clave y categorías de apps
  - Crear el archivo `skepticism_engine.py` en la raíz del proyecto
  - Definir las constantes `_PALABRAS_TRABAJO`, `_PALABRAS_DESCANSO`, `_PALABRAS_TERMINADO`, `_PALABRAS_SIN_TIEMPO`
  - Definir `_APPS_ENTRETENIMIENTO`, `_APPS_CREATIVAS`, `_APPS_EXPLORADOR`, `_APPS_CV`
  - Importar `_APPS_CODIGO`, `_APPS_DISEÑO`, `_APPS_TEXTO_CV` desde `semantic_layer.py` con fallback a sets vacíos si el import falla
  - _Requirements: 1.1, 2.2, 2.3, 7.1, 7.2, 7.3_

- [x] 2. Implementar `ContradictionMemory` con persistencia en `ia_recuerdos.json`
  - [x] 2.1 Implementar la clase `ContradictionMemory` con `_contador` y `_tipos` como estado de sesión
    - Métodos: `incrementar(tipo)`, `get_contador()`, `guardar()`, `cargar_sesion_anterior()`
    - `guardar()` lee el archivo completo antes de escribir para preservar todas las claves existentes
    - `cargar_sesion_anterior()` retorna 0 si el archivo no existe o tiene formato inválido (fail-silent)
    - Instanciar el singleton `_memory = ContradictionMemory()` a nivel de módulo
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 10.1, 10.2, 10.4, 10.5_

  - [ ]* 2.2 Escribir property test: Persistencia preserva claves existentes (Property 9)
    - **Property 9: Persistencia preserva claves existentes del archivo**
    - Usar `@given` con `n=st.integers(min_value=0, max_value=10)`, `tipos` y `claves_extra` con `recuerdos` y `temas`
    - Verificar que después de `guardar()` todas las claves preexistentes siguen presentes con valores intactos
    - Usar archivo temporal (`tmp_path`) para no tocar `ia_recuerdos.json` real
    - **Validates: Requirements 10.4, 3.2**

  - [ ]* 2.3 Escribir property test: Round-trip de persistencia (Property 10)
    - **Property 10: Round-trip de persistencia de contradicciones**
    - Usar `@given(n=st.integers(min_value=0, max_value=50), tipos=st.lists(st.text()))`
    - Verificar que `cargar_sesion_anterior()` retorna exactamente N después de `guardar()` con N contradicciones
    - Usar archivo temporal para aislamiento
    - **Validates: Requirements 10.1, 10.2, 3.2**

- [x] 3. Implementar `_calcular_nivel_sarcasmo()` como función pura
  - Función pura sin efectos secundarios: `0→0`, `1-2→1`, `3-4→2`, `>=5→3`
  - _Requirements: 4.1_

  - [ ]* 3.1 Escribir property test: Nivel de sarcasmo es función pura del contador (Property 6)
    - **Property 6: Nivel de sarcasmo es función pura del contador**
    - Usar `@given(n=st.integers(min_value=0, max_value=20))`
    - Verificar la tabla de mapeo exacta para todos los valores posibles
    - **Validates: Requirements 4.1**

- [x] 4. Implementar `_detectar_contradiccion()` con comparación de palabras clave vs apps activas
  - Comparar mensaje (case-insensitive) contra `_PALABRAS_TRABAJO`, `_PALABRAS_DESCANSO`, `_PALABRAS_TERMINADO`, `_PALABRAS_SIN_TIEMPO`
  - Comparar apps activas (case-insensitive, incluyendo títulos de ventana) contra las categorías de apps
  - Retornar `(bool, str | None)` — nunca lanzar excepción
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 4.1 Escribir property test: Detección trabajo vs entretenimiento (Property 3)
    - **Property 3: Detección de contradicción trabajo vs entretenimiento**
    - Usar `@given` con keyword de `_PALABRAS_TRABAJO` y app de `_APPS_ENTRETENIMIENTO`
    - Verificar `contradiccion_detectada=True` y `tipo="trabajo_vs_entretenimiento"`
    - **Validates: Requirements 2.2**

  - [ ]* 4.2 Escribir property test: Detección descanso vs trabajo (Property 4)
    - **Property 4: Detección de contradicción descanso vs trabajo**
    - Usar `@given` con keyword de `_PALABRAS_DESCANSO` y app de las apps de código/trabajo
    - Verificar `contradiccion_detectada=True` y `tipo="descanso_vs_trabajo"`
    - **Validates: Requirements 2.3**

  - [ ]* 4.3 Escribir property test: No falsos positivos en mensajes neutros (Property 5)
    - **Property 5: No falsos positivos en mensajes neutros**
    - Usar `@given` con texto que no contenga ninguna palabra clave y apps neutras
    - Verificar `contradiccion_detectada=False`
    - **Validates: Requirements 2.6**

- [x] 5. Implementar `_calcular_ajuste_dopamina()` con los tres valores posibles
  - `+0.15` si hay consistencia trabajo/estudio con apps de trabajo
  - `-0.10` si hay contradicción detectada
  - `0.0` en cualquier otro caso
  - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 5.1 Escribir property test: ajuste_dopamina toma exactamente uno de tres valores (Property 8)
    - **Property 8: ajuste_dopamina toma exactamente uno de tres valores**
    - Usar `@given(mensaje=st.text(), apps=st.lists(st.text()))`
    - Verificar que el resultado es exactamente `+0.15`, `-0.10` o `0.0`
    - **Validates: Requirements 5.3**

- [x] 6. Implementar `_evaluar_independencia()` consultando AtlasMemory
  - Consultar AtlasMemory para la franja horaria actual del día anterior
  - Retornar cláusula de prompt si hay contradicción temporal, `""` si no hay registro o falla
  - Nunca lanzar excepción (fail-silent)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Implementar `_evaluar_preferencias()` con reacciones de Alisha ante apps específicas
  - Evaluar `_APPS_CREATIVAS` → instrucción de entusiasmo creativo
  - Evaluar `_APPS_EXPLORADOR` → instrucción de tedio
  - Evaluar `_APPS_CV` con hora > 22:00 → instrucción de empatía nocturna
  - Retornar como máximo 1 cláusula por invocación, `""` si lista vacía o None
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 8. Implementar la función pública `evaluar()` ensamblando todos los componentes
  - Invocar en orden: `_detectar_contradiccion`, `_memory.incrementar`, `_calcular_nivel_sarcasmo`, `_calcular_ajuste_dopamina`, `_evaluar_independencia`, `_evaluar_preferencias`
  - Ensamblar `clausula_prompt` con: instrucción base de voseo rioplatense + instrucción de nivel de sarcasmo + cláusulas de dopamina (req 5.4, 5.5) + cláusula de independencia + cláusula de preferencias + ejemplos de tono (req 8.3, 8.4)
  - Envolver toda la lógica en `try/except Exception` y retornar el dict seguro en caso de error
  - Aplicar `ajuste_dopamina` al `emotion_engine` recibido como parámetro
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 4.2, 4.3, 4.4, 4.5, 5.4, 5.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1_

  - [ ]* 8.1 Escribir property test: Estructura del diccionario de retorno (Property 1)
    - **Property 1: Estructura del diccionario de retorno**
    - Usar `@given(mensaje=st.text(), apps=st.lists(st.text()))`
    - Verificar que el dict tiene exactamente los 5 campos con los tipos correctos y `nivel_sarcasmo` entre 0 y 3
    - **Validates: Requirements 1.3**

  - [ ]* 8.2 Escribir property test: Robustez ante entradas arbitrarias (Property 2)
    - **Property 2: Robustez ante entradas arbitrarias**
    - Usar `@given(mensaje=st.one_of(st.text(), st.just("")), apps=st.lists(st.text()))`
    - Verificar que nunca lanza excepción y siempre retorna dict válido
    - **Validates: Requirements 1.5, 9.4**

  - [ ]* 8.3 Escribir property test: clausula_prompt con instrucciones de tono humano (Property 11)
    - **Property 11: clausula_prompt con contradicción siempre incluye instrucciones de tono humano**
    - Usar `@given` con mensajes que contengan palabras clave de trabajo y apps de entretenimiento
    - Verificar que cuando `contradiccion_detectada=True`, `clausula_prompt` contiene voseo rioplatense y límite de 2 oraciones
    - **Validates: Requirements 8.1, 8.2**

  - [ ]* 8.4 Escribir property test: clausula_prompt contiene instrucción de tono por nivel (Property 7)
    - **Property 7: clausula_prompt contiene instrucción de tono para cada nivel**
    - Usar `@given` con combinaciones que produzcan cada nivel de sarcasmo (0–3)
    - Verificar que `clausula_prompt` contiene la instrucción correspondiente al nivel
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

- [x] 9. Checkpoint — Verificar que todos los tests pasan
  - Ejecutar `pytest tests/test_skepticism_engine/ -v` y confirmar que todos los tests pasan
  - Verificar que `skepticism_engine.py` no tiene errores de importación
  - Asegurar que el singleton `_memory` se inicializa correctamente al importar el módulo
  - Preguntar al usuario si hay dudas antes de continuar con la integración

- [x] 10. Integrar `skepticism_engine` en `ia.py` como importación opcional fail-silent
  - Agregar el bloque de integración en `procesar_turno()` de `ia.py`, justo antes de llamar a `preguntar_ia()`
  - El bloque usa `try/except Exception: pass` en el nivel exterior para garantizar fail-silent total
  - Obtener `_apps` desde `obtener_contexto_pantalla()` con su propio `try/except` interior
  - Inyectar `_clausula_escepticismo` al prompt si no está vacía (concatenar con `"\n\n"`)
  - Aplicar `_ajuste_dopamina_escepticismo` al `emo` usando `registrar_exito_rl()` o `registrar_fracaso_rl()` según el signo
  - No modificar ninguna otra lógica existente de `ia.py`
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.1 Escribir tests de ejemplo para la integración con ia.py
    - Test: `evaluar()` con `apps_activas=[]` retorna dict seguro sin excepción
    - Test: con `ia_recuerdos.json` inexistente, `cargar_sesion_anterior()` retorna 0
    - Test: con `contradicciones_ultima_sesion=4`, `clausula_prompt` del primer mensaje contiene referencia irónica
    - Test: con `dopamina=0.2` y `nivel_sarcasmo=2`, `clausula_prompt` contiene instrucción de fastidio
    - Test: con `dopamina=0.8` y sin contradicción, `clausula_prompt` contiene instrucción de satisfacción
    - _Requirements: 1.4, 3.3, 5.4, 5.5_

- [x] 11. Checkpoint final — Verificar integración completa
  - Ejecutar `pytest tests/test_skepticism_engine/ -v --tb=short` y confirmar que todos los tests pasan
  - Verificar que `ia.py` importa sin errores con `python -c "import ia"`
  - Confirmar que si se elimina `skepticism_engine.py`, `ia.py` sigue funcionando normalmente (fail-silent)
  - Preguntar al usuario si hay dudas antes de dar por terminada la implementación

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Todos los errores deben ser silenciosos (fail-silent) — ningún componente puede romper el flujo de `ia.py`
- El singleton `_memory` se instancia a nivel de módulo para preservar el estado entre llamadas dentro de la misma sesión
- Los tests de propiedad usan Hypothesis (ya presente en el proyecto en `.hypothesis/`)
- La integración con `ia.py` es el único punto de contacto externo — el módulo no modifica ningún otro archivo
- Los tests van en `tests/test_skepticism_engine/` con un `__init__.py` vacío y un archivo `test_skepticism_engine.py`
