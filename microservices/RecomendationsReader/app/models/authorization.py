# models.py
from pydantic import BaseModel

# Модель для запиту від Chrome Extension
class SsoRequest(BaseModel):
    userId: str # chromeUserId (унікальний ID від chrome.identity.getProfileUserInfo)

# Модель для запиту від Фронтенду
class TokenExchangeRequest(BaseModel):
    token: str # One-Time Token

# Модель відповіді для JWT
class AuthResponse(BaseModel):
    jwt: str
