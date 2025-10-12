from fastapi import APIRouter
import json
from typing import Any, Dict

router = APIRouter()

@router.post("/save_data")
def save_data(data:  Dict[str, Any]):
    print(f"Data saved successfully. {data}")
    return {"data": data}
