import os
from fastapi import APIRouter
from app.db.neo4j import get_driver
from fastapi import Request
from app.services.comunication.rabbit_mq_service import RabbitMQBroker
import httpx

router = APIRouter()
@router.post("/post-collected-data")
async def post_collected_data(request: Request):
    data = await request.json()

    amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq/")
    broker = RabbitMQBroker(amqp_url, "raw_data_queue")

    await broker.connect()
    await broker.send(data)

    return {"status": "success"}
