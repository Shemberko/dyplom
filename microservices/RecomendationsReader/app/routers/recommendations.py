from fastapi import APIRouter, HTTPException, Query, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.recomendation_builder_service import RecommendationService
from app.dependencies.auth import get_current_user_id
from pydantic import BaseModel
from fastapi import BackgroundTasks

router = APIRouter()
rec_service = RecommendationService()

@router.get("")
async def get_recommendations(
    user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="Номер сторінки (починаючи з 1)"),
    size: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці"),
    weight_struct: float = Query(0.5, ge=0.0, le=1.0, description="Вага структурних ембедінгів")
) -> Dict[str, Any]:
    """
    Отримати рекомендації для користувача з пагінацією.
    """
    limit_needed = page * size
    recommendations = rec_service.recommend_top_n(
        user_id=user_id,
        n=limit_needed)

    if not recommendations:
        return {
            "data": [],
            "meta": {"page": page, "size": size, "total_found": 0}
        }

    start_index = (page - 1) * size
    end_index = start_index + size
    
    paginated_data = recommendations[start_index:end_index]

    return {
        "data": paginated_data,
        "meta": {
            "page": page, 
            "size": size, 
            "total_found": len(recommendations),
            "has_next": end_index < len(recommendations)
        }
    }

class VisitRequest(BaseModel):
    user_id: str
    page_id: str
    source: str = "recommendation"

@router.post("/visit")
async def track_visit(
    visit: VisitRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """
    Записати подію відвідування сторінки користувачем.
    Виконується асинхронно (у фоні), щоб не блокувати клієнта.
    """
    
    # Перевірка безпеки: переконуємось, що користувач записує візит для себе,
    # або просто ігноруємо user_id з фронтенду і беремо надійний з JWT-токена.
    actual_user_id = current_user_id or visit.user_id

    # Додаємо задачу у фоновий пул FastAPI
    background_tasks.add_task(
        rec_service.track_user_visit,
        user_id=actual_user_id,
        page_id=visit.page_id,
        source=visit.source
    )

    # Миттєво відповідаємо фронтенду, що запит прийнято
    return {
        "status": "success", 
        "message": "Visit tracking queued"
    }