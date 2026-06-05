from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.modules.auth.auth_controller import router as auth_router
from app.modules.resume.resume_controller import router as resume_router
from app.modules.jobs.job_controller import router as jobs_router
from app.modules.feed.feed_controller import router as feed_router
from app.modules.upload.upload_controller import router as upload_router
from app.modules.profile.profile_controller import router as profile_router
from app.modules.admin.admin_controller import router as admin_router
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=False,
    lifespan=lifespan,
)


# Catch-all exception handler to ensure CORS headers are present even on 500s
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(feed_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    from app.services.redis_service import RedisService
    redis_ok = False
    try:
        redis_ok = RedisService().ping()
    except Exception:
        pass
    return {
        "status": "ok",
        "version": settings.app_version,
        "redis": "connected" if redis_ok else "disconnected",
    }

import os
settings = get_settings()
@app.get("/api/v1/hello")
async def hello():
    return {"resend_api": os.getenv("RESEND_API_KEY"),
            "resend_email": os.getenv("RESEND_FROM_EMAIL"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL"),    }
