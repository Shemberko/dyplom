from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

# Імпортуємо ваш сервіс (припускаємо, що він у файлі services.py)
from app.services.recomendation_builder_service import RecommendationService

router = APIRouter()
rec_service = RecommendationService() # Ініціалізація сервісу

@router.get("/{user_id}")
async def get_recommendations(
    user_id: str,
    page: int = Query(1, ge=1, description="Номер сторінки (починаючи з 1)"),
    size: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці"),
    weight_struct: float = Query(0.5, ge=0.0, le=1.0, description="Вага структурних ембедінгів")
) -> Dict[str, Any]:
    """
    Отримати рекомендації для користувача з пагінацією.
    """
    
    # 1. Рахуємо, скільки всього кандидатів нам треба взяти з бази, 
    # щоб забезпечити цю сторінку.
    # Наприклад, якщо page=2, size=10, нам треба мінімум 20 найкращих результатів.
    limit_needed = page * size
    
    # Ми беремо трохи більше кандидатів (candidate_limit), щоб мати з чого вибирати 
    # після сортування за схожістю. Якщо у вас всього 2000 кандидатів,
    # то candidate_limit=2000 - це ок.
    # Але для пагінації ми передаємо у recommend_top_n саме `limit_needed`.
    
    recommendations = rec_service.recommend_top_n(
        user_id=user_id,
        n=limit_needed, # Отримуємо топ-N (де N = кінець поточної сторінки)
        candidate_limit=2000, # Скільки всього кандидатів розглядаємо
        weight_struct=weight_struct
    )

    if not recommendations:
        return {
            "data": [],
            "meta": {"page": page, "size": size, "total_found": 0}
        }

    # 2. Робимо "зріз" (Slicing) для конкретної сторінки
    start_index = (page - 1) * size
    end_index = start_index + size
    
    paginated_data = recommendations[start_index:end_index]

    # 3. Повертаємо дані разом з мета-інформацією
    return {
        "data": paginated_data,
        "meta": {
            "page": page, 
            "size": size, 
            "total_found": len(recommendations), # Скільки всього знайшли релевантного
            "has_next": end_index < len(recommendations)
        }
    }