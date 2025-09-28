from fastapi import FastAPI
from app.routers import test, tab_info_collection

#  uvicorn app.main:app --reload

app = FastAPI()
app.include_router(test.router, prefix="/test", tags=["Neo4j test"])
app.include_router(tab_info_collection.router, prefix="/data", tags=["Tab Info Collection"])