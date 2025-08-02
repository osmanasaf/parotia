from fastapi import FastAPI
from app.routers import health, movies, tv, recommendations, auth, emotion_analysis

app = FastAPI(
    title="Parotia API",
    description="Film/Dizi Bilgi ve Duygu Tabanlı Öneri Sistemi",
    version="1.0.0"
)

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(tv.router)
app.include_router(recommendations.router)
app.include_router(auth.router)
app.include_router(emotion_analysis.router) 