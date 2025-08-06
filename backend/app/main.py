from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, movies, tv, recommendations, auth, emotion_analysis, content

app = FastAPI(
    title="Parotia API",
    description="Film/Dizi Bilgi ve Duygu Tabanlı Öneri Sistemi",
    version="1.0.0"
)

# CORS middleware yapılandırması
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React/Next.js development server
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Alternatif port
        "http://127.0.0.1:3001",
    ],
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