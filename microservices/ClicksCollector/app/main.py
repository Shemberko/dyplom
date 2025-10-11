# import asyncio
# from services.comunication.rabbit_mq_service import RabbitMQBroker 

# async def main():
#     broker = RabbitMQBroker(
#         amqp_url="amqp://guest:guest@localhost/",
#         queue_name="raw_click_queue",
#         # topic_exchange="data_exchange",
#         # routing_key="raw.data"
#     )
#     await broker.connect()
#     print("Waiting for messages. To exit press CTRL+C")
#     try:
#         while True:
#             message = await broker.receive()
#             print(f"Received message: {message}")
#     finally:
#         await broker.disconnect()

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\nProgram interrupted by user. Exiting gracefully.")

import asyncio
from services.comunication.rabbit_mq_service import RabbitMQBroker

# --- OpenTelemetry setup ---
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

resource = Resource(attributes={
    SERVICE_NAME: "clickscollector"
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

async def main():
    broker = RabbitMQBroker(
    amqp_url="amqp://guest:guest@localhost/",
    queue_name="raw_click_queue",
    # topic_exchange="data_exchange",
    # routing_key="raw.data"
    )
    await broker.connect()
    print("Waiting for messages. To exit press CTRL+C")
    try:
        while True:
            message = await broker.receive()
            # Створюємо спан для обробки повідомлення
            with tracer.start_as_current_span("process_rabbitmq_message"):
                print(f"Received message: {message}")
                # тут твоя логіка обробки
    finally:
        await broker.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully.")