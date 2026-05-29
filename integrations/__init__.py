"""
integrations/ — Integraciones externas opcionales.
Se comunican con Alisha via HTTP (API REST de web/), NO via imports directos.
"""
from integrations.discord_bot import DiscordBot
from integrations.telegram_bot import TelegramBot
from integrations.whatsapp_bridge import WhatsAppBridge
from integrations.youtube_client import YouTubeClient


def get_available_integrations() -> list[str]:
    """Retorna los nombres de las integraciones disponibles."""
    return ["discord", "telegram", "whatsapp", "youtube"]


__all__ = [
    "DiscordBot",
    "TelegramBot",
    "WhatsAppBridge",
    "YouTubeClient",
    "get_available_integrations",
]
