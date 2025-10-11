from fastapi import FastAPI
from app.routers import test, tab_info_collection
from fastapi import WebSocket
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
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
app.include_router(test.router, prefix="/test", tags=["Neo4j test"])
