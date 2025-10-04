from fastapi import FastAPI
from app.routers import test, tab_info_collection
from fastapi import WebSocket
from app.services.message_brokers.web_socket_broker import WebSocketBroker
from app.services.comunication.web_socket_rx_service import WebSocketRxService
#  uvicorn app.main:app --reload

app = FastAPI()
app.include_router(test.router, prefix="/test", tags=["Neo4j test"])
app.include_router(tab_info_collection.router, prefix="/data", tags=["Tab Info Collection"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    broker = WebSocketBroker(websocket)
    rx_service = WebSocketRxService(broker)
    await rx_service.handle()