from fastapi import APIRouter, Query, Depends
from typing import Dict, Any

from app.services.text_recommendation_builder_service import TextRecommendationBuilderService
from app.dependencies.auth import get_current_user_id

router = APIRouter()

content_rec_service = TextRecommendationBuilderService()

@router.get("")
async def get_content_recommendations(
    user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="Номер сторінки (починаючи з 1)"),
    size: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці")
) -> Dict[str, Any]:
    """
    Отримати контентні (текстові) рекомендації для користувача з пагінацією.
    Шукає статті, схожі за змістом на останню прочитану.
    """
    limit_needed = page * size
    
    recommendations = content_rec_service.recommend_top_n(
        user_id=user_id,
        n=limit_needed
    )

    if not recommendations:
        return {
            "data": [],
            "meta": {
                "page": page, 
                "size": size, 
                "total_found": 0,
                "has_next": False
            }
        }

    start_index = (page - 1) * size
    end_index = start_index + size
    
    paginated_data = recommendations[start_index:end_index]

    return {
        "data": paginated_data,
        "meta": {
            "page": page, 
            "size": size, 
            "total_fetched": len(recommendations),
            "has_next": end_index < len(recommendations)
        }
    }