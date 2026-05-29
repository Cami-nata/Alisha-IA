"""
channels/base.py — Interfaz base para canales de comunicación.
Todos los canales (Telegram, WhatsApp, Web) heredan de aquí.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """Tipos de mensaje soportados por los canales."""
    TEXT = "text"
    VOICE = "voice"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    COMMAND = "command"


@dataclass
class ChannelMessage:
    """Mensaje normalizado entre canales."""
    channel: str                    # "telegram", "web", "whatsapp"
    user_id: str                    # ID del usuario en ese canal
    message_type: MessageType
    content: str                    # texto o path al archivo
    timestamp: datetime
    metadata: dict[str, Any]        # datos específicos del canal
    reply_to: Optional[str] = None  # ID del mensaje al que responde


@dataclass
class ChannelResponse:
    """Respuesta normalizada de Alisha."""
    text: str
    emotion: Optional[str] = None
    audio_path: Optional[str] = None
    image_path: Optional[str] = None
    metadata: dict[str, Any] = None


class BaseChannel(ABC):
    """
    Clase base para todos los canales de comunicación.
    
    Responsabilidades:
    - Recibir mensajes del canal externo
    - Normalizar a ChannelMessage
    - Enviar al core de Alisha
    - Recibir ChannelResponse
    - Enviar respuesta al canal externo
    """
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.name = self.__class__.__name__.replace("Channel", "").lower()
    
    @abstractmethod
    async def start(self) -> None:
        """Iniciar el canal (conectar, autenticar, etc)."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Detener el canal limpiamente."""
        pass
    
    @abstractmethod
    async def send_message(self, user_id: str, response: ChannelResponse) -> bool:
        """Enviar respuesta al usuario en este canal."""
        pass
    
    @abstractmethod
    async def handle_message(self, message: ChannelMessage) -> None:
        """Procesar mensaje entrante (implementado por cada canal)."""
        pass
    
    def is_enabled(self) -> bool:
        """Verificar si el canal está habilitado."""
        return self.enabled
