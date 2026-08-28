"""
Application entrypoint.

Kept minimal on purpose:
- Middleware
- CORS configuration
- Router registration
- Health check

All business logic lives in services.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # Ensures all ORM models register in Base.metadata
from app.api.v1.router import api_router
from app.core.audit_middleware import AuditLogMiddleware
from app.core.config import settings
from app.db.session import Base, engine


# ---------------------------------------------------------
# Lifespan — Automatic table initialization on startup
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Startup DB init notice (tables may already exist or DB offline): {e}")

    await _seed_admin()
    yield


async def _seed_admin():
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            email = settings.ADMIN_EMAIL.strip().lower()
            existing = (await session.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()
            if not existing:
                session.add(User(
                    email=email,
                    full_name=settings.ADMIN_NAME,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    is_active=True,
                ))
                await session.commit()
                print(f"Admin user seeded: {email}")
            else:
                print(f"Admin user already exists: {email}")
    except Exception as e:
        print(f"Admin seed notice: {e}")


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
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Global Exception Handler — Ensures 500s return JSON
# ---------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled Exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )


# ---------------------------------------------------------
# Audit logging middleware
# ---------------------------------------------------------

app.add_middleware(AuditLogMiddleware)


# ---------------------------------------------------------
# CORS Configuration (Must wrap outer request pipeline)
# ---------------------------------------------------------

# Normalize configured origins from environment
configured_origins = [
    str(origin).rstrip("/").lower()
    for origin in settings.BACKEND_CORS_ORIGINS
]

# Required origins for local development and production
required_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://zeroday-platform-frontend.onrender.com",
]

# Normalize required origins to lowercase for safe comparison
required_origins_lower = [o.lower() for o in required_origins]

# Add any missing required origins
for origin in required_origins_lower:
    if origin not in configured_origins:
        configured_origins.append(origin)

allow_all = "*" in configured_origins

# Debug logging for CORS configuration
print(f"\n=== CORS Configuration Debug ===")
print(f"Environment BACKEND_CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
print(f"Configured Origins (normalized): {configured_origins}")
print(f"Allow All Origins: {allow_all}")
print(f"================================\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else configured_origins,
    allow_origin_regex=r"https://.*\.onrender\.com" if not allow_all else None,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# ---------------------------------------------------------
# System Routes
# ---------------------------------------------------------

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "AI-Powered Zero-Day Detection Platform API is running"
    }


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }
