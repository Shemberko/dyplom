"""
Тести для WebSocketBroker і WebSocketRxService.
Файли:
  app/services/comunication/web_socket_broker.py
  app/services/comunication/web_socket_rx_service.py
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.comunication.web_socket_broker import WebSocketBroker
from app.services.comunication.web_socket_rx_service import WebSocketRxService


# ---------------------------------------------------------------------------
# WebSocketBroker
# ---------------------------------------------------------------------------

class TestWebSocketBroker:

    @pytest.mark.asyncio
    async def test_connect_calls_accept(self):
        """connect() викликає websocket.accept()."""
        ws = AsyncMock()
        broker = WebSocketBroker(ws)
        await broker.connect()
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_calls_send_text(self):
        """send(msg) викликає websocket.send_text(msg)."""
        ws = AsyncMock()
        broker = WebSocketBroker(ws)
        await broker.send("hello")
        ws.send_text.assert_awaited_once_with("hello")

    @pytest.mark.asyncio
    async def test_receive_returns_text(self):
        """receive() повертає текст від websocket."""
        ws = AsyncMock()
        ws.receive_text.return_value = '{"url": "http://a.com"}'
        broker = WebSocketBroker(ws)
        result = await broker.receive()
        assert result == '{"url": "http://a.com"}'

    @pytest.mark.asyncio
    async def test_disconnect_calls_close(self):
        """disconnect() викликає websocket.close()."""
        ws = AsyncMock()
        broker = WebSocketBroker(ws)
        await broker.disconnect()
        ws.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# WebSocketRxService
# ---------------------------------------------------------------------------

class TestWebSocketRxService:

    @pytest.mark.asyncio
    async def test_send_batch_serializes_buffer_as_json(self):
        """send_batch() серіалізує буфер у JSON і відправляє через send_broker."""
        broker = AsyncMock()
        send_broker = AsyncMock()

        service = WebSocketRxService(broker, send_broker, batch_size=3)
        service.buffer = ["msg1", "msg2", "msg3"]

        await service.send_batch()

        send_broker.send.assert_awaited_once()
        sent_data = send_broker.send.call_args[0][0]
        assert json.loads(sent_data) == ["msg1", "msg2", "msg3"]

    @pytest.mark.asyncio
    async def test_send_batch_clears_buffer_after_send(self):
        """Після send_batch() буфер очищається."""
        broker = AsyncMock()
        send_broker = AsyncMock()

        service = WebSocketRxService(broker, send_broker, batch_size=2)
        service.buffer = ["a", "b"]
        await service.send_batch()

        assert service.buffer == []

    @pytest.mark.asyncio
    async def test_handle_triggers_send_batch_when_buffer_full(self):
        """
        handle() викликає send_batch, коли буфер заповнений.
        Симулюємо 3 повідомлення (batch_size=3), а потім CancelledError
        щоб зупинити нескінченний цикл.
        """
        broker = AsyncMock()
        send_broker = AsyncMock()

        call_count = 0

        async def fake_receive():
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                raise asyncio.CancelledError()
            return f"msg{call_count}"

        broker.receive = fake_receive

        service = WebSocketRxService(broker, send_broker, batch_size=3)

        with pytest.raises(asyncio.CancelledError):
            await service.handle()

        # send_batch мав викликатися рівно 1 раз (при 3 повідомленнях)
        send_broker.send.assert_awaited_once()
