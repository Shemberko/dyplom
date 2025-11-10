import os
from fastapi import FastAPI
from app.routers import test, tab_info_collection
from fastapi import WebSocket
from app.services.comunication.web_socket_broker import WebSocketBroker
from app.services.comunication.web_socket_rx_service import WebSocketRxService
from app.services.comunication.rabbit_mq_service import RabbitMQBroker

# --- OpenTelemetry setup ---
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry import trace

resource = Resource(attributes={
    SERVICE_NAME: "fastapi-server"
})

provider = TracerProvider(resource=resource)
endpoint= os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
app.include_router(test.router, prefix="/test", tags=["Neo4j test"])
app.include_router(tab_info_collection.router, prefix="/data", tags=["Tab Info Collection"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    amqp_url=os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq/")
    broker = WebSocketBroker(websocket)
    send_broker = RabbitMQBroker(amqp_url, "raw_click_queue")
    await send_broker.connect()

    rx_service = WebSocketRxService(broker, send_broker, batch_size=5)
    await rx_service.handle()

#  uvicorn app.main:app --reload
# docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# docker stop rabbitmq
# docker rm rabbitmq
#  docker run -d --name jaeger   -e COLLECTOR_OTLP_ENABLED=true  -p 16686:16686 -p 4318:4318  jaegertracing/all-in-one:latest
# docker-compose logs -f rawdatacollector
# docker compose up --build -d
# docker attach rawdatacollector