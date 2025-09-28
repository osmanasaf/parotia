from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, movies, tv, recommendations, auth, emotion_analysis, content
from app.core.config import get_settings
from app.db import SessionLocal
from app.services.recommendation_service import RecommendationService
from app.db import Base, engine
from app import models  # ensure models are imported
import os

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except Exception:
    APSCHEDULER_AVAILABLE = False

app = FastAPI(
    title="Parotia API",
    description="Film/Dizi Bilgi ve Duygu Tabanlı Öneri Sistemi",
    version="1.0.0"
)

# CORS middleware yapılandırması
settings = get_settings()
origins_env = settings.CORS_ALLOW_ORIGINS or ""
origins = [o.strip() for o in origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(content.router)  # Yeni birleşik content router
app.include_router(movies.router)
app.include_router(tv.router)
app.include_router(recommendations.router)
app.include_router(auth.router)
app.include_router(emotion_analysis.router) 

if settings.ENABLE_SCHEDULER and APSCHEDULER_AVAILABLE:
    scheduler = BackgroundScheduler(timezone="UTC")

    def job_populate_continue():
        db = SessionLocal()
        try:
            service = RecommendationService(db)
            service.continue_bulk_popular(
                content_type="movie",
                batch_pages=settings.SCHEDULE_MOVIE_BATCH_PAGES,
                use_details=False,
            )
            service.continue_bulk_popular(
                content_type="tv",
                batch_pages=settings.SCHEDULE_TV_BATCH_PAGES,
                use_details=False,
            )
        finally:
            db.close()

    
    scheduler.add_job(
        job_populate_continue,
        trigger="cron",
        hour=settings.SCHEDULE_HOUR,
        minute=settings.SCHEDULE_MINUTE,
        id="daily_populate_continue",
        replace_existing=True,
    )
    scheduler.start()


@app.on_event("startup")
async def init_db():
    # İlk deploy için otomatik tablo oluşturma (idempotent)
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        Base.metadata.create_all(bind=engine)