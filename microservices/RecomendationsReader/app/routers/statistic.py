from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.user_statistic_service import UserStatisticService
from app.dependencies.auth import get_current_user_id

router = APIRouter()
stats_service = UserStatisticService()

@router.get("")
async def get_user_dashboard(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Отримати повну статистику користувача для дашборду:
    - Загальні цифри (візити, категорії)
    - Топ категорій інтересів
    - Активність за останні 7 днів
    - Розподіл за годинами доби
    """
    stats = stats_service.get_user_dashboard_data(user_id)
    
    if not stats:
        # Якщо даних немає (новий юзер), повертаємо пусту структуру замість 404,
        # щоб фронтенд міг відмалювати пусті графіки
        return {
            "summary": {"total_visits": 0, "unique_pages": 0, "total_categories": 0},
            "top_categories": [],
            "activity_chart": [],
            "browsing_habits": []
        }
    
    return stats

@router.get("/summary")
async def get_stats_summary(
    user_id: str = Depends(get_current_user_id)
):
    """Отримати тільки короткий підсумок (числові показники)."""
    summary = stats_service._get_general_summary(user_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Статистика не знайдена")
    return summary