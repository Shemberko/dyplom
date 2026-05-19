import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# Патчимо neo4j.GraphDatabase.driver щоб HistoryService (через BaseService)
# не намагався підключитися до реального Neo4j під час збирання тестів.
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def _patch_neo4j_driver():
    """Замінює neo4j.GraphDatabase.driver на MagicMock для всієї тестової сесії."""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()
        yield mock_driver


# =============================================================================
# Патчимо ollama.Client, щоб FiltrationService / CategorizationService /
# EmbeddingsService не намагались підключитись до Ollama при імпорті.
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def _patch_ollama_client():
    """Замінює ollama.Client на MagicMock для всієї тестової сесії."""
    with patch("ollama.Client") as mock_ollama:
        mock_ollama.return_value = MagicMock()
        yield mock_ollama
