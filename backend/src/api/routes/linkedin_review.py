"""API endpoints for managing the LinkedIn Review Queue.

Allows the frontend to fetch pending comments, approve them, or reject them.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import get_authenticated_user
from src.modules.linkedin.models import GeneratedComment
from src.modules.linkedin.worker.review_queue import ReviewQueue

router = APIRouter(prefix="/linkedin/review", tags=["LinkedIn Review Queue"])


class RejectRequest(BaseModel):
    reason: str


@router.get("/pending", response_model=list[GeneratedComment])
async def get_pending_comments(
    limit: int = 50,
    user: dict = Depends(get_authenticated_user),
) -> list[GeneratedComment]:
    """Get all comments currently awaiting human review."""
    queue = ReviewQueue()
    return queue.get_pending(limit=limit)


@router.post("/{comment_id}/approve", status_code=status.HTTP_200_OK)
async def approve_comment(
    comment_id: UUID,
    user: dict = Depends(get_authenticated_user),
) -> dict[str, str]:
    """Approve a comment, making it ready for publishing."""
    queue = ReviewQueue()
    success = queue.approve(comment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment {comment_id} not found or could not be approved.",
        )
    return {"status": "approved", "comment_id": str(comment_id)}


@router.post("/{comment_id}/reject", status_code=status.HTTP_200_OK)
async def reject_comment(
    comment_id: UUID,
    request: RejectRequest,
    user: dict = Depends(get_authenticated_user),
) -> dict[str, str]:
    """Reject a comment so it will not be published."""
    queue = ReviewQueue()
    success = queue.reject(comment_id, request.reason)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment {comment_id} not found or could not be rejected.",
        )
    return {"status": "rejected", "comment_id": str(comment_id)}
