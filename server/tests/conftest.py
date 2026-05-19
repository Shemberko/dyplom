import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# Патчимо OTEL exporter і aio_pika, щоб імпорт app.main не падав
# без реального Jaeger / RabbitMQ.
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def _patch_otel():
    """Замінює OTLPSpanExporter, щоб не намагатись з'єднатись з Jaeger."""
    with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as m:
        m.return_value = MagicMock()
        yield m
