from typing import Optional
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

from app.services.authorization.auth_service import SECRET_KEY, ALGORITHM 

async def get_current_user_id(
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

    token = authorization.split(" ")[1] 
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token payload missing user ID")
    except JWTError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired authentication token"
        )
        
    return user_id