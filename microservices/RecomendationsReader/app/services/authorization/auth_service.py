import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from neo4j.exceptions import ClientError
from jose import jwt
from fastapi import HTTPException 

# [ІМПОРТ NEO4J QUERY RUNNER]
# Припустіть правильний відносний або абсолютний імпорт до вашого QueryRunner
from app.services.neo4j.query_runner import QueryRunner 

log = logging.getLogger(__name__)

# --- КОНСТАНТИ БЕЗПЕКИ ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-very-secret-key-for-jwt-signing")
ALGORITHM = "HS256"
SSO_TOKEN_EXPIRY_SECONDS = 100 # One-Time Token діє 30 секунд
JWT_EXPIRY_HOURS = 2

class AuthService(QueryRunner):
    """
    Мікросервіс авторизації/користувачів. 
    Успадковує QueryRunner для прямого доступу до Neo4j.
    """

    def __init__(self) -> None:
        super().__init__()

    # --- 1. DAO (Data Access Object) Методи (Робота з Neo4j) ---

    def _neo4j_find_or_create_user(self, chrome_id: str) -> Dict[str, Any]:
        """
        Знаходить користувача за Chrome ID (у полі id) або створює нового.
        Використовує $chrome_id як єдиний ідентифікатор.
        """
        cypher = """
        MERGE (u:User {id: $chrome_id})    // Використовуємо 'id' для унікальності
        ON CREATE SET 
            u.createdAt = datetime(),
            u.roles = ['user']                
        ON MATCH SET 
            u.lastLogin = datetime()          // Оновлюємо дату останнього входу
        RETURN u.id AS id, u.roles AS roles
        """
        # Використовуємо self.run_one з QueryRunner
        user_data = self.run_one(cypher, {"chrome_id": chrome_id})
        
        if not user_data:
            log.error(f"Failed to find or create user for chrome ID: {chrome_id}")
            raise Exception("Failed to establish user identity.")
            
        return user_data

    def _neo4j_save_sso_token(self, user_id: str, token: str) -> None:
        """
        Створює вузол SSOToken у Neo4j, пов'язаний із користувачем за id.
        """
        future_dt = datetime.utcnow() + timedelta(seconds=SSO_TOKEN_EXPIRY_SECONDS)
        expires_at_str = future_dt.isoformat()        

        cypher = """
        MATCH (u:User {id: $user_id}) // Шукаємо по 'id'
        CREATE (u)-[:HAS_TOKEN]->(t:SSOToken {
            value: $token,
            expiresAt: datetime($expires_at),
            isUsed: false
        })
        """
        # Передаємо 'user_id' як параметр $user_id
        self.run_query(cypher, {
            "user_id": user_id, 
            "token": token, 
            "expires_at": expires_at_str
        })

    def _neo4j_atomic_exchange_token(self, token: str) -> Dict[str, Any]:
        """
        Атомарна операція: Валідуює токен, видаляє його з БД та повертає дані користувача.
        Ми більше не позначаємо токен як використаний — видаляємо вузол SSOToken.
        """
        cypher = """
        MATCH (u:User)-[:HAS_TOKEN]->(t:SSOToken {value: $token})
        WHERE t.expiresAt > datetime()
        WITH u, t
        DETACH DELETE t
        RETURN u.id AS id, u.roles AS roles
        """
        
        user_data = self.run_one(cypher, {"token": token})

        if not user_data:
            raise ValueError("Token not found or expired.")
            
        return user_data

    # --- 2. JWT Утиліти ---

    def create_jwt_token(self, user_id: str, roles: List[str]) -> str:
    # Використовуйте datetime.now(timezone.utc) замість utcnow()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=JWT_EXPIRY_HOURS) 
        
        to_encode = {
            "sub": user_id,
            "exp": expire.timestamp(),
            "iat": now.timestamp() # Використовуємо now з TZ
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    # --- 3. Основна Бізнес-Логіка SSO ---

    def generate_one_time_token(self, chrome_id: str) -> str:
        """ 
        Обробляє запит від Chrome Extension.
        """
        user_data = self._neo4j_find_or_create_user(chrome_id)
        # Використовуємо 'id', отриманий з повернення Cypher
        user_id = user_data["id"] 
        
        sso_token = str(uuid.uuid4())
        # Передаємо user_id (замість internal_user_id)
        self._neo4j_save_sso_token(user_id, sso_token) 
        
        return sso_token

    def exchange_token_for_jwt(self, sso_token: str) -> str:
        """
        Обробляє запит від Фронтенду.
        Обмінює One-Time Token на постійний JWT.
        """
        try:
            # 1. Атомарна перевірка та анулювання токена в Neo4j
            user_data = self._neo4j_atomic_exchange_token(sso_token)
            # Отримуємо 'id'
            user_id = user_data["id"] 
            user_roles = user_data.get("roles", ["user"])
            
            # 2. Генерувати JWT
            jwt_token = self.create_jwt_token(user_id, user_roles)
            
            return jwt_token
            
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"Authorization failed: {e}")
        except ClientError as e:
            log.error(f"Neo4j transaction failed during token exchange: {e}")
            raise HTTPException(status_code=500, detail="Internal database error")
        except Exception as e:
            log.error(f"Unexpected error during token exchange: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

# Створюємо єдиний екземпляр сервісу для використання в роутерах FastAPI
auth_service = AuthService()