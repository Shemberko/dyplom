from fastapi import APIRouter, Query, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from fastapi import BackgroundTasks


from app.services.unified_recommendation_service import UnifiedRecommendationService
from app.dependencies.auth import get_current_user_id

from app.services.recomendation_builder_service import RecommendationService
rec_service = RecommendationService()

router = APIRouter()

def get_recommendation_service() -> UnifiedRecommendationService:
    """
    Провайдер сервісу рекомендацій. 
    Дозволяє легко підміняти сервіс під час написання тестів (Mocking).
    """
    return UnifiedRecommendationService()


@router.get("", summary="Отримати зважені гібридні рекомендації")
async def get_recommendations(
    user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="Номер сторінки (починаючи з 1)"),
    size: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці"),
    weight_struct: float = Query(0.7, ge=0.0, le=1.0, description="Вага: 0.0=Тільки Текст, 1.0=Тільки Граф"),
    rec_service: UnifiedRecommendationService = Depends(get_recommendation_service)
) -> Dict[str, Any]:
    """
    Повертає персоналізовані рекомендації для користувача з пагінацією.
    
    Алгоритм зливає результати двох векторних пошуків:
    - Content-Based (Текстова схожість через LLM-summary)
    - GraphSAGE (Структурна схожість через категорії та історію)
    
    Вага регулюється параметром `weight_struct`.
    """
    data, total_found = rec_service.get_recommendations(
        user_id=user_id, 
        page=page, 
        size=size, 
        weight_struct=weight_struct
    )

    return {
        "data": data,
        "meta": {
            "page": page,
            "size": size,
            "total_found": total_found,
            "has_next": (page * size) < total_found
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

    actual_user_id = current_user_id or visit.user_id

    background_tasks.add_task(
        rec_service.track_user_visit,
        user_id=actual_user_id,
        page_id=visit.page_id,
        source=visit.source
    )

    return {
        "status": "success", 
        "message": "Visit tracking queued"
    }