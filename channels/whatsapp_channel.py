"""
channels/whatsapp_channel.py — Stub para integración futura de WhatsApp.

TODO: Implementar cuando se necesite.
Opciones:
- whatsapp-web.js (Node.js bridge)
- Twilio API (requiere número verificado)
- WhatsApp Business API (requiere aprobación)
"""
from __future__ import annotations

import logging

from channels.base import BaseChannel, ChannelMessage, ChannelResponse

logger = logging.getLogger(__name__)


class WhatsAppChannel(BaseChannel):
    """
    Canal de WhatsApp (no implementado aún).
    """
    
    def __init__(self):
        super().__init__(enabled=False)
        logger.info("WhatsApp channel: stub only, not implemented")
    
    async def start(self) -> None:
        """No implementado."""
        pass
    
    async def stop(self) -> None:
        """No implementado."""
        pass
    
    async def send_message(self, user_id: str, response: ChannelResponse) -> bool:
        """No implementado."""
        return False
    
    async def handle_message(self, message: ChannelMessage) -> None:
        """No implementado."""
        pass
