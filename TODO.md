# TODO — Alisha IA → JARVIS

## 🚀 FASE 1: Limpieza y arquitectura ✅

- [x] Mover `.kiro/` a `docs/dev-history/kiro-specs/`
- [x] Mover `.claude/` a `docs/dev-history/claude-agents/`
- [x] Actualizar `.gitignore`
- [x] Crear estructura `channels/`
- [x] Implementar `channels/base.py`
- [x] Implementar `channels/channel_router.py`
- [x] Implementar `channels/telegram_channel.py`
- [x] Crear stub `channels/whatsapp_channel.py`
- [x] Crear estructura `desktop/`
- [x] Documentar arquitectura en `docs/ARQUITECTURA.md`
- [x] Crear `.env.example`
- [x] Actualizar `README.md`
- [x] Agregar `python-telegram-bot` a requirements

---

## 🤖 FASE 2: Telegram funcional

### Integración con el core
- [ ] Conectar `ChannelRouter` con `core/brain.py`
  - [ ] Crear handler en `brain.py` que acepte `ChannelMessage`
  - [ ] Retornar `ChannelResponse` con texto + emoción
  - [ ] Registrar handler en el router

- [ ] Iniciar canales en `main.py`
  - [ ] Importar `ChannelRouter`, `TelegramChannel`
  - [ ] Registrar canales
  - [ ] Iniciar en thread separado
  - [ ] Detener limpiamente al cerrar

### Features avanzadas
- [ ] Transcripción de audio
  - [ ] Integrar con Whisper si está disponible
  - [ ] Fallback a "audio recibido, no puedo transcribir"
  - [ ] Pasar texto transcrito al core

- [ ] Análisis de imágenes
  - [ ] Integrar con `vision/gemini_vision.py`
  - [ ] Pasar imagen al core para análisis
  - [ ] Responder con descripción

- [ ] Comandos funcionales
  - [ ] `/estado` → leer estado real del core
  - [ ] `/parar` → detener tarea actual
  - [ ] `/tarea` → crear tarea en el sistema
  - [ ] `/captura` → tomar screenshot y enviar

### Testing
- [ ] Test de whitelist
- [ ] Test de comandos
- [ ] Test de mensajes de texto
- [ ] Test de audio
- [ ] Test de imágenes
- [ ] Test end-to-end con bot real

---

## 🎨 FASE 3: UI estilo JARVIS ✅

### Diseño
- [x] Definir paleta de colores JARVIS (cyan, azul, ámbar, oscuro)
- [x] Definir estados del orbe (idle, listening, thinking, speaking, working, error, sleep)
- [x] Definir layout: sidebar + centro (orbe+chat) + módulos + timeline

### Implementación
- [x] Crear `static/js/jarvis-ui.js`
  - [x] Orbe principal con estados y animaciones CSS
  - [x] Timeline de actividad en tiempo real
  - [x] Panel de módulos con estado real
  - [x] Polling de `/api/status` cada 3s
  - [x] Integración con eventos SocketIO
  - [x] Drag & drop de archivos
- [x] Actualizar `templates/index.html` con layout JARVIS completo
  - [x] Header HUD con barras de ánimo/energía
  - [x] Sidebar con historial y trust widget
  - [x] Centro: orbe + chat
  - [x] Timeline de actividad
  - [x] Panel de módulos (Cerebro, Memoria, Voz, Visión, Telegram, Avatar, Sistema)
  - [x] Botón PARAR en panel de módulos
- [x] `static/css/jarvis.css` ya existía con estilos completos

---

## 🎭 FASE 4: Avatar independiente ✅ (parcial)

### Archivos creados
- [x] `avatar/avatar_state.py` — lector de estado compartido (20Hz, fail-silent)
- [x] `avatar/motion_controller.py` — movimiento motriz a 30fps
  - [x] Respiración suave (sinusoidal)
  - [x] Parpadeo natural (timing aleatorio)
  - [x] Mirada aleatoria controlada
  - [x] Micro inclinaciones de cabeza
  - [x] Lip-sync con mouth_amplitude
  - [x] FIX bug transparencia: opacity siempre 1.0, clamp estricto en todos los params

### Pendiente FASE 4
- [ ] Integrar motion_controller en cabina_virtual.py
- [ ] Modo debug visual (overlay con parámetros actuales)
- [ ] Test de arranque independiente del avatar

---

## 💻 FASE 5: Desktop App instalable ✅ (parcial)

- [x] Crear `desktop/launcher.py` con pywebview
  - [x] Inicia backend si no está corriendo
  - [x] Espera a que el backend esté listo
  - [x] Abre ventana nativa sin barras de navegador
  - [x] Fallback a navegador si pywebview no está instalado

---

## ✅ FASE 7: Tests ✅

- [x] `tests/test_channels.py` — 26 tests pasando
  - [x] ChannelMessage y tipos
  - [x] ChannelRouter (registro, routing, handler)
  - [x] Telegram whitelist (vacía, correcta, incorrecta, malformada, desactivada)
  - [x] AvatarState (defaults, is_thinking, is_sleeping, emotion_intensity)
  - [x] Imports principales (config, channels, core, avatar)
  - [x] API endpoints (smoke tests)

---

## 🧹 FASE 6: Limpieza de raíz

### Auditoría de archivos sueltos
- [ ] Listar todos los `.py` en raíz
- [ ] Clasificar en:
  - [ ] Código real → mover a carpeta
  - [ ] Shim → mantener o eliminar
  - [ ] Duplicado → eliminar
  - [ ] Obsoleto → eliminar

### Reorganización
- [ ] Mover archivos a carpetas correctas
  - [ ] `actions.py` → `tools/actions.py`
  - [ ] `agent_loop.py` → ya está en `core/`
  - [ ] `brain.py` → ya está en `core/`
  - [ ] `vision_engine.py` → `vision/`
  - [ ] etc.

- [ ] Actualizar imports
  - [ ] Buscar todos los imports de archivos movidos
  - [ ] Actualizar rutas
  - [ ] Verificar que no se rompa nada

- [ ] Eliminar duplicados
  - [ ] Verificar que no haya dos fuentes de verdad
  - [ ] Mantener solo la versión en carpeta
  - [ ] Crear shim mínimo si es necesario

### Validación
- [ ] Ejecutar `python scripts/validate_structure.py`
- [ ] Verificar que `python main.py` arranca
- [ ] Verificar que todos los módulos importan
- [ ] Ejecutar tests

---

## ✅ FASE 7: Validación final

### Tests de integración
- [ ] Test de arranque completo
  - [ ] Servidor web arranca
  - [ ] Avatar arranca
  - [ ] Tray icon aparece
  - [ ] WebSocket conecta

- [ ] Test de canales
  - [ ] Web funciona
  - [ ] Telegram funciona
  - [ ] Router distribuye correctamente

- [ ] Test de módulos
  - [ ] Brain responde
  - [ ] Memory persiste
  - [ ] Vision analiza
  - [ ] Avatar anima

### Documentación
- [ ] Actualizar README con cambios finales
- [ ] Documentar API interna
- [ ] Crear guía de desarrollo
- [ ] Crear guía de deployment

### Release
- [ ] Crear tag de versión
- [ ] Generar changelog
- [ ] Crear release en GitHub
- [ ] Publicar instalador

---

## 🎯 Resultado esperado

Al completar todas las fases:

✅ **App instalable** de escritorio  
✅ **UI estilo JARVIS** con orbes funcionales  
✅ **Avatar vivo** independiente  
✅ **Telegram estable** como canal oficial  
✅ **Arquitectura limpia** sin carpetas basura  
✅ **Sin duplicados** grandes  
✅ **Documentación completa**  

---

## 📝 Notas

- Cada fase debe completarse antes de pasar a la siguiente
- Validar con tests después de cada cambio importante
- Mantener fail-silent: si algo falla, Alisha sigue arrancando
- No romper funcionalidad existente
- Documentar decisiones importantes

---

## 🚀 Próximo paso inmediato

**FASE 2: Conectar Telegram con el core**

```bash
# 1. Instalar dependencia
pip install python-telegram-bot

# 2. Configurar .env
# Agregar:
# TELEGRAM_ENABLED=true
# TELEGRAM_BOT_TOKEN=tu_token
# TELEGRAM_ALLOWED_USER_IDS=tu_id

# 3. Modificar main.py para iniciar canales
# 4. Crear handler en brain.py
# 5. Probar con mensaje real
```
