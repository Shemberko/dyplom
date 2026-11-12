"""
Тести для TextRecommendationBuilderService (content-based рекомендації).
Файл: app/services/text_recommendation_builder_service.py
"""
import pytest
from unittest.mock import MagicMock
from app.services.text_recommendation_builder_service import TextRecommendationBuilderService


# ---------------------------------------------------------------------------
# recommend_top_n
# ---------------------------------------------------------------------------

def test_recommend_top_n_fallback_when_no_text_embedding(mock_client):
    """Якщо у юзера немає text_embedding → викликається trending fallback."""
    mock_client.run_one.return_value = None
    mock_client.run_query.return_value = [
        {"url": "http://trend.com", "title": "Trend", "image": None}
    ]

    service = TextRecommendationBuilderService(client=mock_client)
    result = service.recommend_top_n("u_no_profile", n=3)

    mock_client.run_query.assert_called_once()
    assert isinstance(result, list)


def test_recommend_top_n_with_text_embedding_calls_vector_search(mock_client):
    """Якщо text_embedding є → викликається vector search."""
    mock_client.run_one.return_value = {"emb": [0.1] * 384}
    mock_client.run_query.return_value = [
        {
            "elementId": "4:abc:10",
            "url": "http://page.com",
            "title": "Page",
            "image": "http://img.com",
            "score": 0.88,
        }
    ]

    service = TextRecommendationBuilderService(client=mock_client)
    result = service.recommend_top_n("u1", n=1)

    mock_client.run_query.assert_called_once()
    assert len(result) == 1
    assert result[0]["type"] == "content-based"


# ---------------------------------------------------------------------------
# _vector_search
# ---------------------------------------------------------------------------

def test_vector_search_formats_output_correctly(mock_client):
    """Перевіряємо: elementId → id, score округлюється, type='content-based'."""
    mock_client.run_query.return_value = [
        {
            "elementId": "4:abc:55",
            "url": "http://x.com",
            "title": "X",
            "image": None,
            "score": 0.999999,
        }
    ]

    service = TextRecommendationBuilderService(client=mock_client)
    result = service._vector_search("u1", [0.1] * 384, 5)

    assert result[0]["id"] == "4:abc:55"
    assert result[0]["score"] == round(0.999999, 4)
    assert result[0]["type"] == "content-based"


def test_vector_search_returns_empty_on_exception(mock_client):
    """Виняток в run_query → []."""
    mock_client.run_query.side_effect = Exception("Index not found")

    service = TextRecommendationBuilderService(client=mock_client)
    result = service._vector_search("u1", [0.1], 5)

    assert result == []


# ---------------------------------------------------------------------------
# _get_trending_fallback
# ---------------------------------------------------------------------------

def test_trending_fallback_maps_to_type_trending(mock_client):
    """Trending fallback додає type='trending' і score=0.0."""
    mock_client.run_query.return_value = [
        {"url": "http://t.com", "title": "T", "image": None}
    ]

    service = TextRecommendationBuilderService(client=mock_client)
    result = service._get_trending_fallback(5)

    assert result[0]["type"] == "trending"
    assert result[0]["score"] == 0.0


def test_trending_fallback_empty(mock_client):
    """Якщо БД порожня → []."""
    mock_client.run_query.return_value = []

    service = TextRecommendationBuilderService(client=mock_client)
    result = service._get_trending_fallback(5)

    assert result == []
