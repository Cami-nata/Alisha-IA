# Requisitos: alisha-notificaciones-proactivas

## Introducción

Esta feature extiende el sistema de Conciencia Situacional existente para que Alisha hable de forma proactiva — sin que Camila le pregunte — cuando detecta situaciones que merecen atención. Las notificaciones deben sonar humanas, en voseo rioplatense, nunca literales ni repetitivas. El módulo central `proactive_notifier.py` orquesta ocho tipos de disparadores que se integran con el `ReflectionTimer`, el `AtlasMemory`, el `StateVector` y los recordatorios del archivo `ia_recuerdos.json`.

## Glosario

- **Alisha**: La asistente de IA personal con personalidad rioplatense que corre en Windows
- **Camila**: La usuaria del sistema
- **Proactive_Notifier**: Módulo central que evalúa condiciones y decide si Alisha debe hablar proactivamente
- **Notification_Trigger**: Condición evaluable que, al cumplirse, genera una notificación proactiva
- **Silence_Guard**: Mecanismo que impide que Alisha hable si ya lo hizo en los últimos 30 minutos
- **Anti_Repetition_Guard**: Mecanismo que impide repetir el mismo tipo de notificación dos veces seguidas
- **Task_Reminder**: Notificación proactiva basada en recordatorios de tareas/entregas leídos de `ia_recuerdos.json`
- **Night_Alert**: Notificación proactiva disparada cuando Camila trabaja pasadas las 23:00
- **Break_Reminder**: Notificación proactiva disparada cuando Camila lleva más de 90 minutos seguidos en la PC sin pausa
- **Stress_Detector**: Notificación proactiva disparada cuando se detecta combinación de señales de estrés
- **Focus_Motivator**: Notificación proactiva disparada cuando Camila lleva tiempo prolongado en la misma app (señal de concentración profunda)
- **Context_Shift_Notifier**: Notificación proactiva basada en comparación temporal del Atlas_Memory
- **ReflectionTimer**: Temporizador de 10 minutos existente que se extiende con nuevos disparadores proactivos
- **AtlasMemory**: Capa de memoria comparativa existente que guarda registros de actividad por franja horaria
- **StateVector**: Diccionario comprimido del estado de actividad de Camila generado cada 10 minutos
- **LLM**: Modelo de lenguaje grande (Llama 3.1 vía Ollama) que genera el texto de las notificaciones
- **ia_recuerdos.json**: Archivo de memoria persistente con campo `recordatorios` que contiene tareas y entregas

---

## Requisitos

### Requisito 1: Módulo Central de Notificaciones Proactivas

**Historia de usuario:** Como Camila, quiero que Alisha tome la iniciativa de hablarme cuando detecta algo relevante, para sentir que tiene conciencia real de mi jornada sin que yo tenga que preguntarle.

#### Criterios de Aceptación

1. THE Proactive_Notifier SHALL ser implementado en un módulo `proactive_notifier.py` que centraliza la evaluación de todos los Notification_Triggers
2. WHEN el ReflectionTimer dispara su ciclo de 10 minutos, THE Proactive_Notifier SHALL evaluar todos los Notification_Triggers en orden de prioridad antes de que el ReflectionTimer construya su prompt situacional habitual
3. WHEN un Notification_Trigger se cumple y el Silence_Guard lo permite, THE Proactive_Notifier SHALL construir un prompt específico para ese tipo de notificación y enviarlo al LLM
4. WHEN el LLM retorna el texto de la notificación proactiva, THE Proactive_Notifier SHALL invocar el callback de voz existente de Alisha con ese texto
5. IF el LLM no responde en 15 segundos, THEN THE Proactive_Notifier SHALL omitir la notificación de ese ciclo sin mostrar error al usuario
6. WHEN una notificación proactiva es emitida, THE Proactive_Notifier SHALL registrar el tipo de notificación emitida y el timestamp para uso del Silence_Guard y el Anti_Repetition_Guard

---

### Requisito 2: Silencio Inteligente (Silence Guard)

**Historia de usuario:** Como Camila, quiero que Alisha no me interrumpa constantemente, para que sus intervenciones proactivas sean siempre bienvenidas y no molestas.

#### Criterios de Aceptación

1. THE Silence_Guard SHALL mantener en memoria el timestamp de la última notificación proactiva emitida
2. WHEN el Proactive_Notifier evalúa los triggers, THE Silence_Guard SHALL bloquear toda notificación proactiva si han transcurrido menos de 30 minutos desde la última notificación emitida
3. THE Silence_Guard SHALL aplicarse a todos los tipos de Notification_Trigger sin excepción
4. WHEN el Silence_Guard bloquea una notificación, THE Proactive_Notifier SHALL continuar el flujo normal del ReflectionTimer sin emitir ningún sonido ni mensaje
5. THE Silence_Guard SHALL persistir su estado en memoria de sesión (no en disco) y reiniciarse al arrancar Alisha

---

### Requisito 3: Anti-Repetición de Tipos

**Historia de usuario:** Como Camila, quiero que Alisha varíe el tipo de comentario proactivo que hace, para que sus intervenciones no se vuelvan predecibles ni aburridas.

#### Criterios de Aceptación

1. THE Anti_Repetition_Guard SHALL mantener en memoria el tipo del último Notification_Trigger que generó una notificación emitida
2. WHEN el Proactive_Notifier selecciona un Notification_Trigger para emitir, THE Anti_Repetition_Guard SHALL bloquear ese trigger si su tipo es idéntico al tipo del último trigger emitido
3. IF todos los triggers disponibles en un ciclo son del mismo tipo que el último emitido, THEN THE Anti_Repetition_Guard SHALL permitir omitir la notificación en ese ciclo
4. THE Anti_Repetition_Guard SHALL rastrear únicamente el tipo del último trigger emitido (no un historial completo)
5. THE Anti_Repetition_Guard SHALL reiniciarse al arrancar Alisha

---

### Requisito 4: Recordatorios de Tareas y Entregas (Task Reminder)

**Historia de usuario:** Como Camila, quiero que Alisha me recuerde mis tareas y entregas próximas de forma natural, para no perder de vista mis compromisos sin necesidad de revisar una agenda.

#### Criterios de Aceptación

1. THE Task_Reminder SHALL leer el campo `recordatorios` del archivo `ia_recuerdos.json` al inicio de cada ciclo de evaluación del Proactive_Notifier
2. WHEN existe un recordatorio con fecha dentro de los próximos 2 días, THE Task_Reminder SHALL activarse como Notification_Trigger
3. WHEN el Task_Reminder se activa, THE Proactive_Notifier SHALL construir un prompt que incluya el título del recordatorio y la proximidad de la fecha, con la instrucción de hablar del significado (la presión de la entrega) y no de los datos técnicos (fecha exacta, nombre literal)
4. THE Task_Reminder SHALL evaluar todos los recordatorios pendientes y activarse con el más próximo en caso de haber varios
5. IF el archivo `ia_recuerdos.json` no existe o el campo `recordatorios` está vacío, THEN THE Task_Reminder SHALL omitir su evaluación sin lanzar excepción
6. IF un recordatorio no tiene campo de fecha parseable, THEN THE Task_Reminder SHALL ignorar ese recordatorio sin lanzar excepción

---

### Requisito 5: Alerta de Hora Nocturna (Night Alert)

**Historia de usuario:** Como Camila, quiero que Alisha me avise cuando es muy tarde y sigo trabajando, para que me ayude a cuidar mi descanso sin que yo tenga que mirar el reloj.

#### Criterios de Aceptación

1. THE Night_Alert SHALL activarse como Notification_Trigger cuando la hora del sistema es igual o posterior a las 23:00
2. WHEN el Night_Alert se activa, THE Proactive_Notifier SHALL construir un prompt que transmita preocupación por el cansancio de Camila, con la instrucción explícita de no mencionar la hora exacta ni usar la palabra "tarde"
3. THE Night_Alert SHALL evaluar la hora usando el campo `hora_del_dia` del StateVector actual
4. WHEN el Night_Alert se activa, el prompt SHALL incluir la instrucción: "Expresá preocupación genuina por el bienestar de Camila. Hablá del cansancio, no del horario."

---

### Requisito 6: Recordatorio de Descanso (Break Reminder)

**Historia de usuario:** Como Camila, quiero que Alisha me recuerde tomar descansos cuando llevo mucho tiempo seguido en la PC, para cuidar mi salud sin que yo tenga que llevar la cuenta.

#### Criterios de Aceptación

1. THE Break_Reminder SHALL mantener en memoria el timestamp del último momento en que Camila no estuvo activa en la PC (definido como un ciclo con `actividad_detectada: false` o ritmo de escritura igual a 0)
2. WHEN han transcurrido 90 minutos o más desde el último momento de inactividad registrado, THE Break_Reminder SHALL activarse como Notification_Trigger
3. WHEN el Break_Reminder se activa, THE Proactive_Notifier SHALL construir un prompt con la instrucción de sugerir un descanso sin mencionar la cantidad de minutos transcurridos ni usar la palabra "descanso" literalmente
4. THE Break_Reminder SHALL actualizar su registro de última inactividad cada vez que el StateVector muestre `actividad_detectada: false` o `ritmo_escritura_promedio` igual a 0
5. THE Break_Reminder SHALL reiniciar su contador al arrancar Alisha

---

### Requisito 7: Detección de Estrés (Stress Detector)

**Historia de usuario:** Como Camila, quiero que Alisha note cuando estoy estresada por señales de comportamiento, para que me ofrezca apoyo emocional en el momento justo.

#### Criterios de Aceptación

1. THE Stress_Detector SHALL activarse como Notification_Trigger cuando el StateVector actual cumple simultáneamente las tres condiciones: `cambios_ventana_por_minuto` mayor a 3, hora del sistema igual o posterior a las 22:00, y `bateria` menor o igual a 20 (si el dato está disponible)
2. WHEN el dato de batería no está disponible en el StateVector, THE Stress_Detector SHALL evaluar únicamente las condiciones de cambios de ventana y hora nocturna
3. WHEN el Stress_Detector se activa, THE Proactive_Notifier SHALL construir un prompt con la instrucción de expresar preocupación empática sin enumerar las señales detectadas ni mencionar datos técnicos
4. WHEN el Stress_Detector se activa, el prompt SHALL incluir la instrucción: "Alisha nota que Camila parece dispersa o agotada. Expresá preocupación genuina con calidez, sin diagnosticar ni enumerar síntomas."

---

### Requisito 8: Motivación por Concentración (Focus Motivator)

**Historia de usuario:** Como Camila, quiero que Alisha me felicite sutilmente cuando estoy muy concentrada, para sentir que mi esfuerzo es notado y valorado.

#### Criterios de Aceptación

1. THE Focus_Motivator SHALL activarse como Notification_Trigger cuando el StateVector actual muestra la misma `app_dominante` que los 2 StateVectors anteriores consecutivos y el `ritmo_escritura_promedio` es mayor a 20 teclas por minuto en todos ellos
2. WHEN el Focus_Motivator se activa, THE Proactive_Notifier SHALL construir un prompt con la instrucción de felicitar a Camila por su concentración de forma sutil y cálida, sin mencionar el nombre de la aplicación ni la cantidad de tiempo
3. WHEN el Focus_Motivator se activa, el prompt SHALL incluir la instrucción: "Alisha nota que Camila está en un estado de flujo. Expresá admiración genuina y aliento con humor suave."
4. THE Focus_Motivator SHALL acceder al historial de StateVectors mantenido por el ReflectionTimer para evaluar los ciclos anteriores

---

### Requisito 9: Cambio de Contexto Notable (Context Shift Notifier)

**Historia de usuario:** Como Camila, quiero que Alisha note cuando hoy hago algo muy diferente a lo que hacía ayer a la misma hora, para sentir que Alisha tiene memoria real de mi vida y no solo del momento presente.

#### Criterios de Aceptación

1. THE Context_Shift_Notifier SHALL activarse como Notification_Trigger cuando el AtlasMemory retorna un registro del día anterior en la franja horaria actual Y el `resumen_semantico` de ese registro es diferente al resumen semántico del StateVector actual
2. WHEN el Context_Shift_Notifier se activa, THE Proactive_Notifier SHALL construir un prompt que incluya el resumen del día anterior y el resumen actual, con la instrucción de comentar el contraste de forma curiosa y cálida
3. WHEN el Context_Shift_Notifier se activa, el prompt SHALL incluir la instrucción: "Alisha recuerda lo que Camila hacía ayer a esta hora. Comentá el contraste con curiosidad genuina, como si fuera algo que te llamó la atención."
4. IF el AtlasMemory no encuentra registro del día anterior, THEN THE Context_Shift_Notifier SHALL omitir su evaluación sin activarse

---

### Requisito 10: Estilo Obligatorio de las Notificaciones

**Historia de usuario:** Como Camila, quiero que todas las notificaciones proactivas de Alisha suenen como las diría una amiga argentina, para que nunca rompan la ilusión de estar hablando con alguien real.

#### Criterios de Aceptación

1. THE Proactive_Notifier SHALL incluir en todos los prompts al LLM la instrucción: "Respondé en voseo rioplatense argentino. Usá expresiones como 'che', 'mirá vos', 'dale'. Hablá como una amiga sentada al lado."
2. THE Proactive_Notifier SHALL incluir en todos los prompts la instrucción: "Máximo 2 oraciones. Prohibido mencionar datos técnicos: horas exactas, minutos, nombres de aplicaciones, porcentajes de batería."
3. THE Proactive_Notifier SHALL incluir en todos los prompts la instrucción: "Hablá del significado y del estado emocional, nunca del evento técnico que lo disparó."
4. WHEN el LLM retorna una respuesta con más de 2 oraciones, THE Proactive_Notifier SHALL usar solo las primeras 2 oraciones del texto retornado
5. THE Proactive_Notifier SHALL usar el mismo modelo LLM (`llama3.1` vía Ollama en `http://localhost:11434/api/generate`) que el ReflectionTimer existente
