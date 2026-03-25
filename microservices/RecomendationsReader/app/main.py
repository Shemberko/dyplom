from fastapi import FastAPI
from app.routers import recommendations, authorization, profile, text_recommendations, statistic, unified_recommendations, stats, history
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendations.router, prefix="/text_recommendations", tags=["recommendations"])
app.include_router(text_recommendations.router, prefix="/content_recomendations", tags=["recommendations"])
app.include_router(authorization.router, prefix="/sso", tags=["authorization"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(statistic.router, prefix="/statistic", tags=["statistic"])
app.include_router(unified_recommendations.router, prefix="/recommendations", tags=["statistic"])
app.include_router(stats.router, prefix="/stats", tags=["statistic"])
app.include_router(history.router, prefix="/history", tags=["statistic"])

