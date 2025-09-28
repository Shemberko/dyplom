from fastapi import APIRouter
from app.db.neo4j import get_driver
from fastapi import Request
import pdb

router = APIRouter()
@router.post("/post-collected-data")
async def post_collected_data(request: Request):
    data = await request.json()
    user = data.get("user", {}).get("info", {})
    pdb.set_trace()
    print(user)
    driver = get_driver()
    with driver.session(database="neo4j") as session:
        result = session.run("MATCH (n:Label) RETURN n")
        labels = [record["n"] for record in result]
        return {"labels": labels, "received_data": data}
