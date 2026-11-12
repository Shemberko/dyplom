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
            return {"id": user_id, "email": "Користувач", "roles": [], "createdAt": None}
            
        profile_data['email'] = profile_data.get('email', 'Користувач')
        profile_data['id'] = profile_data.get('id', user_id)

        # Fix Pydantic serialization error for Neo4j DateTime
        if 'createdAt' in profile_data and profile_data['createdAt']:
            if hasattr(profile_data['createdAt'], 'iso_format'):
                profile_data['createdAt'] = profile_data['createdAt'].iso_format()
            elif hasattr(profile_data['createdAt'], 'isoformat'):
                profile_data['createdAt'] = profile_data['createdAt'].isoformat()
            else:
                profile_data['createdAt'] = str(profile_data['createdAt'])

        return profile_data
    
profile_service = ProfileService()