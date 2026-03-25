from fastapi import APIRouter, Query, Depends
from typing import Dict, Any

from app.services.history_service import HistoryService
from app.dependencies.auth import get_current_user_id

router = APIRouter(tags=["History"])
history_service = HistoryService()

@router.get("")
async def get_history(
    user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="Номер сторінки (починаючи з 1)"),
    size: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці"),
    days: int = Query(7, ge=1, description="За скільки останніх днів показати історію")
) -> Dict[str, Any]:
    """
    Отримати історію переглядів для користувача з пагінацією та фільтром по днях.
    """
    limit_needed = page * size
    
    history_records = history_service.get_user_history(
        user_id=user_id,
        n=limit_needed,
        days_ago=days
    )

    if not history_records:
        return {
            "data": [],
            "meta": {"page": page, "size": size, "days": days, "total_found": 0}
        }

    start_index = (page - 1) * size
    end_index = start_index + size
    
    paginated_data = history_records[start_index:end_index]

    return {
        "data": paginated_data,
        "meta": {
            "page": page, 
            "size": size, 
            "days": days,
            "total_found": len(history_records),
            "has_next": end_index < len(history_records)
        }
    }

@router.delete("/{page_id}")
async def remove_visit_from_history(
    page_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """
    Видалити сторінку з історії переглядів користувача.
    Якщо візит впливав на рекомендації (tracked: true), 
    математично віднімає вплив цієї сторінки з вектора користувача.
    """
    success = history_service.delete_visit(user_id=user_id, page_id=page_id)
    
    if not success:
        return {
            "status": "success", 
            "message": " Не знайдено."
        }
        
    return {
        "status": "success", 
        "message": "Сторінку успішно видалено з історії. Профіль перераховано."
    }