import json

class WebSocketRxService:
    def __init__(self, broker, send_broker, batch_size=3):
        self.broker = broker
        self.send_broker = send_broker
        self.batch_size = batch_size
        self.buffer = []

    async def handle(self):
        await self.broker.connect()
        while True:
            data = await self.broker.receive()
            self.buffer.append(data)
            if len(self.buffer) >= self.batch_size:
                await self.send_batch()

    async def send_batch(self):
        print("Sending batch:", self.buffer)
        batch = json.dumps(self.buffer)
        await self.send_broker.send(batch)
        self.buffer.clear()
