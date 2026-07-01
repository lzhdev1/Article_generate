# backend/app/api/endpoints/project.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.project import Project

router = APIRouter()


class TopicInput(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, description="文章主题")


class ProjectResponse(BaseModel):
    project_id: str
    topic: str
    status: str
    created_at: str


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(input: TopicInput, db: AsyncSession = Depends(get_db)):
    """创建新项目"""
    project = Project(topic=input.topic, status="init")
    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        project_id=str(project.id),
        topic=project.topic,
        status=project.status,
        created_at=project.created_at.isoformat(),
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        project_id=str(project.id),
        topic=project.topic,
        status=project.status,
        created_at=project.created_at.isoformat(),
    )
