"""
Application entrypoint.

Kept minimal on purpose:
- Middleware
- CORS configuration
- Router registration
- Health check

All business logic lives in services.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.audit_middleware import AuditLogMiddleware
from app.core.config import settings


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Enterprise deep learning platform for zero-day attack "
        "classification using open-set recognition and explainable AI."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------
# Audit logging middleware
# ---------------------------------------------------------

app.add_middleware(AuditLogMiddleware)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
#
# Frontend:
#     http://localhost:3000
#
# Backend:
#     http://localhost:8000
#
# The browser needs permission to make requests from
# localhost:3000 to localhost:8000.
# ---------------------------------------------------------

configured_origins = [
    str(origin).rstrip("/")
    for origin in settings.BACKEND_CORS_ORIGINS
]

# Make sure the local frontend is always allowed.
required_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

for origin in required_origins:
    if origin not in configured_origins:
        configured_origins.append(origin)


app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }