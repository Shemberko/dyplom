"""
Тести для UserStatisticService.
Файл: app/services/user_statistic_service.py
"""
import pytest
from unittest.mock import MagicMock, call
from app.services.user_statistic_service import UserStatisticService


# ---------------------------------------------------------------------------
# get_user_dashboard_data
# ---------------------------------------------------------------------------

def test_dashboard_returns_all_four_sections(mock_client):
    """Результат містить усі 4 ключі: summary, top_categories, activity_chart, browsing_habits."""
    mock_client.run_one.return_value = {
        "total_visits": 10,
        "unique_pages": 8,
        "total_categories": 3,
    }
    mock_client.run_query.return_value = []

    service = UserStatisticService(client=mock_client)
    result = service.get_user_dashboard_data("u1")

    assert "summary" in result
    assert "top_categories" in result
    assert "activity_chart" in result
    assert "browsing_habits" in result


def test_dashboard_exception_returns_empty_dict(mock_client):
    """Якщо будь-який внутрішній виклик кидає виняток → повертається {}."""
    mock_client.run_one.side_effect = Exception("DB connection error")

    service = UserStatisticService(client=mock_client)
    result = service.get_user_dashboard_data("u1")

    assert result == {}


def test_dashboard_calls_run_query_three_times(mock_client):
    """
    _get_top_categories, _get_activity_by_day, _get_browsing_time_stats
    кожен робить виклик run_query → разом 3 виклики.
    """
    mock_client.run_one.return_value = {"total_visits": 0, "unique_pages": 0, "total_categories": 0}
    mock_client.run_query.return_value = []

    service = UserStatisticService(client=mock_client)
    service.get_user_dashboard_data("u1")

    assert mock_client.run_query.call_count == 3


# ---------------------------------------------------------------------------
# _get_general_summary (внутрішній метод)
# ---------------------------------------------------------------------------

def test_general_summary_passes_user_id(mock_client):
    """run_one викликається з правильним user_id."""
    mock_client.run_one.return_value = {"total_visits": 5, "unique_pages": 4, "total_categories": 2}
    mock_client.run_query.return_value = []

    service = UserStatisticService(client=mock_client)
    service._get_general_summary("test_user_42")

    # Перевіряємо, що параметр user_id переданий у виклику run_one
    call_args = mock_client.run_one.call_args
    assert call_args[0][1] == {"user_id": "test_user_42"}


# ---------------------------------------------------------------------------
# _get_top_categories (внутрішній метод)
# ---------------------------------------------------------------------------

def test_top_categories_returns_list_from_run_query(mock_client):
    """_get_top_categories повертає те, що повернув run_query."""
    expected = [{"name": "Tech", "value": 5}, {"name": "Sport", "value": 3}]
    mock_client.run_query.return_value = expected

    service = UserStatisticService(client=mock_client)
    result = service._get_top_categories("u1")

    assert result == expected
