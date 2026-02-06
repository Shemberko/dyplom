from pydantic import BaseModel

class SsoRequest(BaseModel):
    userId: str

class TokenExchangeRequest(BaseModel):
    token: str

class AuthResponse(BaseModel):
    jwt: str
