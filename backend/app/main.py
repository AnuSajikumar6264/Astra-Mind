from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .services.engine import ensure_seed
from .routers.api import router
@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db();ensure_seed();yield
app=FastAPI(title="ASTRA-MIND API",version="0.1.0",description="Offline-friendly astronaut health research prototype.",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api/v1")
@app.get("/")
def root():return {"name":"ASTRA-MIND","docs":"/docs","api":"/api/v1"}
