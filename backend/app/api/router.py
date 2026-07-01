# backend/app/api/router.py

from fastapi import APIRouter

from app.api.endpoints import project, workflow

api_router = APIRouter()

api_router.include_router(project.router, tags=["project"])
api_router.include_router(workflow.router, tags=["workflow"])
