import pytest
from unittest.mock import MagicMock, patch

# =============================================================================
# ВАЖЛИВО: query_runner.py на рівні модуля виконує `query_runner = QueryRunner()`,
# а QueryRunner.__init__ → BaseService.__init__ → GraphDatabase.driver(...)
# Патчимо driver ДО будь-якого імпорту app-модулів, щоб тести не падали
# через відсутність реального Neo4j.
# =============================================================================

# Цей патч активний протягом усієї сесії pytest
@pytest.fixture(scope="session", autouse=True)
def _patch_neo4j_driver():
    """Замінює neo4j.GraphDatabase.driver на MagicMock для всієї тестової сесії."""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()
        yield mock_driver


@pytest.fixture
def mock_client():
    """
    Мок QueryRunner — підміняємо run_query / run_one без реального Neo4j.
    Всі сервіси вже приймають `client: Any = None`, тому мок передається напряму.
    """
    client = MagicMock()
    client.run_query.return_value = []
    client.run_one.return_value = None
    return client
