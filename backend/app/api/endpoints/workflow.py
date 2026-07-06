# backend/app/api/endpoints/workflow.py

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.workflow_service import workflow_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class SelectTitleRequest(BaseModel):
    title: str


class GenerateOutlinesRequest(BaseModel):
    outline_config: Optional[dict] = None


class SelectOutlineRequest(BaseModel):
    outline: dict


class GenerateArticleRequest(BaseModel):
    article_config: Optional[dict] = None


@router.post("/projects/{project_id}/workflow/start")
async def start_workflow(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    启动工作流：搜索→过滤→知识提取→生成标题
    返回5个候选标题
    """
    try:
        result = await workflow_service.start(db, project_id)
        return {"project_id": project_id, **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/workflow/start-stream")
async def start_workflow_stream(project_id: str):
    """
    启动工作流（SSE 流式返回进度）
    事件类型：
    - progress: 每个节点完成时发送 {stage, message}
    - completed: 工作流完成时发送完整状态
    - error: 出错时发送 {message}
    """
    async def event_generator():
        try:
            async for event in workflow_service.start_with_progress(project_id):
                event_type = event.get("event", "message")
                data = json.dumps(event.get("data", {}), ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_data = json.dumps({"message": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.post("/projects/{project_id}/workflow/select-title")
async def select_title(
    project_id: str,
    request: SelectTitleRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户选择标题，继续到大纲生成"""
    try:
        result = await workflow_service.resume_with_title(db, project_id, request.title)
        return {"project_id": project_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/workflow/save-outline-config")
async def save_outline_config(
    project_id: str,
    request: GenerateOutlinesRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存大纲配置并生成大纲"""
    try:
        if not request.outline_config:
            raise HTTPException(status_code=400, detail="outline_config is required")
        result = await workflow_service.resume_with_outline_config(
            db, project_id, request.outline_config
        )
        return {"project_id": project_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/workflow/select-outline")
async def select_outline(
    project_id: str,
    request: SelectOutlineRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户选择大纲，继续到文章生成"""
    try:
        result = await workflow_service.resume_with_outline(db, project_id, request.outline)
        return {"project_id": project_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/workflow/save-article-config")
async def save_article_config(
    project_id: str,
    request: GenerateArticleRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存文章配置并开始生成文章"""
    try:
        if request.article_config:
            result = await workflow_service.resume_with_article_config(
                db, project_id, request.article_config
            )
            return {"project_id": project_id, **result}
        raise HTTPException(status_code=400, detail="article_config is required")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/workflow/state")
async def get_workflow_state(project_id: str):
    """获取工作流当前状态"""
    state = await workflow_service.get_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "project_id": project_id,
        "current_stage": state.get("current_stage", "unknown"),
        "data": {
            "topic": state.get("topic"),
            "titles": state.get("generated_titles", []),
            "selected_title": state.get("selected_title"),
            "outlines": state.get("generated_outlines", []),
            "selected_outline": state.get("selected_outline"),
            "article": state.get("full_article"),
            "summary": state.get("article_summary"),
            "faq": state.get("article_faq", []),
            "verification_passed": state.get("verification_passed"),
            "current_stage": state.get("current_stage"),
            "error": state.get("error"),
        },
    }
