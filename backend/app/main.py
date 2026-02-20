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

    def job_cache_popular_and_similar():
        """Pre-warm cache for popular movies and tv shows"""
        db = SessionLocal()
        from app.services.movie_service import MovieService
        from app.services.tv_service import TVService
        from app.services.recommendation_service import RecommendationService
        from app.core.cache import CacheService
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info("Starting daily cache pre-warming for popular content recommendations")
        
        try:
            movie_service = MovieService(db)
            tv_service = TVService(db)
            rec_service = RecommendationService(db)
            cache_service = CacheService()
            
            # Pre-warm movies
            popular_movies = movie_service.get_popular_movies(page=1)
            if popular_movies.get("success"):
                for movie in popular_movies.get("data", {}).get("results", [])[:20]: # Top 20
                    tmdb_id = movie["id"]
                    cache_key = f"tmdb:movie:{tmdb_id}:details_similar_public"
                    
                    try:
                        detail_result = movie_service.get_movie_details(tmdb_id)
                        if detail_result.get("success"):
                            detail = detail_result["data"]
                            overview_text = detail.get("overview", "")
                            
                            similar = rec_service.get_emotion_based_recommendations_public(
                                overview_text, content_type="movie", exclude_tmdb_ids={tmdb_id}
                            )
                            
                            response_data = {
                                "success": True,
                                "data": {
                                    "detail": detail,
                                    "similar": similar.get("data", {}).get("recommendations", [])
                                }
                            }
                            cache_service.set_json(cache_key, response_data, 86400)
                    except Exception as e:
                        logger.error(f"Failed to cache movie {tmdb_id}: {str(e)}")
            
            # Pre-warm TV shows
            popular_tv = tv_service.get_popular_tv_shows(page=1)
            if popular_tv.get("success"):
                for tv_show in popular_tv.get("data", {}).get("results", [])[:20]: # Top 20
                    tmdb_id = tv_show["id"]
                    cache_key = f"tmdb:tv:{tmdb_id}:details_similar_public"
                    
                    try:
                        detail_result = tv_service.get_tv_show_details(tmdb_id)
                        if detail_result.get("success"):
                            detail = detail_result["data"]
                            overview_text = detail.get("overview", "")
                            
                            similar = rec_service.get_emotion_based_recommendations_public(
                                overview_text, content_type="tv", exclude_tmdb_ids={tmdb_id}
                            )
                            
                            response_data = {
                                "success": True,
                                "data": {
                                    "detail": detail,
                                    "similar": similar.get("data", {}).get("recommendations", [])
                                }
                            }
                            cache_service.set_json(cache_key, response_data, 86400)
                    except Exception as e:
                        logger.error(f"Failed to cache TV {tmdb_id}: {str(e)}")
                        
            logger.info("Daily cache pre-warming completed")
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
    
    scheduler.add_job(
        job_cache_popular_and_similar,
        trigger="cron",
        hour=settings.SCHEDULE_HOUR,
        minute=(settings.SCHEDULE_MINUTE + 5) % 60, # Run 5 minutes after populate
        id="daily_cache_popular_and_similar",
        replace_existing=True,
    )
    
    scheduler.start()


@app.on_event("startup")
async def init_db():
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        Base.metadata.create_all(bind=engine)
        
    # Trigger cache pre-warming on startup if scheduler is enabled
    if settings.ENABLE_SCHEDULER and APSCHEDULER_AVAILABLE:
        import threading
        job = scheduler.get_job("daily_cache_popular_and_similar")
        if job:
            threading.Thread(target=job.func, daemon=True).start()