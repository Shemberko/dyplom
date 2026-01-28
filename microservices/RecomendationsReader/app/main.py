from fastapi import FastAPI
from app.routers import recommendations, authorization, profile
import os
from fastapi.middleware.cors import CORSMiddleware


# # --- OpenTelemetry setup ---
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry.sdk.resources import SERVICE_NAME, Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
# from opentelemetry import trace

# resource = Resource(attributes={
#     SERVICE_NAME: "recommendationsreader"
# })

# provider = TracerProvider(resource=resource)
# endpoint= os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")

# processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
# provider.add_span_processor(processor)
# trace.set_tracer_provider(provider)

app = FastAPI()

# main.py (FastAPI)

origins = [
    "http://localhost:5173",  # Дозволити ваш Vue App
    "http://127.0.0.1:5173",
    # Додайте продакшн домен, коли він з'явиться
    # "https://your-production-domain.com", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,             # Дозволяє куки та авторизаційні заголовки
    allow_methods=["*"],                # Дозволяє POST, GET, OPTIONS, etc.
    allow_headers=["*"],                # Дозволяє всі заголовки (Authorization, Content-Type, etc.)
)
# FastAPIInstrumentor.instrument_app(app)

# delete later
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(authorization.router, prefix="/sso", tags=["authorization"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
