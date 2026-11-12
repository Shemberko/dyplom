"""
Тести для UnifiedRecommendationService — найскладніша логіка злиття scores.
Файл: app/services/unified_recommendation_service.py
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.unified_recommendation_service import UnifiedRecommendationService


# ---------------------------------------------------------------------------
# Хелпер: генерація фейкових результатів vector search
# ---------------------------------------------------------------------------

def _make_page(pid: str, score: float):
    return {
        "id": pid,
        "url": f"http://{pid}.com",
        "title": pid.upper(),
        "image": None,
        "score": score,
        "visit_count": 0,
        "last_visited": None,
    }


# ---------------------------------------------------------------------------
# Fallback (немає embeddings)
# ---------------------------------------------------------------------------

def test_fallback_when_no_embeddings(mock_client):
    """Обидва embedding None → trending fallback викликається."""
    mock_client.run_one.return_value = {}  # порожній профіль
    mock_client.run_query.return_value = []

    service = UnifiedRecommendationService(client=mock_client)
    result, total = service.get_recommendations("u1", page=1, size=5, weight_struct=0.7)

    assert result == []
    assert total == 0


def test_fallback_when_profile_missing(mock_client):
    """run_one повертає None → trending fallback."""
    mock_client.run_one.return_value = None
    mock_client.run_query.return_value = []

    service = UnifiedRecommendationService(client=mock_client)
    result, total = service.get_recommendations("u1", page=1, size=5, weight_struct=0.5)

    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Злиття scores
# ---------------------------------------------------------------------------

def test_merging_scores_combined_weight(mock_client):
    """
    Одна сторінка є в обох джерелах.
    final_score = t_score*(1-w) + h_score*w  де w=0.5
    """
    mock_client.run_one.return_value = {
        "text_emb": [0.1] * 5,
        "hybrid_emb": [0.2] * 5,
    }

    page_id = "p1"

    def fake_vector_search(index_name, user_id, embedding, k):
        if "text" in index_name:
            return [_make_page(page_id, 0.8)]
        else:
            return [_make_page(page_id, 0.6)]

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_vector_search

    result, total = service.get_recommendations("u1", page=1, size=10, weight_struct=0.5)

    assert total == 1
    expected_score = round(0.8 * 0.5 + 0.6 * 0.5, 4)
    assert result[0]["score"] == expected_score


def test_rec_type_mixed_when_scores_close(mock_client):
    """Якщо |h_score - t_score| <= 0.03 → type == 'mixed'."""
    mock_client.run_one.return_value = {
        "text_emb": [0.1],
        "hybrid_emb": [0.2],
    }

    def fake_search(index_name, user_id, embedding, k):
        return [_make_page("p1", 0.9)]

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_search

    result, _ = service.get_recommendations("u1", page=1, size=10, weight_struct=0.5)
    assert result[0]["type"] == "mixed"


def test_rec_type_hybrid_when_h_score_greater(mock_client):
    """Якщо h_score > t_score і різниця > 0.03 → type == 'hybrid'."""
    mock_client.run_one.return_value = {
        "text_emb": [0.1],
        "hybrid_emb": [0.2],
    }

    def fake_search(index_name, user_id, embedding, k):
        if "text" in index_name:
            return [_make_page("p1", 0.5)]
        else:
            return [_make_page("p1", 0.9)]

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_search

    result, _ = service.get_recommendations("u1", page=1, size=10, weight_struct=0.5)
    assert result[0]["type"] == "hybrid"


def test_rec_type_text_only(mock_client):
    """Сторінка тільки в text_recs → type == 'text'."""
    mock_client.run_one.return_value = {
        "text_emb": [0.1],
        "hybrid_emb": None,
    }

    def fake_search(index_name, user_id, embedding, k):
        if "text" in index_name:
            return [_make_page("p1", 0.8)]
        return []

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_search

    result, _ = service.get_recommendations("u1", page=1, size=10, weight_struct=0.0)
    assert result[0]["type"] == "text"


def test_low_score_items_filtered_out(mock_client):
    """Елементи з final_score < 0.1 відкидаються."""
    mock_client.run_one.return_value = {
        "text_emb": [0.1],
        "hybrid_emb": None,
    }

    def fake_search(index_name, user_id, embedding, k):
        return [_make_page("p_low", 0.05)]  # дуже низький score

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_search

    result, total = service.get_recommendations("u1", page=1, size=10, weight_struct=0.0)
    assert total == 0
    assert result == []


# ---------------------------------------------------------------------------
# Пагінація
# ---------------------------------------------------------------------------

def test_pagination_returns_correct_slice(mock_client):
    """page=2, size=2 → повертаємо елементи з індексу 2..3."""
    mock_client.run_one.return_value = {
        "text_emb": [0.1],
        "hybrid_emb": None,
    }

    pages = [_make_page(f"p{i}", 0.9 - i * 0.05) for i in range(6)]

    def fake_search(index_name, user_id, embedding, k):
        return pages

    service = UnifiedRecommendationService(client=mock_client)
    service._vector_search = fake_search

    result, total = service.get_recommendations("u1", page=2, size=2, weight_struct=0.0)
    assert len(result) == 2
    assert total == 6


# ---------------------------------------------------------------------------
# Trending fallback (внутрішній метод)
# ---------------------------------------------------------------------------

def test_trending_fallback_empty_db(mock_client):
    """Якщо в БД немає візитів → fallback повертає [] та total=0."""
    mock_client.run_query.return_value = []

    service = UnifiedRecommendationService(client=mock_client)
    result, total = service._get_trending_fallback(page=1, size=5)

    assert result == []
    assert total == 0
