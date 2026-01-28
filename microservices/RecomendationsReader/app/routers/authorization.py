import uuid
from fastapi import APIRouter, HTTPException

# [1] Імпорт моделей
from app.models.authorization import SsoRequest, TokenExchangeRequest, AuthResponse

# [2] Імпорт екземпляра сервісу
# Припускаємо, що auth_service.py знаходиться на рівень вище або у доступному модулі
from app.services.authorization.auth_service import auth_service 

router = APIRouter(tags=["SSO"])

@router.post("/generate-one-time-token", status_code=200)
async def generate_one_time_token_endpoint(request: SsoRequest):
    """
    Етап 1: Викликається розширенням Chrome.
    Обмінює Chrome ID на короткоживучий One-Time Token, використовуючи AuthService.
    """
    chrome_id = request.userId
    
    try:
        # ВИКОРИСТАННЯ СЕРВІСУ: делегуємо всю бізнес-логіку
        sso_token = auth_service.generate_one_time_token(chrome_id)
        
        return {"oneTimeToken": sso_token}
    
    except Exception as e:
        # Обробка загальних помилок (наприклад, проблем з драйвером Neo4j)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during token generation: {e}"
        )


@router.post("/exchange-token", response_model=AuthResponse)
async def exchange_token_for_jwt_endpoint(request: TokenExchangeRequest):
    """
    Етап 2: Викликається фронтендом.
    Обмінює One-Time Token на постійний JWT, використовуючи AuthService.
    """
    sso_token = request.token
    
    try:
        # ВИКОРИСТАННЯ СЕРВІСУ: делегуємо всю бізнес-логіку
        jwt_token = auth_service.exchange_token_for_jwt(sso_token)
        
        return AuthResponse(jwt=jwt_token)
        
    except HTTPException as e:
        # Це перехоплює HTTPException 401, кинутий AuthService (наприклад, "Token expired")
        raise e
    
    except Exception as e:
        # Обробка інших помилок
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during token exchange: {e}"
        )