from typing import Any, Dict, List, Optional

from neo4j.exceptions import ClientError
from jose import jwt
from fastapi import HTTPException 

from app.services.neo4j.query_runner import QueryRunner 


class ProfileService(QueryRunner):

    def __init__(self) -> None:
        super().__init__()

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Отримує профіль користувача за його ID.
        """
        cypher = """
        MATCH (u:User {id: $user_id}) 
        RETURN u.id AS id, 
                u.email AS email, 
                u.roles AS roles, 
                u.createdAt AS createdAt
        """
        
        profile_data = self.run_one(cypher, {"user_id": user_id})
        
        if not profile_data:
            raise ValueError(f"User with ID {user_id} not found in database.")
            
        profile_data['email'] = profile_data.get('email')
        profile_data['id'] = profile_data.get('id')

        return profile_data
    
profile_service = ProfileService()