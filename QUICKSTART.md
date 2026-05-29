# 🚀 Quickstart — Alisha IA

## Arranque rápido (5 minutos)

```bash
# 1. Clonar o abrir el proyecto
cd alisha-ia

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar
cp .env.example .env
# Editar .env y agregar al menos una API key (Groq es gratis y rápido)

# 4. Iniciar Alisha
python main.py
```

Esto abre:
- 🌐 Web en `http://localhost:5000`
- 🎭 Avatar Live2D en ventana separada
- 🔔 Tray icon para control

---

## Telegram (opcional, +5 minutos)

```bash
# 1. Crear bot con @BotFather en Telegram
#    - Enviar /newbot
#    - Seguir instrucciones
#    - Copiar el token

# 2. Obtener tu user ID
#    - Hablar con @userinfobot
#    - Copiar tu ID

# 3. Configurar .env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_ALLOWED_USER_IDS=123456789

# 4. Instalar dependencia
pip install python-telegram-bot

# 5. Reiniciar Alisha
python main.py

# 6. Enviar mensaje al bot
#    - Buscar tu bot en Telegram
#    - Enviar /start
```

---

## Estructura del proyecto

```
alisha-ia/
├── main.py              ← Punto de entrada
├── channels/            ← Telegram, WhatsApp, etc
├── core/                ← Cerebro (brain.py)
├── avatar/              ← Live2D
├── memory/              ← Persistencia
├── web/                 ← Interfaz web
├── desktop/             ← App de escritorio (futuro)
├── data/                ← Datos de runtime
└── docs/                ← Documentación
```

---

## Comandos útiles

```bash
# Validar estructura
python scripts/validate_structure.py

# Ver estado del sistema
python -c "from core.assistant_state import get_state; print(get_state())"

# Limpiar logs
del data\*.log

# Limpiar caché
rmdir /s /q __pycache__
```

---

## Troubleshooting

### El servidor no arranca
```bash
# Verificar que el puerto 5000 no está en uso
netstat -ano | findstr :5000

# Si está en uso, matar el proceso
taskkill /PID <PID> /F
```

### El avatar no aparece
```bash
# Verificar que VTube Studio está instalado
# O cambiar LIVE2D_MODEL_PATH en .env
```

### Telegram no responde
```bash
# Verificar configuración
python -c "import os; from dotenv import load_env; load_env(); print(os.getenv('TELEGRAM_BOT_TOKEN'))"

# Verificar que el bot está activo
# Enviar /start al bot en Telegram
```

### Error de imports
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

---

## Próximos pasos

1. **Leer la arquitectura:** `docs/ARQUITECTURA.md`
2. **Ver el TODO:** `TODO.md`
3. **Revisar el refactor:** `REFACTOR_COMPLETE.md`

---

## Desarrollo

### Agregar un nuevo canal

1. Crear `channels/mi_canal.py`:
   ```python
   from channels.base import BaseChannel, ChannelMessage, ChannelResponse
   
   class MiCanal(BaseChannel):
       async def start(self): ...
       async def stop(self): ...
       async def send_message(self, user_id, response): ...
       async def handle_message(self, message): ...
   ```

2. Registrar en `main.py`:
   ```python
   from channels.mi_canal import MiCanal
   router.register_channel(MiCanal())
   ```

### Agregar un nuevo comando de Telegram

Editar `channels/telegram_channel.py`:
```python
async def _cmd_mi_comando(self, update, context):
    await update.message.reply_text("Respuesta")

# En start():
self.app.add_handler(CommandHandler("mi_comando", self._cmd_mi_comando))
```

### Modificar la personalidad

Editar `core/brain.py`:
```python
SYSTEM_PROMPT = """
Tu nueva personalidad aquí...
"""
```

---

## Links útiles

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Live2D Cubism](https://www.live2d.com/en/sdk/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [Groq API](https://console.groq.com/)

---

## Ayuda

- **Documentación:** `docs/`
- **Issues:** GitHub Issues
- **Arquitectura:** `docs/ARQUITECTURA.md`
- **TODO:** `TODO.md`

---

**¡Listo para empezar! 🎭**
