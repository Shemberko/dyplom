import asyncio
import os
from services.comunication.rabbit_mq_service import RabbitMQBroker

# --- OpenTelemetry setup ---
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

resource = Resource(attributes={
    SERVICE_NAME: "rawdatacollector"
})

provider = TracerProvider(resource=resource)
endpoint= os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

async def main():
    amqp_url=os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq/")
    broker = RabbitMQBroker(
        amqp_url=amqp_url,
        queue_name="raw_data_queue"
    )
    await broker.connect()
    print("Waiting for messages. To exit press CTRL+C")
    try:
        while True:
            message = await broker.receive()
            # Створюємо спан для обробки повідомлення

            attributes = {
                "messaging.system": "rabbitmq",
                "messaging.destination": broker.queue_name,
                "messaging.message_payload_size": len(message),
                "messaging.message_preview": message[:200],  # короткий превью
                "app.environment": os.getenv("ENV", "dev"),
            }
            with tracer.start_as_current_span("process_rabbitmq_message", attributes=attributes) as span:
                print(f"Received message: {message}")
    finally:
        await broker.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully.")