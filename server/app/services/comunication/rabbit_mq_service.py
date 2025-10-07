import asyncio
import aio_pika
from app.services.abstractions.message_broker import MessageBroker

class RabbitMQBroker(MessageBroker):
    def __init__(self, amqp_url, queue_name):
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.queue = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        self.queue = await self.channel.declare_queue(self.queue_name, durable=True)

    async def send(self, message):
        await self.channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=self.queue_name
        )

    async def receive(self):
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    return message.body.decode()

    async def disconnect(self):
        await self.connection.close()