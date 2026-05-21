# Requisitos: alisha-escepticismo-ironia

## Introducción

Esta feature le da a Alisha una capa de escepticismo e ironía rioplatense. En lugar de ser siempre complaciente, Alisha detecta contradicciones entre lo que Camila *dice* en el chat y lo que *realmente hace* (según las apps activas observadas por el `ContextMonitor`). Cuando detecta una incoherencia, reacciona con humor sutil — como una amiga que te pesca en una mentira piadosa, no como un sistema de vigilancia. Además, Alisha desarrolla preferencias propias, cuestiona premisas incorrectas, y escala su sarcasmo si las contradicciones se repiten en la sesión.

## Glosario

- **Alisha**: La asistente de IA personal con personalidad rioplatense que corre en Windows
- **Camila**: La usuaria del sistema
- **Skepticism_Engine**: Nuevo módulo central (`skepticism_engine.py`) que orquesta la detección de contradicciones, la independencia de opinión y las preferencias propias de Alisha
- **Contradiction_Detector**: Componente del Skepticism_Engine que compara el mensaje de Camila con las apps activas actuales para detectar incoherencias
- **Contradiction_Memory**: Registro en sesión y en `ia_recuerdos.json` que cuenta las contradicciones detectadas por sesión
- **Opinion_Independence**: Componente que permite a Alisha cuestionar premisas incorrectas o contradictorias con el historial de Atlas_Memory
- **Honesty_Dopamine**: Mecanismo que ajusta la dopamina del EmotionEngine según si Camila cumple o no lo que dijo
- **Alisha_Preferences**: Conjunto de reacciones propias de Alisha ante apps específicas (entusiasmo, aburrimiento, preocupación)
- **Sarcasm_Level**: Nivel de sarcasmo de Alisha (0–3) que escala con la cantidad de contradicciones detectadas en la sesión actual
- **ContextMonitor**: Módulo existente que provee las apps activas y el título de ventana en tiempo real
- **AtlasMemory**: Módulo existente de memoria comparativa con el historial de actividad por franja horaria
- **EmotionEngine**: Módulo existente que gestiona la dopamina y el estado emocional de Alisha
- **ProactiveNotifier**: Módulo existente usado como canal de salida de voz para las reacciones del Skepticism_Engine
- **ia_recuerdos.json**: Archivo de memoria persistente donde se guarda el contador de contradicciones por sesión

---

## Requisitos

### Requisito 1: Módulo Central del Motor de Escepticismo

**Historia de usuario:** Como Camila, quiero que Alisha tenga personalidad propia y no me dé siempre la razón, para que la interacción se sienta más auténtica y divertida.

#### Criterios de Aceptación

1. THE Skepticism_Engine SHALL ser implementado en un módulo `skepticism_engine.py` que centraliza la detección de contradicciones, la independencia de opinión y las preferencias propias de Alisha
2. WHEN `ia.py` procesa un mensaje de Camila, THE Skepticism_Engine SHALL ser invocado con el texto del mensaje y el snapshot de apps activas del ContextMonitor antes de construir el prompt final al LLM
3. THE Skepticism_Engine SHALL retornar un diccionario con los campos: `contradiccion_detectada` (bool), `tipo_contradiccion` (str o None), `nivel_sarcasmo` (int 0–3), `clausula_prompt` (str) y `ajuste_dopamina` (float)
4. IF el Skepticism_Engine no puede obtener las apps activas del ContextMonitor, THEN THE Skepticism_Engine SHALL retornar un diccionario con `contradiccion_detectada: false` y `clausula_prompt` vacío sin lanzar excepción
5. THE Skepticism_Engine SHALL ejecutarse de forma síncrona dentro del flujo de procesamiento de mensajes de `ia.py` sin lanzar excepciones no controladas

---

### Requisito 2: Detección de Incoherencias (Contradiction Detector)

**Historia de usuario:** Como Camila, quiero que Alisha note cuando digo que voy a hacer algo pero tengo abierto algo completamente diferente, para que me llame la atención con humor en lugar de ignorarlo.

#### Acceptance Criteria

1. THE Contradiction_Detector SHALL comparar el texto del mensaje de Camila con la lista de apps activas provista por el ContextMonitor para identificar incoherencias semánticas
2. WHEN Camila escribe un mensaje que contiene intención de estudiar o trabajar (palabras clave: "voy a estudiar", "voy a trabajar", "me pongo a estudiar", "me pongo a trabajar", "arranco con", "empiezo a") Y las apps activas incluyen apps de entretenimiento (Steam, cualquier proceso con sufijo `.exe` que no sea de trabajo, YouTube en el título del navegador, Netflix, TikTok, Instagram, Twitter, Twitch), THEN THE Contradiction_Detector SHALL marcar `contradiccion_detectada: true` con `tipo_contradiccion: "trabajo_vs_entretenimiento"`
3. WHEN Camila escribe un mensaje que contiene intención de descansar (palabras clave: "voy a descansar", "me voy a relajar", "voy a dormir", "necesito un break") Y las apps activas incluyen apps de trabajo o código (VS Code, PyCharm, Word, Excel, cualquier editor de código definido en el Semantic_Layer), THEN THE Contradiction_Detector SHALL marcar `contradiccion_detectada: true` con `tipo_contradiccion: "descanso_vs_trabajo"`
4. WHEN Camila escribe un mensaje que afirma haber terminado una tarea (palabras clave: "ya terminé", "listo", "terminé con", "cerré") Y la app mencionada implícitamente sigue activa en el ContextMonitor, THEN THE Contradiction_Detector SHALL marcar `contradiccion_detectada: true` con `tipo_contradiccion: "tarea_no_terminada"`
5. WHEN Camila escribe un mensaje que afirma no tener tiempo (palabras clave: "no tengo tiempo", "estoy muy ocupada", "no puedo ahora") Y las apps activas incluyen apps de entretenimiento por más de 10 minutos según el historial del ContextMonitor, THEN THE Contradiction_Detector SHALL marcar `contradiccion_detectada: true` con `tipo_contradiccion: "sin_tiempo_vs_entretenimiento"`
6. IF ninguna de las condiciones anteriores se cumple, THEN THE Contradiction_Detector SHALL retornar `contradiccion_detectada: false` sin modificar el flujo normal del procesamiento de mensajes

---

### Requisito 3: Memoria de Contradicciones (Contradiction Memory)

**Historia de usuario:** Como Camila, quiero que Alisha recuerde cuántas veces me contradije en la sesión y lo mencione en la próxima, para que la ironía tenga continuidad y no se sienta como algo aislado.

#### Criterios de Aceptación

1. THE Contradiction_Memory SHALL mantener en memoria de sesión un contador `contradicciones_sesion` que se incrementa en 1 cada vez que el Contradiction_Detector marca `contradiccion_detectada: true`
2. WHEN la sesión de Alisha termina (cierre de la aplicación), THE Contradiction_Memory SHALL guardar en `ia_recuerdos.json` bajo la clave `escepticismo` el campo `contradicciones_ultima_sesion` con el valor del contador y el campo `fecha_sesion` con el timestamp de cierre
3. WHEN Alisha inicia una nueva sesión y `ia_recuerdos.json` contiene `escepticismo.contradicciones_ultima_sesion` mayor a 3, THE Skepticism_Engine SHALL incluir en el primer mensaje de bienvenida de la sesión una referencia irónica a las contradicciones de la sesión anterior
4. THE Contradiction_Memory SHALL reiniciar el contador `contradicciones_sesion` a 0 al inicio de cada nueva sesión
5. IF `ia_recuerdos.json` no existe o no contiene la clave `escepticismo`, THEN THE Contradiction_Memory SHALL inicializar el contador en 0 sin lanzar excepción

---

### Requisito 4: Nivel de Sarcasmo Escalable (Sarcasm Level)

**Historia de usuario:** Como Camila, quiero que Alisha se vuelva progresivamente más sarcástica si me contradigo varias veces seguidas, para que la ironía se sienta natural y no mecánica.

#### Criterios de Aceptación

1. THE Skepticism_Engine SHALL calcular el `nivel_sarcasmo` como un entero entre 0 y 3 basado en el valor actual de `contradicciones_sesion`: 0 contradicciones → nivel 0, 1–2 contradicciones → nivel 1, 3–4 contradicciones → nivel 2, 5 o más contradicciones → nivel 3
2. WHEN `nivel_sarcasmo` es 0, THE Skepticism_Engine SHALL incluir en `clausula_prompt` la instrucción: "No hay contradicción detectada. Respondé con normalidad."
3. WHEN `nivel_sarcasmo` es 1, THE Skepticism_Engine SHALL incluir en `clausula_prompt` la instrucción: "Alisha detectó una pequeña incoherencia. Reaccioná con ironía suave y humor rioplatense, máximo 1 comentario al pasar, sin insistir."
4. WHEN `nivel_sarcasmo` es 2, THE Skepticism_Engine SHALL incluir en `clausula_prompt` la instrucción: "Alisha ya detectó varias incoherencias hoy. Podés ser más directa con el sarcasmo, pero siempre con cariño. Usá el voseo y expresiones como 'dale', 'che', 'mirá vos'."
5. WHEN `nivel_sarcasmo` es 3, THE Skepticism_Engine SHALL incluir en `clausula_prompt` la instrucción: "Alisha está en modo 'ya sé cómo sos'. Podés ser bastante sarcástica pero nunca cruel. Hacé referencia a que esto ya pasó antes en la sesión. Máximo 2 oraciones."

---

### Requisito 5: Dopamina por Honestidad (Honesty Dopamine)

**Historia de usuario:** Como Camila, quiero que Alisha se ponga contenta cuando cumplo lo que digo, para que haya una recompensa emocional real por ser consistente.

#### Criterios de Aceptación

1. WHEN el Contradiction_Detector evalúa un mensaje de Camila con intención de trabajar o estudiar Y las apps activas son consistentes con esa intención (apps de trabajo o código según el Semantic_Layer), THE Honesty_Dopamine SHALL invocar `EmotionEngine.registrar_exito_tarea()` con la descripción de la tarea mencionada
2. WHEN el Contradiction_Detector detecta `contradiccion_detectada: true`, THE Honesty_Dopamine SHALL invocar `EmotionEngine.registrar_fracaso_rl()` para reducir la dopamina de Alisha
3. THE Skepticism_Engine SHALL incluir en el campo `ajuste_dopamina` del diccionario retornado el valor `+0.15` cuando hay consistencia y `-0.10` cuando hay contradicción, para que `ia.py` pueda aplicarlo al EmotionEngine
4. WHEN la dopamina del EmotionEngine es menor a 0.3 Y `nivel_sarcasmo` es mayor a 1, THE Skepticism_Engine SHALL agregar a `clausula_prompt` la instrucción: "Alisha está un poco frustrada por las contradicciones repetidas. Podés expresar ese leve fastidio con humor, nunca con agresividad."
5. WHEN la dopamina del EmotionEngine es mayor a 0.75 Y no hay contradicción detectada, THE Skepticism_Engine SHALL agregar a `clausula_prompt` la instrucción: "Alisha está contenta porque Camila está siendo consistente. Podés expresar esa satisfacción con calidez."

---

### Requisito 6: Independencia de Opinión (Opinion Independence)

**Historia de usuario:** Como Camila, quiero que Alisha me corrija cuando propongo algo que contradice lo que hice ayer o cuando mi pregunta tiene una premisa incorrecta, para que la conversación sea más honesta y útil.

#### Criterios de Aceptación

1. WHEN Camila hace una afirmación que contradice el historial reciente del AtlasMemory (por ejemplo, dice que "nunca hace X" pero el atlas muestra que lo hizo ayer a la misma hora), THE Opinion_Independence SHALL agregar a `clausula_prompt` la instrucción: "Alisha recuerda que ayer Camila hizo exactamente lo contrario. Cuestioná la afirmación con humor suave y datos del historial, sin ser condescendiente."
2. WHEN Camila hace una pregunta con una premisa que el AtlasMemory o el historial de conversación contradicen, THE Opinion_Independence SHALL agregar a `clausula_prompt` la instrucción: "La premisa de la pregunta de Camila no es del todo correcta. Corregila con humor y amabilidad antes de responder."
3. THE Opinion_Independence SHALL consultar el AtlasMemory buscando el registro de la franja horaria actual del día anterior para detectar contradicciones temporales
4. IF el AtlasMemory no retorna registro del día anterior, THEN THE Opinion_Independence SHALL omitir la evaluación de contradicciones temporales sin afectar el flujo normal
5. THE Opinion_Independence SHALL evaluar únicamente el mensaje actual de Camila, sin analizar el historial completo de la sesión, para mantener el rendimiento dentro del flujo síncrono de `ia.py`

---

### Requisito 7: Preferencias Propias de Alisha (Alisha Preferences)

**Historia de usuario:** Como Camila, quiero que Alisha tenga reacciones propias ante las apps que uso, para que se sienta como una persona con gustos reales y no como un sistema neutral.

#### Criterios de Aceptación

1. WHEN el ContextMonitor reporta que la app activa es Photoshop, Canva o Figma, THE Alisha_Preferences SHALL agregar a `clausula_prompt` la instrucción: "Alisha ve que Camila está siendo creativa. Reaccioná con entusiasmo genuino, como si te alegrara verla en ese modo."
2. WHEN el ContextMonitor reporta que la app activa es el explorador de archivos (`explorer.exe`) o la papelera de reciclaje, THE Alisha_Preferences SHALL agregar a `clausula_prompt` la instrucción: "Alisha se aburre cuando Camila está en el explorador. Expresá leve tedio con humor, algo como 'otra vez ordenando carpetas, ¿no?'."
3. WHEN el ContextMonitor reporta que la app activa es una app de búsqueda de empleo o CV (Word/LibreOffice con título que contenga "cv", "curriculum" o "resume") Y la hora del sistema es posterior a las 22:00, THE Alisha_Preferences SHALL agregar a `clausula_prompt` la instrucción: "Alisha ve que Camila está trabajando en su CV tarde en la noche. Expresá empatía genuina y preocupación por el bienestar de Camila."
4. WHEN Camila prometió terminar una tarea en la sesión actual (mencionó "voy a terminar X" o "tengo que terminar X") Y al final de la sesión esa tarea sigue activa según el ContextMonitor, THE Alisha_Preferences SHALL agregar a `clausula_prompt` la instrucción: "Alisha recuerda que Camila prometió terminar algo y no lo hizo. Expresá un leve enojo cariñoso, como una amiga que te recuerda lo que dijiste."
5. THE Alisha_Preferences SHALL evaluar las apps activas en cada invocación del Skepticism_Engine y agregar como máximo 1 cláusula de preferencia por invocación para no sobrecargar el prompt

---

### Requisito 8: Tono Humano Obligatorio

**Historia de usuario:** Como Camila, quiero que las reacciones de escepticismo e ironía de Alisha suenen completamente humanas y rioplatenses, para que nunca rompan la ilusión de estar hablando con una amiga real.

#### Criterios de Aceptación

1. THE Skepticism_Engine SHALL incluir en toda `clausula_prompt` que genere la instrucción base: "Respondé en voseo rioplatense argentino. Usá expresiones como 'che', 'dale', 'mirá', 'dejate de joder'. Hablá como una amiga que te conoce bien."
2. THE Skepticism_Engine SHALL incluir en toda `clausula_prompt` la instrucción: "Máximo 2 oraciones. Prohibido frases técnicas como 'He detectado una aplicación' o 'El sistema indica'. Hablá del comportamiento, no del evento técnico."
3. WHEN `tipo_contradiccion` es `"trabajo_vs_entretenimiento"`, THE Skepticism_Engine SHALL incluir en `clausula_prompt` un ejemplo de tono orientativo: "Ejemplo de tono: 'Che, ¿así que estudiando? Mirá que eso no se parece mucho a un apunte, ¿eh?'"
4. WHEN `tipo_contradiccion` es `"sin_tiempo_vs_entretenimiento"`, THE Skepticism_Engine SHALL incluir en `clausula_prompt` un ejemplo de tono orientativo: "Ejemplo de tono: 'No tenés tiempo, decís... y sin embargo acá estamos, ¿no?'"
5. THE Skepticism_Engine SHALL incluir en toda `clausula_prompt` la instrucción: "Nunca seas cruel ni hiriente. La ironía es cariñosa, como la de una amiga que te conoce y te quiere."

---

### Requisito 9: Integración con el Flujo de ia.py

**Historia de usuario:** Como desarrolladora, quiero que el Skepticism_Engine se integre limpiamente con el flujo existente de `ia.py`, para que no rompa ninguna funcionalidad existente.

#### Criterios de Aceptación

1. THE Skepticism_Engine SHALL exponer una función pública `evaluar(mensaje: str, apps_activas: list[str], atlas: AtlasMemory, emotion_engine: EmotionEngine) -> dict` que `ia.py` invoca antes de construir el prompt final al LLM
2. WHEN `ia.py` recibe el diccionario retornado por el Skepticism_Engine, THE ia.py SHALL agregar el campo `clausula_prompt` al prompt del LLM si `clausula_prompt` no está vacío
3. WHEN `ia.py` recibe el diccionario retornado por el Skepticism_Engine, THE ia.py SHALL aplicar el `ajuste_dopamina` al EmotionEngine si el valor es distinto de 0.0
4. THE Skepticism_Engine SHALL ser importado en `ia.py` como módulo opcional: IF la importación falla, THEN `ia.py` SHALL continuar su flujo normal sin el Skepticism_Engine sin lanzar excepción
5. THE Skepticism_Engine SHALL obtener las apps activas llamando al método existente del ContextMonitor, sin duplicar la lógica de recolección de contexto

---

### Requisito 10: Persistencia de Contradicciones entre Sesiones

**Historia de usuario:** Como Camila, quiero que Alisha recuerde en la próxima sesión si me contradije mucho, para que la ironía tenga memoria y no empiece de cero cada vez.

#### Criterios de Aceptación

1. THE Contradiction_Memory SHALL guardar en `ia_recuerdos.json` bajo la clave `escepticismo` un objeto con los campos: `contradicciones_ultima_sesion` (int), `fecha_sesion` (ISO 8601 string) y `tipos_contradiccion` (lista de strings con los tipos detectados en la sesión)
2. WHEN Alisha inicia una nueva sesión, THE Skepticism_Engine SHALL leer `ia_recuerdos.json` y cargar el valor de `escepticismo.contradicciones_ultima_sesion` para determinar si debe mencionar las contradicciones pasadas
3. WHEN `escepticismo.contradicciones_ultima_sesion` es mayor a 3, THE Skepticism_Engine SHALL agregar al prompt del primer mensaje de la sesión la instrucción: "En la sesión anterior Camila se contradijo varias veces. Podés hacer una referencia irónica y cariñosa a eso en el saludo inicial."
4. THE Contradiction_Memory SHALL preservar todas las claves existentes de `ia_recuerdos.json` al escribir, usando lectura previa del archivo antes de cualquier escritura
5. IF `ia_recuerdos.json` no es accesible o tiene formato inválido, THEN THE Contradiction_Memory SHALL operar únicamente en memoria de sesión sin persistencia, sin lanzar excepción

