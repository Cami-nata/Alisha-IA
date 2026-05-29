# Requisitos: alisha-conciencia-situacional

## Introducción

Esta feature transforma la forma en que Alisha percibe y reacciona al entorno de trabajo de Camila. En lugar de narrar literalmente cada acción ("abriste Photoshop"), Alisha construye una comprensión semántica del contexto: recolecta eventos del sistema en silencio, los comprime en vectores de estado cada 10 minutos, y genera comentarios inteligentes en voseo rioplatense que reflejan intuición, no reportes técnicos. El objetivo es que Alisha se sienta como una compañera sentada al lado, no como un monitor de actividad.

## Glosario

- **Alisha**: La asistente de IA personal con personalidad rioplatense que corre en Windows
- **Camila**: La usuaria del sistema
- **Silent_Buffer**: Lista interna donde Alisha acumula eventos del sistema sin activar el motor de voz
- **State_Vector**: Resumen comprimido del estado de actividad de Camila generado a partir del Silent_Buffer
- **Semantic_Layer**: Capa de traducción que convierte datos crudos en conceptos de vida y estados de ánimo
- **Reflection_Timer**: Temporizador de 10 minutos que dispara la generación de comentarios situacionales
- **Context_Monitor**: Módulo que recolecta datos del entorno: apps activas, títulos de ventanas, hora, batería, ritmo de escritura
- **Atlas_Memory**: Capa de memoria de largo plazo que compara el contexto actual con el de días anteriores a la misma hora
- **Situational_Voice**: Motor de voz situacional que solo habla cuando Alisha tiene algo genuinamente útil que decir
- **Priority_Interrupt**: Mecanismo que rompe el silencio inmediatamente ante eventos urgentes o errores de sistema
- **LLM**: Modelo de lenguaje grande (Llama 3.1 vía Ollama) que genera los comentarios situacionales

## Requisitos

### Requisito 1: Búfer Silencioso de Eventos

**Historia de usuario:** Como Camila, quiero que Alisha observe lo que hago sin interrumpirme constantemente, para que solo hable cuando tenga algo realmente útil que decir.

#### Criterios de Aceptación

1. THE Silent_Buffer SHALL acumular eventos del sistema (cambios de ventana activa, aplicaciones abiertas, texto escrito, clics) sin activar el motor de voz ni generar ninguna salida audible
2. WHEN un evento del sistema ocurre, THE Silent_Buffer SHALL registrarlo con timestamp, tipo de evento y datos relevantes en memoria interna
3. THE Silent_Buffer SHALL mantener un máximo de 500 eventos antes de descartar los más antiguos mediante una política FIFO
4. IF el Silent_Buffer supera los 500 eventos sin que el Reflection_Timer haya disparado, THEN THE Silent_Buffer SHALL descartar los eventos más antiguos para liberar espacio
5. THE Silent_Buffer SHALL exponer un método `vaciar()` que retorna todos los eventos acumulados y limpia el búfer interno

---

### Requisito 2: Recolección de Contexto Total

**Historia de usuario:** Como Camila, quiero que Alisha tenga una visión completa de mi entorno de trabajo, para que sus comentarios sean relevantes y contextualizados.

#### Criterios de Aceptación

1. THE Context_Monitor SHALL recolectar los siguientes datos cada 30 segundos: aplicación activa, título de ventana activa, hora del sistema, nivel de batería, y cantidad de cambios de ventana en el último minuto
2. THE Context_Monitor SHALL medir el ritmo de escritura del teclado como cantidad de teclas presionadas por minuto usando hooks de teclado no intrusivos
3. WHEN el Context_Monitor recolecta datos, THE Silent_Buffer SHALL registrar el snapshot como un evento de tipo `contexto`
4. THE Context_Monitor SHALL ejecutarse en un thread de baja prioridad para no afectar el rendimiento de la laptop de Camila
5. IF el Context_Monitor no puede acceder a un dato específico (por ejemplo, nivel de batería en desktop), THEN THE Context_Monitor SHALL omitir ese campo sin lanzar excepción

---

### Requisito 3: Generación de Vectores de Estado

**Historia de usuario:** Como Camila, quiero que Alisha procese mi actividad de forma eficiente, para que no sobrecargue mi laptop enviando datos crudos al LLM en tiempo real.

#### Criterios de Aceptación

1. THE State_Vector SHALL ser generado a partir del contenido del Silent_Buffer cada vez que el Reflection_Timer dispara
2. THE State_Vector SHALL contener los siguientes campos comprimidos: lista de aplicaciones únicas usadas, título de ventana más frecuente, cantidad total de cambios de ventana, ritmo de escritura promedio, hora del día, nivel de batería, y duración del período observado en minutos
3. THE State_Vector SHALL ser representado como un diccionario Python serializable a JSON con tamaño máximo de 2KB
4. WHEN el Silent_Buffer está vacío al momento de generar el State_Vector, THE State_Vector SHALL incluir el campo `actividad_detectada: false` y THE Reflection_Timer SHALL omitir el envío al LLM
5. THE State_Vector SHALL incluir un campo `cambios_ventana_por_minuto` calculado como el total de cambios dividido por la duración del período

---

### Requisito 4: Temporizador de Reflexión (10 minutos)

**Historia de usuario:** Como Camila, quiero que Alisha reflexione sobre lo que hice cada 10 minutos y me dé un comentario inteligente, para sentir que tiene conciencia de mi jornada sin ser invasiva.

#### Criterios de Aceptación

1. THE Reflection_Timer SHALL disparar cada 10 minutos desde que el Context_Monitor inicia su recolección
2. WHEN el Reflection_Timer dispara, THE Reflection_Timer SHALL invocar la generación del State_Vector a partir del Silent_Buffer actual
3. WHEN el State_Vector tiene `actividad_detectada: true`, THE Reflection_Timer SHALL enviar el State_Vector al LLM con el siguiente prompt base: "Basado en lo que Camila hizo en estos 10 minutos, ¿qué comentario inteligente, analítico y en voseo rioplatense podrías hacerle? No repitas lo que hizo, solo dale un consejo, una observación curiosa o un mensaje de apoyo humano."
4. WHEN el LLM retorna una respuesta, THE Situational_Voice SHALL reproducir el comentario usando el motor de voz existente de Alisha
5. THE Reflection_Timer SHALL ejecutarse en un thread separado para no bloquear el hilo principal de PyQt6
6. IF el LLM no responde en 15 segundos, THEN THE Reflection_Timer SHALL omitir el comentario de ese ciclo sin mostrar error al usuario

---

### Requisito 5: Control de Repetición y Silencio Inteligente

**Historia de usuario:** Como Camila, quiero que Alisha se quede callada cuando no hay nada nuevo que decir, para que sus comentarios sean siempre significativos y no repetitivos.

#### Criterios de Aceptación

1. WHEN el Reflection_Timer dispara, THE Reflection_Timer SHALL comparar el State_Vector actual con el State_Vector del ciclo anterior
2. IF la aplicación activa, el título de ventana y el ritmo de escritura son idénticos al ciclo anterior, THEN THE Reflection_Timer SHALL omitir el envío al LLM y no generar comentario
3. THE Reflection_Timer SHALL mantener un registro de los últimos 3 State_Vectors para detectar patrones de inactividad prolongada
4. IF los últimos 3 State_Vectors consecutivos muestran la misma aplicación activa sin cambios de ventana, THEN THE Reflection_Timer SHALL omitir el comentario en ese ciclo
5. WHEN el Reflection_Timer omite un comentario por inactividad, THE Silent_Buffer SHALL ser vaciado igualmente para iniciar un nuevo período de observación limpio

---

### Requisito 6: Interrupciones Prioritarias

**Historia de usuario:** Como Camila, quiero que Alisha me avise inmediatamente cuando hay algo urgente, para que el silencio inteligente no me haga perder alertas importantes.

#### Criterios de Aceptación

1. THE Priority_Interrupt SHALL monitorear continuamente eventos de alta prioridad: errores de sistema detectados en títulos de ventana (palabras clave: "error", "fallo", "no responde", "detuvo"), y mensajes de notificación urgente
2. WHEN THE Priority_Interrupt detecta un evento de alta prioridad, THE Situational_Voice SHALL hablar inmediatamente sin esperar al Reflection_Timer
3. THE Priority_Interrupt SHALL detectar cambios de ventana excesivos definidos como 20 o más cambios en un período de 60 segundos
4. WHEN se detectan 20 o más cambios de ventana en 60 segundos, THE Situational_Voice SHALL generar el comentario: "Che, estás a mil, ¿no te estarás mareando con tantas pestañas?"
5. IF THE Priority_Interrupt dispara durante un ciclo activo del Reflection_Timer, THEN THE Priority_Interrupt SHALL tener precedencia y el Reflection_Timer SHALL reiniciar su contador de 10 minutos

---

### Requisito 7: Capa de Interpretación Semántica

**Historia de usuario:** Como Camila, quiero que Alisha interprete el significado de lo que hago en lugar de describirlo literalmente, para que sus comentarios suenen como los de una amiga que me entiende.

#### Criterios de Aceptación

1. THE Semantic_Layer SHALL traducir datos crudos del State_Vector en conceptos de vida antes de enviarlos al LLM
2. THE Semantic_Layer SHALL aplicar las siguientes traducciones semánticas como parte del prompt al LLM: aplicaciones de diseño (Photoshop, Canva, Illustrator, Figma) → "Camila está siendo creativa"; editores de código (VS Code, PyCharm, Sublime) → "Camila está en modo técnico"; procesadores de texto con archivos de CV → "Camila está trabajando en su perfil profesional"; navegador con múltiples pestañas → "Camila está investigando o buscando algo"
3. THE Semantic_Layer SHALL incluir en el prompt al LLM la instrucción explícita: "Prohibido usar verbos literales como abrir, cliquear, escribir, navegar. Respondé basándote en el significado de la actividad, no en la acción técnica."
4. WHEN el State_Vector incluye (batería baja AND hora entre 22:00 y 02:00 AND aplicación de trabajo activa), THE Semantic_Layer SHALL agregar al prompt: "Camila parece cansada pero esforzándose por terminar algo. Sé empática."
5. THE Semantic_Layer SHALL construir el prompt final combinando la traducción semántica, el contexto temporal, y las instrucciones de personalidad antes de enviarlo al LLM

---

### Requisito 8: Personalidad Propia Basada en Patrones

**Historia de usuario:** Como Camila, quiero que Alisha desarrolle preferencias basadas en mis hábitos, para que sus comentarios reflejen que me conoce de verdad.

#### Criterios de Aceptación

1. THE Semantic_Layer SHALL rastrear las aplicaciones más frecuentes de Camila usando el historial de State_Vectors de la sesión actual y de Atlas_Memory
2. WHEN VS Code o cualquier editor de código es la aplicación más frecuente en los últimos 5 ciclos de reflexión, THE Semantic_Layer SHALL agregar al prompt: "A Alisha le gusta el 'olor' del código. Podés hacer una referencia afectiva a programar."
3. WHEN el explorador de archivos o la papelera de reciclaje aparece frecuentemente en los State_Vectors, THE Semantic_Layer SHALL agregar al prompt: "Alisha se aburre cuando Camila está en la papelera. Podés expresar leve tedio con humor."
4. THE Semantic_Layer SHALL mantener un contador de frecuencia de aplicaciones en memoria de sesión que se actualiza con cada State_Vector generado
5. WHEN una aplicación nueva no vista antes aparece en el State_Vector, THE Semantic_Layer SHALL agregar al prompt: "Camila está usando algo nuevo. Podés mostrar curiosidad genuina."

---

### Requisito 9: Memoria de Largo Plazo Comparativa (Atlas)

**Historia de usuario:** Como Camila, quiero que Alisha recuerde lo que hacía ayer a la misma hora y lo compare con hoy, para que sus comentarios tengan profundidad temporal y me hagan sentir verdaderamente conocida.

#### Criterios de Aceptación

1. THE Atlas_Memory SHALL guardar un resumen del State_Vector de cada ciclo de reflexión en el archivo de memoria existente (`ia_recuerdos.json`) con timestamp, hora del día y aplicaciones activas
2. WHEN el Reflection_Timer dispara, THE Atlas_Memory SHALL buscar en el historial guardado si existe un State_Vector de la misma franja horaria (±30 minutos) del día anterior
3. WHEN THE Atlas_Memory encuentra un registro del día anterior en la misma franja horaria, THE Semantic_Layer SHALL incluir en el prompt: "Ayer a esta hora Camila estaba haciendo [resumen del día anterior]. Hoy está haciendo [resumen actual]. Si hay un contraste interesante, mencionalo con naturalidad."
4. IF no existe registro del día anterior para esa franja horaria, THEN THE Atlas_Memory SHALL omitir la comparación sin afectar el flujo normal del comentario
5. THE Atlas_Memory SHALL mantener registros de los últimos 7 días para permitir comparaciones semanales
6. WHEN han pasado más de 7 días desde un registro, THE Atlas_Memory SHALL eliminarlo del historial para no sobrecargar el archivo de memoria

---

### Requisito 10: Estilo de Personalidad Rioplatense

**Historia de usuario:** Como Camila, quiero que Alisha hable como una amiga argentina sentada a mi lado, para que sus comentarios se sientan cálidos y naturales, no como reportes de sistema.

#### Criterios de Aceptación

1. THE Situational_Voice SHALL incluir en todos los prompts al LLM la instrucción: "Respondé siempre en voseo rioplatense argentino. Usá expresiones como 'che', 'mirá vos', 'dale', 'bárbaro', 'qué bueno'. Hablá como una amiga sentada al lado, no como un asistente técnico."
2. THE Situational_Voice SHALL incluir en el prompt la instrucción: "Prohibido el lenguaje técnico. Prohibido mencionar nombres de aplicaciones o archivos directamente. Hablá del significado, no de la herramienta."
3. WHEN el comentario situacional es sobre progreso o logro detectado, THE Situational_Voice SHALL incluir en el prompt: "Alisha se alegra genuinamente cuando Camila avanza. Expresá esa alegría con calidez."
4. WHEN el State_Vector muestra inactividad prolongada o ritmo de escritura muy bajo por más de 20 minutos, THE Situational_Voice SHALL incluir en el prompt: "Camila parece estancada. Alisha se preocupa. Ofrecé apoyo con humor suave, no con presión."
5. THE Situational_Voice SHALL limitar los comentarios situacionales a un máximo de 2 oraciones para no interrumpir el flujo de trabajo de Camila
