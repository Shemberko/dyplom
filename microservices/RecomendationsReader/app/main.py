from fastapi import FastAPI
from app.routers import recommendations
import os

# --- OpenTelemetry setup ---
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry import trace

resource = Resource(attributes={
    SERVICE_NAME: "recommendationsreader"
})

provider = TracerProvider(resource=resource)
endpoint= os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")

processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# delete later
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
