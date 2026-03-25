from fastapi import APIRouter
from typing import Dict
from app.services.stats_service import StatsService

router = APIRouter()
stats_service = StatsService()

@router.get("")
async def get_general_stats() -> Dict[str, int]:
    """
    Отримати загальну статистику платформи.
    Ендпоінт публічний (не потребує авторизації).
    """
    return stats_service.get_platform_stats()