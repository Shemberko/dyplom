from fastapi import APIRouter
from app.db.neo4j import get_driver

router = APIRouter()

@router.get("/test-neo4j")
def get_all_labels():
    driver = get_driver()
    with driver.session(database="neo4j") as session:
        result = session.run("MATCH (n:Label) RETURN n")
        labels = [record["n"] for record in result]
        return {"labels": labels}
