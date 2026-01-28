from fastapi import APIRouter, HTTPException, Query, Depends, HTTPException
from typing import List, Dict, Any, Optional

# Імпортуємо ваш сервіс (припускаємо, що він у файлі services.py)
from app.services.authorization.profile_service import profile_service
from app.dependencies.auth import get_current_user_id

router = APIRouter()

@router.get("")
async def profile(
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Отримати профіль користувача.
    """

    profile_data = profile_service.get_user_profile(user_id)
    
    if not profile_data:
        # Це має бути неможливо, якщо get_current_user_id успішно спрацював,
        # але це запобігає збою.
        raise ValueError(f"User with ID {user_id} not found in database.")
 
    return profile_data