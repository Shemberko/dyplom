"""
Тести для HistoryService — парсинг дат, сортування, фільтрація.
Файл: app/services/history_service.py
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.services.history_service import HistoryService


def _iso(days_ago: int = 0) -> str:
    """Хелпер: повертає ISO-рядок N днів тому від UTC-зараз."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _make_row(url: str, last_visited: str, visit_count: int = 1):
    return {
        "elementId": f"id:{url}",
        "url": url,
        "title": url.upper(),
        "image": None,
        "last_visited": last_visited,
        "visitedAt": None,
        "visit_count": visit_count,
    }


# ---------------------------------------------------------------------------
# get_user_history
# ---------------------------------------------------------------------------

def test_get_user_history_returns_sorted_by_date(mock_client):
    """Результат має бути відсортований від найновішого до найстарішого."""
    rows = [
        _make_row("older.com", _iso(days_ago=3)),
        _make_row("newest.com", _iso(days_ago=0)),
        _make_row("middle.com", _iso(days_ago=1)),
    ]
    mock_client.run_query.return_value = rows

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1", n=10, days_ago=7)

    assert result[0]["url"] == "newest.com"
    assert result[1]["url"] == "middle.com"
    assert result[2]["url"] == "older.com"


def test_get_user_history_filters_old_entries(mock_client):
    """Записи старіші за days_ago відкидаються."""
    rows = [
        _make_row("recent.com", _iso(days_ago=2)),
        _make_row("old.com", _iso(days_ago=10)),  # старіший за 7 днів
    ]
    mock_client.run_query.return_value = rows

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1", n=10, days_ago=7)

    urls = [r["url"] for r in result]
    assert "recent.com" in urls
    assert "old.com" not in urls


def test_get_user_history_handles_list_visitedAt(mock_client):
    """visitedAt може бути списком — беремо останній елемент."""
    dt_str = _iso(days_ago=1)
    rows = [{
        "elementId": "id:list.com",
        "url": "list.com",
        "title": "LIST.COM",
        "image": None,
        "last_visited": None,
        "visitedAt": [_iso(days_ago=5), dt_str],  # список — беремо dt_str
        "visit_count": 1,
    }]
    mock_client.run_query.return_value = rows

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1", n=10, days_ago=7)

    assert len(result) == 1
    assert result[0]["url"] == "list.com"


def test_get_user_history_skips_none_time(mock_client):
    """Запис без жодної мітки часу → пропускається."""
    rows = [{
        "elementId": "id:notime.com",
        "url": "notime.com",
        "title": "NOTIME",
        "image": None,
        "last_visited": None,
        "visitedAt": None,
        "visit_count": 1,
    }]
    mock_client.run_query.return_value = rows

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1", n=10, days_ago=7)

    assert result == []


def test_get_user_history_exception_returns_empty(mock_client):
    """Виняток при run_query → повертається []."""
    mock_client.run_query.side_effect = Exception("Neo4j down")

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1")

    assert result == []


def test_get_user_history_respects_n_limit(mock_client):
    """Повертається не більше n записів."""
    rows = [_make_row(f"site{i}.com", _iso(days_ago=i)) for i in range(10)]
    mock_client.run_query.return_value = rows

    service = HistoryService(client=mock_client)
    result = service.get_user_history("u1", n=3, days_ago=30)

    assert len(result) == 3


# ---------------------------------------------------------------------------
# clear_user_history
# ---------------------------------------------------------------------------

def test_clear_user_history_returns_true(mock_client):
    """run_query без помилки → True."""
    mock_client.run_query.return_value = []

    service = HistoryService(client=mock_client)
    assert service.clear_user_history("u1") is True


def test_clear_user_history_returns_false_on_exception(mock_client):
    """run_query кидає → False."""
    mock_client.run_query.side_effect = RuntimeError("fail")

    service = HistoryService(client=mock_client)
    assert service.clear_user_history("u1") is False


# ---------------------------------------------------------------------------
# delete_visit
# ---------------------------------------------------------------------------

def test_delete_visit_returns_true_when_found(mock_client):
    """run_query повертає результат → True."""
    mock_client.run_query.return_value = [{"success": True}]

    service = HistoryService(client=mock_client)
    assert service.delete_visit("u1", "4:abc:1") is True


def test_delete_visit_returns_false_when_not_found(mock_client):
    """run_query повертає [] → False."""
    mock_client.run_query.return_value = []

    service = HistoryService(client=mock_client)
    assert service.delete_visit("u1", "4:abc:1") is False


def test_delete_visit_returns_false_on_exception(mock_client):
    """Виняток → False."""
    mock_client.run_query.side_effect = Exception("error")

    service = HistoryService(client=mock_client)
    assert service.delete_visit("u1", "4:abc:1") is False
