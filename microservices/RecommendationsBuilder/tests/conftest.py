import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# Патчимо Celery і Neo4j ДО будь-яких імпортів app-модулів.
#
# celery_worker.py при імпорті одразу створює `app = Celery(broker=..., backend=...)`
# і намагається з'єднатись. Патчимо Celery.
# query_runner.py → BaseService.__init__ → GraphDatabase.driver(...)
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def _patch_celery():
    """Замінює celery.Celery щоб не підключатись до RabbitMQ/Redis."""
    with patch("celery.Celery") as mock_celery:
        mock_app = MagicMock()
        mock_celery.return_value = mock_app
        # Celery task decorator: @app.task → повертає функцію як є
        mock_app.task = lambda *a, **kw: (lambda f: f)
        yield mock_celery


@pytest.fixture(scope="session", autouse=True)
def _patch_neo4j_driver():
    """Замінює neo4j.GraphDatabase.driver на MagicMock."""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()
        yield mock_driver


@pytest.fixture
def mock_client():
    """Загальний мок Neo4j QueryRunner для тестів."""
    client = MagicMock()
    client.run_query.return_value = []
    client.run_one.return_value = None
    return client
