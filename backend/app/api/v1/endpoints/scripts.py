"""Scripts endpoints — view and edit generated scripts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.script import Script
from app.schemas import ScriptResponse, ScriptUpdate

router = APIRouter()


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get a script by ID."""
    script = await db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return ScriptResponse.model_validate(script)


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int, data: ScriptUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    """Update a script (for manual editing before publish)."""
    script = await db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if data.title is not None:
        script.title = data.title
    if data.content is not None:
        script.content = data.content
        script.word_count = len(data.content.split())
        script.duration_estimate = script.word_count / 150.0
    if data.status is not None:
        script.status = data.status

    await db.commit()
    await db.refresh(script)
    return ScriptResponse.model_validate(script)
