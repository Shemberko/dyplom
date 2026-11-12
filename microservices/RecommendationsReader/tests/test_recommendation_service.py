"""
Тести для RecommendationService (GraphSAGE / hybrid vector search).
Файл: app/services/recommendation_builder_service.py
"""
import pytest
from unittest.mock import MagicMock
from app.services.recommendation_builder_service import RecommendationService


# ---------------------------------------------------------------------------
# recommend_top_n
# ---------------------------------------------------------------------------

def test_recommend_top_n_fallback_when_no_embedding(mock_client):
    """Якщо у юзера немає embedding → викликається trending fallback."""
    mock_client.run_one.return_value = None  # немає профілю
    mock_client.run_query.return_value = [
        {"url": "http://a.com", "title": "A", "image": None}
    ]

    service = RecommendationService(client=mock_client)
    result = service.recommend_top_n("user_no_profile", n=5)

    # run_one викликався для отримання embedding
    mock_client.run_one.assert_called_once()
    # run_query викликався для trending fallback
    mock_client.run_query.assert_called_once()
    assert isinstance(result, list)


def test_recommend_top_n_calls_vector_search_when_embedding_exists(mock_client):
    """Якщо embedding є → викликається vector search через run_query."""
    mock_client.run_one.return_value = {"emb": [0.1, 0.2, 0.3]}
    mock_client.run_query.return_value = [
        {
            "elementId": "4:abc:1",
            "url": "http://b.com",
            "title": "B",
            "image": None,
            "score": 0.95,
        }
    ]

    service = RecommendationService(client=mock_client)
    result = service.recommend_top_n("user_with_profile", n=1)

    mock_client.run_query.assert_called_once()
    assert len(result) == 1
    assert result[0]["url"] == "http://b.com"


# ---------------------------------------------------------------------------
# _vector_search
# ---------------------------------------------------------------------------

def test_vector_search_formats_result_correctly(mock_client):
    """Перевіряємо маппинг полів: elementId → id, score округлюється."""
    mock_client.run_query.return_value = [
        {
            "elementId": "4:abc:42",
            "url": "http://c.com",
            "title": "C",
            "image": "http://img.com",
            "score": 0.987654,
        }
    ]

    service = RecommendationService(client=mock_client)
    result = service._vector_search("u1", [0.1, 0.2], 5)

    assert result[0]["id"] == "4:abc:42"
    assert result[0]["score"] == round(0.987654, 4)
    assert result[0]["title"] == "C"


def test_vector_search_returns_empty_on_exception(mock_client):
    """Якщо run_query кидає виняток → повертається []."""
    mock_client.run_query.side_effect = Exception("DB error")

    service = RecommendationService(client=mock_client)
    result = service._vector_search("u1", [0.1], 5)

    assert result == []


# ---------------------------------------------------------------------------
# track_user_visit
# ---------------------------------------------------------------------------

def test_track_user_visit_returns_true_on_success(mock_client):
    """Успішний трекінг → True."""
    mock_client.run_query.return_value = [{"visit_id": "4:xyz:99"}]

    service = RecommendationService(client=mock_client)
    result = service.track_user_visit("u1", "4:abc:1", "recommendation")

    assert result is True


def test_track_user_visit_returns_false_on_exception(mock_client):
    """Виняток при запиті → False."""
    mock_client.run_query.side_effect = RuntimeError("connection lost")

    service = RecommendationService(client=mock_client)
    result = service.track_user_visit("u1", "4:abc:1")

    assert result is False


def test_track_user_visit_returns_false_when_empty_result(mock_client):
    """run_query повертає [] (вузол не знайдено) → False."""
    mock_client.run_query.return_value = []

    service = RecommendationService(client=mock_client)
    result = service.track_user_visit("u1", "4:abc:1")

    assert result is False
