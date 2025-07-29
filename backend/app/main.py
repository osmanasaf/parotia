from fastapi import FastAPI
from app.routers import health, movies, tv

app = FastAPI()

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(tv.router) 