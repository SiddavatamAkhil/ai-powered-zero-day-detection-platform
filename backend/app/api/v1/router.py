"""
Aggregates all v1 routers. Future modules (datasets, training, models,
explainability, reports) each add one line here — main.py never changes.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, datasets, explainability, reports, simulation, system, training, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(training.router)
api_router.include_router(explainability.router)
api_router.include_router(simulation.router)
api_router.include_router(reports.router)
api_router.include_router(system.router)
api_router.include_router(users.router)
# api_router.include_router(models.router)
# api_router.include_router(explainability.router)
# api_router.include_router(reports.router)
