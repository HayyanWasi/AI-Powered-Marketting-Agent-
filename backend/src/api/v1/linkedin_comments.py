from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any
import logging
from src.api.dependencies import require_user
from src.modules.linkedin.worker.reply_service import ReplyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/comments", tags=["LinkedIn Comments"])

@router.post("/{comment_id}/reply")
async def reply_to_comment(
    comment_id: str,
    text: str = Body(..., embed=True),
    user_id: str = Depends(require_user)
) -> dict[str, Any]:
    """Manually reply to an inbound LinkedIn comment."""
    service = ReplyService()
    try:
        result = await service.send_manual_reply(user_id, comment_id, text)
        return result
    except Exception as e:
        logger.exception(f"Failed to send manual reply to comment {comment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

