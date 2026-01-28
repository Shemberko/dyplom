from typing import Optional
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

# Імпорт констант та сервісу
from app.services.authorization.auth_service import SECRET_KEY, ALGORITHM 

# Схема для валідації токена у заголовку
async def get_current_user_id(
    # FastAPI автоматично шукає заголовок Authorization: Bearer <token>
    authorization: Optional[str] = Header(None) 
) -> str:
    """
    Валідує JWT, отримує ID користувача та повертає його.
    Викликає 401, якщо токен недійсний або відсутній.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing or malformed"
        )

    # Витягуємо сам JWT (після "Bearer ")
    token = authorization.split(" ")[1] 
    
    try:
        # 1. Декодування JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Перевірка терміну дії (це робить jwt.decode автоматично, але перевірка не завадить)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token payload missing user ID")
        
        # 3. Додаткова перевірка в БД (за потреби):
        #    Наприклад, перевірка існування користувача в Neo4j
        # user_exists = auth_service.check_user_exists(user_id)
        # if not user_exists:
        #     raise HTTPException(status_code=401, detail="User not found in DB")
        
    except JWTError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired authentication token"
        )
        
    return user_id

# Ви можете створити об'єкт Depends для повторного використання
# наприклад, для перевірки ролей:
# async def get_admin_user(user_id: str = Depends(get_current_user_id)):
#     roles = ... (отримати ролі з Neo4j)
#     if 'admin' not in roles:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     return user_id