"""
channels/channel_router.py — Router central para todos los canales.

Arquitectura:
Telegram/Web/WhatsApp → ChannelRouter → Core Alisha → ChannelRouter → Canal

El router:
1. Recibe ChannelMessage normalizado
2. Lo pasa al core de Alisha (brain.py)
3. Recibe respuesta del core
4. La envía de vuelta al canal correcto
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from channels.base import BaseChannel, ChannelMessage, ChannelResponse, MessageType

logger = logging.getLogger(__name__)

# Executor para correr brain.process() (síncrono) desde contexto async
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ChannelWorker")


def _process_with_brain(message: ChannelMessage) -> ChannelResponse:
    """
    Llama al brain.process() de forma síncrona.
    Se ejecuta en un thread del executor para no bloquear el event loop.
    """
    try:
        from core.brain import get_brain
        brain = get_brain()

        # Construir texto según tipo de mensaje
        if message.message_type == MessageType.TEXT:
            user_input = message.content
        elif message.message_type == MessageType.VOICE:
            # Intentar transcribir
            transcripcion = _transcribir_audio(message.content)
            if transcripcion:
                user_input = transcripcion
            else:
                return ChannelResponse(
                    text="Recibí tu nota de voz pero no pude transcribirla. "
                         "¿Podés escribirme lo que querías decir?",
                    emotion="neutral"
                )
        elif message.message_type == MessageType.IMAGE:
            # Pasar a visión si está disponible
            descripcion = _analizar_imagen(message.content)
            user_input = f"[Imagen recibida] {descripcion}" if descripcion else "[Imagen recibida]"
        elif message.message_type == MessageType.COMMAND:
            user_input = message.content
        else:
            user_input = message.content

        # Procesar con el brain
        response = brain.process(user_input)

        return ChannelResponse(
            text=response.content,
            emotion=response.emotional_state.categoria if response.emotional_state else "neutral",
            metadata={
                "engine": response.engine_used,
                "sarcasm_score": response.sarcasm_score,
            }
        )

    except Exception as e:
        logger.error(f"Error en brain.process: {e}", exc_info=True)
        return ChannelResponse(
            text="Che, algo salió mal de mi lado. Intentá de nuevo.",
            emotion="frustración"
        )


def _transcribir_audio(audio_path: str) -> str:
    """Transcribir audio a texto. Fail-silent."""
    try:
        from audio_listener import transcribir_audio_bytes
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        return transcribir_audio_bytes(audio_bytes) or ""
    except Exception:
        pass
    # Fallback: intentar con whisper directamente
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language="es")
        return result.get("text", "")
    except Exception:
        return ""


def _analizar_imagen(image_path: str) -> str:
    """Analizar imagen con visión. Fail-silent."""
    try:
        from file_analyzer import analizar_archivo
        return analizar_archivo(image_path, "¿Qué ves en esta imagen?") or ""
    except Exception:
        return ""


class ChannelRouter:
    """
    Router central que conecta todos los canales con el core de Alisha.

    Responsabilidades:
    - Registrar canales activos
    - Recibir mensajes de cualquier canal
    - Enviar al brain.process() en thread separado
    - Devolver respuesta al canal correcto
    """

    def __init__(self):
        self.channels: dict[str, BaseChannel] = {}
        # Permite override del handler (útil para tests)
        self._custom_handler: Optional[callable] = None

    def register_channel(self, channel: BaseChannel) -> None:
        """Registrar un canal en el router."""
        if channel.is_enabled():
            self.channels[channel.name] = channel
            logger.info(f"✓ Canal registrado: {channel.name}")
        else:
            logger.info(f"Canal deshabilitado (skip): {channel.name}")

    def set_core_handler(self, handler: callable) -> None:
        """Override del handler del core (útil para tests)."""
        self._custom_handler = handler
        logger.info("✓ Core handler personalizado configurado")

    async def route_message(self, message: ChannelMessage) -> Optional[ChannelResponse]:
        """
        Procesar mensaje de cualquier canal.

        Flujo:
        1. Validar canal
        2. Correr brain.process() en executor (no bloquea el event loop)
        3. Enviar respuesta al canal
        """
        if message.channel not in self.channels:
            logger.error(f"Canal desconocido: {message.channel}")
            return None

        try:
            loop = asyncio.get_event_loop()

            if self._custom_handler:
                # Handler personalizado (tests)
                response = await self._custom_handler(message)
            else:
                # Brain real — corre en thread para no bloquear async
                response = await loop.run_in_executor(
                    _executor,
                    _process_with_brain,
                    message
                )

            # Enviar respuesta al canal
            channel = self.channels[message.channel]
            success = await channel.send_message(message.user_id, response)

            if success:
                logger.info(f"✓ [{message.channel}] {message.user_id[:6]}*** → respondido")
            else:
                logger.error(f"Error enviando respuesta a {message.channel}")

            return response

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}", exc_info=True)
            return None

    async def start_all(self) -> None:
        """Iniciar todos los canales registrados."""
        for name, channel in self.channels.items():
            try:
                await channel.start()
                logger.info(f"✓ Canal iniciado: {name}")
            except Exception as e:
                logger.error(f"Error iniciando canal {name}: {e}")

    async def stop_all(self) -> None:
        """Detener todos los canales limpiamente."""
        for name, channel in self.channels.items():
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"Error deteniendo canal {name}: {e}")
        _executor.shutdown(wait=False)
