import asyncio
import os
import logging
from typing import Set

from services.comunication.rabbit_mq_service import RabbitMQBroker
from services.record_processing.record_processor_service import RecordProcessorService
from services.record_processing.feature_extraction_service import FeatureExtractionService

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "1"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

resource = Resource(attributes={SERVICE_NAME: "rawdatacollector"})
provider = TracerProvider(resource=resource)
endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
processor_span = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
provider.add_span_processor(processor_span)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

processor_service = RecordProcessorService() 
extractor_service = FeatureExtractionService()
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

async def process_message_task(message: bytes):
    """
    Фонова задача для обробки одного повідомлення.
    """
    async with semaphore:
        with tracer.start_as_current_span("process_message_flow"):
            try:
                extracted_data = extractor_service.parse_and_extract(message)
                if extracted_data:
                    user_id = extracted_data.get("user_id", "unknown")
                    await asyncio.to_thread(processor_service.process, extracted_data)
                    logger.info(f"Processed data for user: {user_id}")
                else:
                    logger.warning("Skipping message: extraction returned None")

            except Exception as e:
                logger.error(f"Error in processing task: {e}", exc_info=True)

async def main():
    amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq/")
    broker = RabbitMQBroker(amqp_url=amqp_url, queue_name="raw_data_queue")

    # Логіка реконнекту до RabbitMQ
    max_retries = int(os.getenv("RABBITMQ_CONNECT_RETRIES", "10"))
    delay = 5
    for attempt in range(1, max_retries + 1):
        try:
            await broker.connect()
            logger.info("Connected to RabbitMQ")
            break
        except Exception as e:
            logger.error(f"RabbitMQ connect attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                logger.critical("Could not connect to RabbitMQ. Exiting.")
                return
            await asyncio.sleep(delay)

    logger.info("Service started. Waiting for messages...")
    
    background_tasks: Set[asyncio.Task] = set()

    try:
        while True:
            message = await broker.receive()
            task = asyncio.create_task(process_message_task(message))
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

    except asyncio.CancelledError:
        logger.info("Stopping service...")
    finally:
        if background_tasks:
            logger.info(f"Waiting for {len(background_tasks)} active tasks to finish...")
            await asyncio.gather(*background_tasks, return_exceptions=True)
        
        await broker.disconnect()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass