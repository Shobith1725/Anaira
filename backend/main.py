import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from session import router as session_router
from voice_pipeline import router as voice_router
from dashboard_ws import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[ANAIRA] Starting in {'LOGISTICS' if settings.LOGISTICS_MODE else 'RECEPTIONIST'} mode")
    yield
    print("[ANAIRA] Shutting down")


app = FastAPI(
    title="ANAIRA Voice Agent",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(session_router)
app.include_router(voice_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "logistics" if settings.LOGISTICS_MODE else "receptionist",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)