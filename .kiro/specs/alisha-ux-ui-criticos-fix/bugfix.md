# Bugfix Requirements Document

## Introduction

Alisha tiene problemas críticos de UX/UI que afectan la experiencia del usuario final. Los problemas incluyen historial sucio con observaciones técnicas visibles, animaciones que se narran en texto en lugar de ejecutarse visualmente, confusión de identidad donde el sistema puede llamar "Alisha" al usuario, y problemas de rate limiting con Google que disparan CAPTCHAs por exceso de peticiones de visión.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN Alisha hace observaciones automáticas THEN el sistema muestra "[Alisha observa]" y "[Alisha sugiere]" en el historial del usuario

1.2 WHEN Alisha necesita hacer una animación THEN el sistema escribe acciones entre asteriscos (ej: *gira la cabeza*) en el chat en lugar de ejecutar la animación

1.3 WHEN el sistema procesa interacciones THEN puede confundir la identidad y llamar "Alisha" al usuario en lugar de usar el nombre correcto "Cami"

1.4 WHEN Alisha usa el sistema de visión THEN hace demasiadas peticiones por segundo a Google Gemini Vision causando errores 429 y CAPTCHAs

### Expected Behavior (Correct)

2.1 WHEN Alisha hace observaciones automáticas THEN el sistema SHALL ocultar "[Alisha observa]" y "[Alisha sugiere]" del historial del usuario y guardarlos en un log oculto

2.2 WHEN Alisha necesita hacer una animación THEN el sistema SHALL conectar las acciones entre asteriscos al modelo Live2D para ejecutar la animación visualmente

2.3 WHEN el sistema procesa interacciones THEN el sistema SHALL asegurar que user_name sea "Cami" en todo el sistema y nunca llamar "Alisha" al usuario

2.4 WHEN Alisha usa el sistema de visión THEN el sistema SHALL implementar rate limiting apropiado para evitar errores 429 y CAPTCHAs de Google

### Unchanged Behavior (Regression Prevention)

3.1 WHEN el usuario envía mensajes normales THEN el sistema SHALL CONTINUE TO mostrar esos mensajes en el historial con títulos de 3 palabras

3.2 WHEN Alisha responde normalmente sin animaciones THEN el sistema SHALL CONTINUE TO mostrar las respuestas de texto normalmente

3.3 WHEN el sistema funciona correctamente con identidades THEN el sistema SHALL CONTINUE TO mantener la identidad de Alisha como asistente y Cami como usuario

3.4 WHEN el sistema de visión funciona dentro de los límites de rate THEN el sistema SHALL CONTINUE TO proporcionar análisis de pantalla efectivo