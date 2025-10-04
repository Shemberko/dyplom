from app.services.abstractions.message_broker import MessageBroker

class WebSocketBroker(MessageBroker):
    def __init__(self, websocket):
        self.websocket = websocket

    async def connect(self):
        await self.websocket.accept()

    async def send(self, message):
        await self.websocket.send_text(message)

    async def receive(self):
        message = await self.websocket.receive_text()
        print(f"Received message: {message}")
        return message

    async def disconnect(self):
        await self.websocket.close()