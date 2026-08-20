"""Approval Service — manages human approval suspension and resume."""

import logging
from datetime import datetime

from ..models import ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


class ApprovalService:
    """Manages human approval requests for workflow suspension."""

    def __init__(self):
        self._pending: dict[str, ApprovalRequest] = {}

    def request_approval(
        self,
        thread_id: str,
        node_name: str,
        request_data: dict,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            thread_id=thread_id,
            node_name=node_name,
            request_data=request_data,
            status=ApprovalStatus.PENDING,
            rejection_reason=None,
            created_at=datetime.now(),
            resolved_at=None,
        )
        self._pending[thread_id] = request
        logger.info("Approval requested for thread %s at node %s", thread_id, node_name)
        return request

    def approve(self, thread_id: str) -> ApprovalRequest:
        request = self._pending.get(thread_id)
        if not request:
            raise ValueError(f"No pending approval for thread {thread_id}")
        request.approve()
        del self._pending[thread_id]
        logger.info("Approval granted for thread %s", thread_id)
        return request

    def reject(self, thread_id: str, reason: str) -> ApprovalRequest:
        request = self._pending.get(thread_id)
        if not request:
            raise ValueError(f"No pending approval for thread {thread_id}")
        request.reject(reason)
        del self._pending[thread_id]
        logger.info("Approval rejected for thread %s: %s", thread_id, reason)
        return request

    def has_pending(self, thread_id: str) -> bool:
        return thread_id in self._pending

    def get_pending(self, thread_id: str) -> ApprovalRequest | None:
        return self._pending.get(thread_id)
