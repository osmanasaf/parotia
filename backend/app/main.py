from fastapi import FastAPI
from app.routers import health, movies, tv, auth

app = FastAPI()

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(tv.router)
app.include_router(auth.router) 