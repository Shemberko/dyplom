import asyncio
import os
from services.comunication.rabbit_mq_service import RabbitMQBroker
from services.json_message_processor import JsonMessageProcessor


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

# ...existing code...
async def main():
    amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq/")
    broker = RabbitMQBroker(
        amqp_url=amqp_url,
        queue_name="raw_data_queue"
    )

    # retry connect loop: RABBITMQ_CONNECT_RETRIES=0 -> infinite retries
    max_retries = int(os.getenv("RABBITMQ_CONNECT_RETRIES", "5"))
    delay = float(os.getenv("RABBITMQ_CONNECT_DELAY", "5"))
    attempt = 0

    while True:
        try:
            await broker.connect()
            print("Connected to RabbitMQ")
            break
        except Exception as e:
            attempt += 1
            print(f"RabbitMQ connect attempt {attempt} failed: {e}")
            if max_retries > 0 and attempt >= max_retries:
                print("Max RabbitMQ connect retries reached, exiting main()")
                return  # do not crash the container with an unhandled exception
            await asyncio.sleep(delay)

    print("Waiting for messages. To exit press CTRL+C")
    try:
        while True:
            message = await broker.receive()
            print(f"Received message: {message}")

            JsonMessageProcessor().process(message)
    finally:
        await broker.disconnect()
# ...existing code...
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully.")