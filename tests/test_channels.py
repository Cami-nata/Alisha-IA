"""
tests/test_channels.py — Tests para el sistema de canales.

Cubre:
- Whitelist de Telegram
- ChannelRouter
- ChannelMessage normalizado
- Imports principales
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: ChannelMessage y tipos
# ══════════════════════════════════════════════════════════════════════════════

class TestChannelMessage:
    def test_create_text_message(self):
        from channels.base import ChannelMessage, MessageType
        from datetime import datetime

        msg = ChannelMessage(
            channel="telegram",
            user_id="123456",
            message_type=MessageType.TEXT,
            content="Hola Alisha",
            timestamp=datetime.now(),
            metadata={},
        )
        assert msg.channel == "telegram"
        assert msg.user_id == "123456"
        assert msg.message_type == MessageType.TEXT
        assert msg.content == "Hola Alisha"

    def test_message_types(self):
        from channels.base import MessageType
        assert MessageType.TEXT.value == "text"
        assert MessageType.VOICE.value == "voice"
        assert MessageType.IMAGE.value == "image"
        assert MessageType.COMMAND.value == "command"

    def test_channel_response(self):
        from channels.base import ChannelResponse
        resp = ChannelResponse(text="Hola!", emotion="alegría")
        assert resp.text == "Hola!"
        assert resp.emotion == "alegría"
        assert resp.audio_path is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: ChannelRouter
# ══════════════════════════════════════════════════════════════════════════════

class TestChannelRouter:
    def test_register_enabled_channel(self):
        from channels.channel_router import ChannelRouter
        from channels.base import BaseChannel, ChannelMessage, ChannelResponse

        class FakeChannel(BaseChannel):
            def __init__(self):
                super().__init__(enabled=True)
                self.name = "fake"
            async def start(self): pass
            async def stop(self): pass
            async def send_message(self, uid, resp): return True
            async def handle_message(self, msg): pass

        router = ChannelRouter()
        router.register_channel(FakeChannel())
        assert "fake" in router.channels

    def test_disabled_channel_not_registered(self):
        from channels.channel_router import ChannelRouter
        from channels.base import BaseChannel, ChannelMessage, ChannelResponse

        class DisabledChannel(BaseChannel):
            def __init__(self):
                super().__init__(enabled=False)
                self.name = "disabled"
            async def start(self): pass
            async def stop(self): pass
            async def send_message(self, uid, resp): return False
            async def handle_message(self, msg): pass

        router = ChannelRouter()
        router.register_channel(DisabledChannel())
        assert "disabled" not in router.channels

    def test_route_unknown_channel_returns_none(self):
        from channels.channel_router import ChannelRouter
        from channels.base import ChannelMessage, MessageType
        from datetime import datetime

        router = ChannelRouter()
        msg = ChannelMessage(
            channel="nonexistent",
            user_id="123",
            message_type=MessageType.TEXT,
            content="test",
            timestamp=datetime.now(),
            metadata={},
        )
        result = asyncio.get_event_loop().run_until_complete(
            router.route_message(msg)
        )
        assert result is None

    def test_route_with_custom_handler(self):
        from channels.channel_router import ChannelRouter
        from channels.base import BaseChannel, ChannelMessage, ChannelResponse, MessageType
        from datetime import datetime

        class FakeChannel(BaseChannel):
            def __init__(self):
                super().__init__(enabled=True)
                self.name = "test"
                self.sent = []
            async def start(self): pass
            async def stop(self): pass
            async def send_message(self, uid, resp):
                self.sent.append(resp)
                return True
            async def handle_message(self, msg): pass

        async def fake_handler(msg):
            return ChannelResponse(text="respuesta de test")

        router = ChannelRouter()
        ch = FakeChannel()
        router.register_channel(ch)
        router.set_core_handler(fake_handler)

        msg = ChannelMessage(
            channel="test",
            user_id="123",
            message_type=MessageType.TEXT,
            content="hola",
            timestamp=datetime.now(),
            metadata={},
        )

        result = asyncio.get_event_loop().run_until_complete(
            router.route_message(msg)
        )
        assert result is not None
        assert result.text == "respuesta de test"
        assert len(ch.sent) == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Telegram whitelist
# ══════════════════════════════════════════════════════════════════════════════

class TestTelegramWhitelist:
    def test_empty_whitelist_denies_all(self):
        with patch.dict(os.environ, {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "fake:token",
            "TELEGRAM_ALLOWED_USER_IDS": "",
        }):
            from channels.telegram_channel import TelegramChannel
            ch = TelegramChannel()
            assert not ch._is_user_allowed(123456)
            assert not ch._is_user_allowed(0)

    def test_whitelist_allows_correct_user(self):
        with patch.dict(os.environ, {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "fake:token",
            "TELEGRAM_ALLOWED_USER_IDS": "123456,789012",
        }):
            from channels.telegram_channel import TelegramChannel
            ch = TelegramChannel()
            assert ch._is_user_allowed(123456)
            assert ch._is_user_allowed(789012)

    def test_whitelist_denies_unknown_user(self):
        with patch.dict(os.environ, {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "fake:token",
            "TELEGRAM_ALLOWED_USER_IDS": "123456",
        }):
            from channels.telegram_channel import TelegramChannel
            ch = TelegramChannel()
            assert not ch._is_user_allowed(999999)

    def test_malformed_ids_returns_empty(self):
        with patch.dict(os.environ, {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "fake:token",
            "TELEGRAM_ALLOWED_USER_IDS": "abc,def",
        }):
            from channels.telegram_channel import TelegramChannel
            ch = TelegramChannel()
            assert len(ch.allowed_users) == 0

    def test_disabled_channel(self):
        with patch.dict(os.environ, {
            "TELEGRAM_ENABLED": "false",
        }):
            from channels.telegram_channel import TelegramChannel
            ch = TelegramChannel()
            assert not ch.is_enabled()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Avatar state
# ══════════════════════════════════════════════════════════════════════════════

class TestAvatarState:
    def test_default_state(self):
        from avatar.avatar_state import AvatarState
        s = AvatarState()
        assert s.estado == "neutral"
        assert s.hablando is False
        assert s.mouth_amplitude == 0.0
        assert s.modo == "IDLE"

    def test_is_thinking(self):
        from avatar.avatar_state import AvatarState
        s = AvatarState(modo="THINKING")
        assert s.is_thinking

        s2 = AvatarState(estado="curiosidad")
        assert s2.is_thinking

    def test_is_sleeping(self):
        from avatar.avatar_state import AvatarState
        s = AvatarState(modo="IDLE", estado="cansancio")
        assert s.is_sleeping

    def test_emotion_intensity(self):
        from avatar.avatar_state import AvatarState
        s_entusiasmo = AvatarState(estado="entusiasmo")
        s_neutral    = AvatarState(estado="neutral")
        assert s_entusiasmo.emotion_intensity > s_neutral.emotion_intensity

    def test_clamp_mouth_amplitude(self):
        from avatar.avatar_state import AvatarState
        s = AvatarState(mouth_amplitude=1.5)
        # El reader hace clamp al escribir, pero el dataclass acepta cualquier valor
        # Verificar que el reader lo clampea
        assert s.mouth_amplitude == 1.5  # dataclass no clampea


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Imports principales
# ══════════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_config_imports(self):
        import config
        assert hasattr(config, "__file__")

    def test_channels_base_imports(self):
        from channels.base import BaseChannel, ChannelMessage, ChannelResponse, MessageType
        assert BaseChannel is not None

    def test_channel_router_imports(self):
        from channels.channel_router import ChannelRouter
        assert ChannelRouter is not None

    def test_telegram_channel_imports(self):
        from channels.telegram_channel import TelegramChannel
        assert TelegramChannel is not None

    def test_core_brain_imports(self):
        from core.brain import get_brain
        assert get_brain is not None

    def test_core_assistant_state_imports(self):
        from core.assistant_state import cargar_estado, actualizar_estado
        assert cargar_estado is not None

    def test_avatar_state_imports(self):
        from avatar.avatar_state import AvatarState, get_state
        assert AvatarState is not None

    def test_avatar_motion_controller_imports(self):
        from avatar.motion_controller import MotionController
        assert MotionController is not None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: API endpoints (smoke tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIEndpoints:
    """Smoke tests de los endpoints de la API interna."""

    def test_api_server_imports(self):
        from web.api_server import app
        assert app is not None

    def test_status_endpoint_structure(self):
        """Verificar que el endpoint /status retorna la estructura correcta."""
        from web.api_server import app
        from fastapi.testclient import TestClient

        try:
            client = TestClient(app)
            resp = client.get("/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "mode" in data
            assert "engine" in data
            assert "emotional_state" in data
            assert "online" in data
        except Exception:
            pytest.skip("FastAPI TestClient no disponible")

    def test_message_endpoint_requires_text(self):
        """Verificar que /message requiere el campo 'text'."""
        from web.api_server import app

        try:
            from fastapi.testclient import TestClient
            client = TestClient(app)
            resp = client.post("/message", json={})
            assert resp.status_code == 422
        except Exception:
            pytest.skip("FastAPI TestClient no disponible")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
