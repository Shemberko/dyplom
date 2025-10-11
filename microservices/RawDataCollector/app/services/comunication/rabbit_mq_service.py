import asyncio
import aio_pika
from ..abstractions.message_broker import MessageBroker

class RabbitMQBroker(MessageBroker):
    def __init__(self, amqp_url, queue_name, topic_exchange=None, routing_key="#"):
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.topic_exchange_name = topic_exchange
        self.routing_key = routing_key
        self.connection = None
        self.channel = None
        self.queue = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        if self.topic_exchange_name:
            self.exchange = await self.channel.declare_exchange(
                self.topic_exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )
            self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
            await self.queue.bind(self.exchange, routing_key=self.routing_key)
        else:
            self.queue = await self.channel.declare_queue(self.queue_name, durable=True)

    async def send(self, message):
        msg = aio_pika.Message(body=message.encode())
        if self.exchange:
            await self.exchange.publish(msg, routing_key=self.routing_key)
        else:
            await self.channel.default_exchange.publish(
                msg, routing_key=self.queue_name
            )

    async def receive(self):
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    return message.body.decode()

    async def disconnect(self):
        await self.connection.close()