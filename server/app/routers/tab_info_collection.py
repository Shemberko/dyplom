from fastapi import APIRouter
from app.db.neo4j import get_driver
from fastapi import Request
import aio_pika
from app.services.comunication.rabbit_mq_service import RabbitMQBroker

router = APIRouter()
@router.post("/post-collected-data")
async def post_collected_data(request: Request):
    data = await request.json()


    # Connect to RabbitMQ
    broker = RabbitMQBroker("amqp://guest:guest@localhost/", "raw_data_queue")
    # broker = RabbitMQBroker("amqp://guest:guest@localhost/", "raw_data_queue", topic_exchange="data_exchange", routing_key="raw.data")
    await broker.connect()
    await broker.send(data)

    return {"status": "success"}
