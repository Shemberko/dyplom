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
    # save_url = os.getenv("SAVE_SERVICE_URL", "http://recomendationsreader:8001/data/save_data")
    # try:
    #     async with httpx.AsyncClient() as client:
    #         resp = await client.post(save_url, json=data, timeout=10.0)
    #         resp.raise_for_status()
    #         save_resp = resp.json()
    # except Exception as e:
    #     return {"status": "queued", "save_service": "error", "error": str(e)}

    return {"status": "success"}
