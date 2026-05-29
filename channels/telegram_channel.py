"""
channels/telegram_channel.py — Integración oficial de Telegram Bot API.

Características:
- Texto, voz, audio, imágenes, documentos
- Comandos: /start, /estado, /parar, /tarea, /captura, /ayuda
- Whitelist de usuarios permitidos
- Transcripción de audio (si disponible)
- Visión de imágenes (si disponible)
- Logs seguros sin exponer tokens

Variables de entorno:
- TELEGRAM_ENABLED=false
- TELEGRAM_BOT_TOKEN=
- TELEGRAM_ALLOWED_USER_IDS=123456,789012
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from channels.base import (
    BaseChannel,
    ChannelMessage,
    ChannelResponse,
    MessageType,
)

# Fail-silent: si telegram no está instalado, el canal simplemente no arranca
try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot no instalado. Canal Telegram deshabilitado.")


logger = logging.getLogger(__name__)

# Router global — se inyecta desde main.py
_router: Optional[object] = None

def set_router(router) -> None:
    """Inyectar el ChannelRouter para que el canal pueda enrutar mensajes."""
    global _router
    _router = router


class TelegramChannel(BaseChannel):
    """
    Canal de Telegram usando Bot API oficial.
    
    Arquitectura:
    - Recibe mensajes de Telegram
    - Los normaliza a ChannelMessage
    - Los pasa al ChannelRouter
    - Recibe ChannelResponse
    - Envía respuesta a Telegram
    
    No contiene lógica de IA — solo es un adaptador.
    """
    
    def __init__(self):
        # Leer configuración
        enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        super().__init__(enabled=enabled)
        
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.allowed_users = self._parse_allowed_users()
        
        self.app: Optional[Application] = None
        self.inbox_dir = Path("data/telegram/inbox")
        self.audio_dir = self.inbox_dir / "audio"
        self.image_dir = self.inbox_dir / "images"
        self.doc_dir = self.inbox_dir / "documents"
        
        # Crear directorios
        for d in [self.audio_dir, self.image_dir, self.doc_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _parse_allowed_users(self) -> set[int]:
        """Parsear lista de IDs permitidos desde env."""
        raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if not raw:
            return set()
        
        try:
            return {int(uid.strip()) for uid in raw.split(",") if uid.strip()}
        except ValueError:
            logger.error("TELEGRAM_ALLOWED_USER_IDS mal formateado")
            return set()
    
    def _is_user_allowed(self, user_id: int) -> bool:
        """Verificar si el usuario está en la whitelist."""
        if not self.allowed_users:
            logger.warning("No hay usuarios permitidos configurados")
            return False
        return user_id in self.allowed_users
    
    async def start(self) -> None:
        """Iniciar el bot de Telegram."""
        if not self.enabled:
            logger.info("Canal Telegram deshabilitado")
            return
        
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot no disponible")
            return
        
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN no configurado")
            return
        
        logger.info("Iniciando canal Telegram...")
        
        # Crear aplicación
        self.app = Application.builder().token(self.token).build()
        
        # Registrar handlers
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("estado", self._cmd_estado))
        self.app.add_handler(CommandHandler("parar", self._cmd_parar))
        self.app.add_handler(CommandHandler("tarea", self._cmd_tarea))
        self.app.add_handler(CommandHandler("captura", self._cmd_captura))
        self.app.add_handler(CommandHandler("ayuda", self._cmd_ayuda))
        
        # Mensajes de texto
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        
        # Voz y audio
        self.app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        self.app.add_handler(MessageHandler(filters.AUDIO, self._handle_audio))
        
        # Imágenes
        self.app.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        
        # Documentos
        self.app.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))
        
        # Iniciar polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("✓ Canal Telegram activo")
    
    async def stop(self) -> None:
        """Detener el bot limpiamente."""
        if self.app:
            logger.info("Deteniendo canal Telegram...")
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("✓ Canal Telegram detenido")
    
    async def send_message(self, user_id: str, response: ChannelResponse) -> bool:
        """Enviar respuesta a Telegram."""
        if not self.app:
            return False
        
        try:
            chat_id = int(user_id)
            
            # Enviar texto
            if response.text:
                await self.app.bot.send_message(chat_id=chat_id, text=response.text)
            
            # Enviar audio si existe
            if response.audio_path and Path(response.audio_path).exists():
                with open(response.audio_path, "rb") as audio:
                    await self.app.bot.send_voice(chat_id=chat_id, voice=audio)
            
            # Enviar imagen si existe
            if response.image_path and Path(response.image_path).exists():
                with open(response.image_path, "rb") as img:
                    await self.app.bot.send_photo(chat_id=chat_id, photo=img)
            
            return True
        
        except Exception as e:
            logger.error(f"Error enviando mensaje a Telegram: {e}")
            return False
    
    async def handle_message(self, message: ChannelMessage) -> None:
        """
        Procesar mensaje normalizado.
        Este método es llamado por el ChannelRouter después de procesar con el core.
        """
        # En Telegram, la respuesta se envía directamente desde send_message
        pass
    
    # ── Handlers de comandos ──────────────────────────────────────────────────
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /start"""
        user_id = update.effective_user.id
        
        if not self._is_user_allowed(user_id):
            await update.message.reply_text("⛔ No tenés acceso a este bot.")
            logger.warning(f"Usuario no autorizado intentó /start: {user_id}")
            return
        
        await update.message.reply_text(
            "👋 Hola! Soy Alisha.\n\n"
            "Comandos disponibles:\n"
            "/estado — ver mi estado actual\n"
            "/tarea <descripción> — asignarme una tarea\n"
            "/captura — tomar screenshot de la pantalla\n"
            "/parar — detener tarea actual\n"
            "/ayuda — ver esta ayuda\n\n"
            "También podés mandarme texto, notas de voz, imágenes o documentos."
        )
    
    async def _cmd_estado(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /estado"""
        if not self._is_user_allowed(update.effective_user.id):
            return

        try:
            from core.assistant_state import cargar_estado
            estado = cargar_estado()
            modo = estado.get("modo", "IDLE")
            emo = estado.get("estado", "neutral")
            hablando = estado.get("hablando", False)

            estado_emoji = {
                "IDLE": "😴", "WORKING": "⚙️",
                "THINKING": "🤔", "OVERLOADED": "⚠️"
            }.get(modo, "🟢")

            texto = (
                f"{estado_emoji} **Estado de Alisha**\n\n"
                f"Modo: `{modo}`\n"
                f"Emoción: `{emo}`\n"
                f"Hablando: {'Sí' if hablando else 'No'}"
            )
            await update.message.reply_text(texto, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("🟢 Activa y lista")
    
    async def _cmd_parar(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /parar"""
        if not self._is_user_allowed(update.effective_user.id):
            return

        try:
            from tools.pc_controller import abort_all_actions
            abort_all_actions()
            await update.message.reply_text("⏸️ Acciones detenidas")
        except Exception:
            await update.message.reply_text("⏸️ Parado")
    
    async def _cmd_tarea(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /tarea <descripción>"""
        if not self._is_user_allowed(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text("Uso: /tarea <descripción>")
            return

        tarea = " ".join(context.args)

        # Enrutar como mensaje de texto al core
        msg = ChannelMessage(
            channel="telegram",
            user_id=str(update.effective_user.id),
            message_type=MessageType.COMMAND,
            content=f"Tarea: {tarea}",
            timestamp=datetime.now(),
            metadata={"command": "tarea", "chat_id": update.effective_chat.id}
        )

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        if _router:
            await _router.route_message(msg)
        else:
            await update.message.reply_text(f"✓ Tarea registrada: {tarea}")
    
    async def _cmd_captura(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /captura — toma screenshot y lo envía por Telegram."""
        if not self._is_user_allowed(update.effective_user.id):
            return

        await update.message.reply_text("📸 Capturando pantalla...")

        try:
            import mss
            import io
            from PIL import Image

            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Guardar en data/screenshots/
            from pathlib import Path
            screenshots_dir = Path("data/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            filepath = screenshots_dir / f"telegram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            img.save(filepath, "JPEG", quality=85)

            # Enviar la imagen
            with open(filepath, "rb") as f:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f,
                    caption="📸 Captura de pantalla"
                )
        except Exception as e:
            await update.message.reply_text(f"No pude capturar la pantalla: {e}")
    
    async def _cmd_ayuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /ayuda"""
        if not self._is_user_allowed(update.effective_user.id):
            return
        
        await self._cmd_start(update, context)
    
    # ── Handlers de mensajes ──────────────────────────────────────────────────
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar mensaje de texto."""
        user_id = update.effective_user.id

        if not self._is_user_allowed(user_id):
            return

        text = update.message.text

        # Crear mensaje normalizado
        msg = ChannelMessage(
            channel="telegram",
            user_id=str(user_id),
            message_type=MessageType.TEXT,
            content=text,
            timestamp=datetime.now(),
            metadata={"chat_id": update.effective_chat.id}
        )

        # Indicador de "escribiendo..."
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Enrutar al core
        if _router:
            await _router.route_message(msg)
        else:
            await update.message.reply_text(
                "Che, el router no está configurado todavía. Reiniciá Alisha."
            )
    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar nota de voz."""
        user_id = update.effective_user.id
        
        if not self._is_user_allowed(user_id):
            return
        
        # Descargar audio
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
        filepath = self.audio_dir / filename
        
        await file.download_to_drive(filepath)
        
        # Crear mensaje normalizado
        msg = ChannelMessage(
            channel="telegram",
            user_id=str(user_id),
            message_type=MessageType.VOICE,
            content=str(filepath),
            timestamp=datetime.now(),
            metadata={"duration": voice.duration}
        )

        # Indicador de "grabando audio..."
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="record_voice"
        )

        # Enrutar al core (transcribirá y procesará)
        if _router:
            await _router.route_message(msg)
        else:
            await update.message.reply_text("🎤 Nota de voz recibida. Transcribiendo...")
    
    async def _handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar archivo de audio."""
        user_id = update.effective_user.id
        
        if not self._is_user_allowed(user_id):
            return
        
        audio = update.message.audio
        file = await context.bot.get_file(audio.file_id)
        
        filename = audio.file_name or f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        filepath = self.audio_dir / filename
        
        await file.download_to_drive(filepath)
        
        await update.message.reply_text(f"🎵 Audio recibido: {filename}")
    
    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar imagen."""
        user_id = update.effective_user.id
        
        if not self._is_user_allowed(user_id):
            return
        
        # Obtener la imagen de mayor resolución
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = self.image_dir / filename
        
        await file.download_to_drive(filepath)
        
        # Crear mensaje normalizado
        msg = ChannelMessage(
            channel="telegram",
            user_id=str(user_id),
            message_type=MessageType.IMAGE,
            content=str(filepath),
            timestamp=datetime.now(),
            metadata={"width": photo.width, "height": photo.height}
        )

        # Indicador de "subiendo foto..."
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_photo"
        )

        # Enrutar al core (analizará con visión)
        if _router:
            await _router.route_message(msg)
        else:
            await update.message.reply_text("🖼️ Imagen recibida. Analizando...")
    
    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar documento."""
        user_id = update.effective_user.id
        
        if not self._is_user_allowed(user_id):
            return
        
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        
        filename = doc.file_name or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filepath = self.doc_dir / filename
        
        await file.download_to_drive(filepath)
        
        await update.message.reply_text(f"📄 Documento recibido: {filename}")
