"""
integrations/telegram_bot.py - Canal Telegram para Alisha IA.

Este modulo mantiene Telegram como adaptador externo: recibe mensajes,
valida el usuario y delega la respuesta al brain de Alisha.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Iterable

from config.env_loader import load_env

try:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    _TELEGRAM_OK = True
except ImportError:
    Update = object  # type: ignore
    ContextTypes = object  # type: ignore
    _TELEGRAM_OK = False


logger = logging.getLogger("TelegramBot")


def _parse_allowed_ids(raw: str | None) -> set[int]:
    ids: set[int] = set()
    for item in (raw or "").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError:
            logger.warning("TELEGRAM_ALLOWED_USER_IDS contiene un ID invalido: %s", item)
    return ids


def _split_telegram_message(text: str, limit: int = 3900) -> Iterable[str]:
    if len(text) <= limit:
        yield text
        return
    for start in range(0, len(text), limit):
        yield text[start:start + limit]


@dataclass
class TelegramConfig:
    token: str
    allowed_user_ids: set[int]

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        load_env()
        return cls(
            token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            allowed_user_ids=_parse_allowed_ids(os.environ.get("TELEGRAM_ALLOWED_USER_IDS")),
        )


class TelegramBot:
    """Bot de Telegram integrado con Alisha mediante core.brain.get_brain()."""

    def __init__(
        self,
        token: str | None = None,
        allowed_user_ids: set[int] | None = None,
    ) -> None:
        cfg = TelegramConfig.from_env()
        self.token = (token or cfg.token).strip()
        self.allowed_user_ids = allowed_user_ids if allowed_user_ids is not None else cfg.allowed_user_ids
        self.application = None
        self._brain = None

    def _is_allowed(self, update: Update) -> bool:
        user = getattr(update, "effective_user", None)
        user_id = getattr(user, "id", None)
        if not self.allowed_user_ids:
            logger.warning("TELEGRAM_ALLOWED_USER_IDS esta vacio; rechazo por seguridad.")
            return False
        return isinstance(user_id, int) and user_id in self.allowed_user_ids

    def _get_brain(self):
        if self._brain is None:
            from core.brain import get_brain
            self._brain = get_brain()
        return self._brain

    async def _reply_denied(self, update: Update) -> None:
        if update.message:
            await update.message.reply_text("No tengo permiso para responder a este usuario.")

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            await self._reply_denied(update)
            return
        await update.message.reply_text(
            "Che, ya estoy conectada a Telegram. Mandame un mensaje y lo proceso desde Alisha."
        )

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            await self._reply_denied(update)
            return
        await update.message.reply_text(
            "Comandos disponibles:\n"
            "/start - iniciar\n"
            "/estado - comprobar conexion\n"
            "/ayuda - ver comandos\n\n"
            "Tambien podes escribirme texto normal."
        )

    async def status_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            await self._reply_denied(update)
            return
        try:
            brain = self._get_brain()
            engine = getattr(getattr(brain, "router", None), "last_engine", "hybrid")
            await update.message.reply_text(f"Alisha esta activa. Motor: {engine}.")
        except Exception as exc:
            logger.exception("No se pudo obtener estado: %s", exc)
            await update.message.reply_text("Estoy conectada, pero no pude leer el estado interno.")

    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            await self._reply_denied(update)
            return
        if not update.message or not update.message.text:
            return

        user_text = update.message.text.strip()
        if not user_text:
            return

        logger.info("Mensaje recibido desde Telegram user_id=%s", update.effective_user.id)

        try:
            await update.message.chat.send_action(action=ChatAction.TYPING)
            loop = asyncio.get_running_loop()
            brain = self._get_brain()
            result = await loop.run_in_executor(None, brain.process, user_text)
            response_text = getattr(result, "content", str(result)).strip()
        except Exception as exc:
            logger.exception("Error procesando mensaje con Alisha: %s", exc)
            response_text = "Che, se me complico procesar eso. Probame de nuevo en un momento."

        for chunk in _split_telegram_message(response_text or "No tengo respuesta para eso todavia."):
            await update.message.reply_text(chunk)

    def start(self) -> None:
        """Arranca el bot con long polling. Este metodo bloquea el hilo actual."""
        if not _TELEGRAM_OK:
            raise RuntimeError("Falta python-telegram-bot. Instala dependencias con requirements.txt.")
        if not self.token:
            raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en .env.")

        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("ayuda", self.help_handler))
        self.application.add_handler(CommandHandler("help", self.help_handler))
        self.application.add_handler(CommandHandler("estado", self.status_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))

        logger.info("Iniciando canal Telegram de Alisha...")
        self.application.run_polling(close_loop=False)

    def stop(self) -> None:
        """Detiene el bot si fue iniciado por el ciclo de vida principal."""
        if self.application:
            logger.info("Deteniendo canal Telegram...")
            self.application.stop()


def main() -> None:
    TelegramBot().start()


if __name__ == "__main__":
    main()
