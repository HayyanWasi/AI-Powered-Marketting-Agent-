"""Tests for Workflow Engine services."""

from src.modules.workflow_engine.models import (
    ApprovalStatus,
    ExecutionState,
    RetryPolicy,
    WorkflowContext,
)
from src.modules.workflow_engine.services.approval_service import ApprovalService
from src.modules.workflow_engine.services.resume_service import ResumeService
from src.modules.workflow_engine.services.retry_service import RetryService
from src.modules.workflow_engine.services.state_manager import StateManager


class TestRetryService:
    def test_retry_service(self) -> None:
        svc = RetryService()
        policy = RetryPolicy(max_retries=3, delay_seconds=0.01)

        assert svc.can_retry("node1", policy) is True
        svc.record_attempt("node1")
        svc.record_attempt("node1")
        assert svc.get_attempt_count("node1") == 2
        assert svc.can_retry("node1", policy) is True

        svc.record_attempt("node1")
        assert svc.can_retry("node1", policy) is False

    def test_retry_delay_calculation(self) -> None:
        svc = RetryService()
        policy = RetryPolicy(max_retries=3, delay_seconds=1.0, backoff_multiplier=2.0)

        svc.record_attempt("n")
        delay = svc.calculate_delay("n", policy)
        assert delay == 2.0  # 1.0 * 2^1

    def test_reset_attempts(self) -> None:
        svc = RetryService()
        svc.record_attempt("n")
        svc.reset_attempts("n")
        assert svc.get_attempt_count("n") == 0


class TestResumeService:
    def test_save_and_resume(self) -> None:
        svc = ResumeService()
        ctx = WorkflowContext.create(
            workflow_id="wf-1",
            thread_id="th-1",
            current_node="node_c",
        )

        svc.save_checkpoint("th-1", ctx)
        assert svc.has_checkpoint("th-1") is True

        resumed = svc.resume("th-1")
        assert resumed.state == ExecutionState.RUNNING
        assert resumed.current_node == "node_c"

    def test_resume_without_checkpoint_raises(self) -> None:
        svc = ResumeService()
        try:
            svc.resume("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_clear_checkpoint(self) -> None:
        svc = ResumeService()
        ctx = WorkflowContext.create(workflow_id="wf-1", thread_id="th-1")
        svc.save_checkpoint("th-1", ctx)
        svc.clear_checkpoint("th-1")
        assert svc.has_checkpoint("th-1") is False


class TestApprovalService:
    def test_request_and_approve(self) -> None:
        svc = ApprovalService()
        req = svc.request_approval("th-1", "approve_node", {"data": "review"})
        assert req.status == ApprovalStatus.PENDING
        assert svc.has_pending("th-1") is True

        approved = svc.approve("th-1")
        assert approved.status == ApprovalStatus.APPROVED
        assert svc.has_pending("th-1") is False

    def test_request_and_reject(self) -> None:
        svc = ApprovalService()
        svc.request_approval("th-1", "node", {"data": "x"})

        rejected = svc.reject("th-1", "Not good")
        assert rejected.status == ApprovalStatus.REJECTED
        assert rejected.rejection_reason == "Not good"

    def test_approve_without_pending_raises(self) -> None:
        svc = ApprovalService()
        try:
            svc.approve("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestStateManager:
    def test_initialize(self) -> None:
        svc = StateManager()
        ctx = WorkflowContext.create(workflow_id="wf-1", thread_id="th-1")
        result = svc.initialize("th-1", ctx)
        assert result.state == ExecutionState.RUNNING

    def test_mark_node_completed(self) -> None:
        svc = StateManager()
        svc.mark_node_completed("th-1", "node_a", {"output": 1})

        assert svc.is_node_completed("th-1", "node_a") is True
        assert svc.get_node_output("th-1", "node_a") == {"output": 1}
        assert "node_a" in svc.get_completed_nodes("th-1")

    def test_get_all_outputs(self) -> None:
        svc = StateManager()
        svc.mark_node_completed("th-1", "a", 1)
        svc.mark_node_completed("th-1", "b", 2)

        outputs = svc.get_all_outputs("th-1")
        assert outputs == {"a": 1, "b": 2}

    def test_restore_checkpoint(self) -> None:
        svc = StateManager()
        svc.mark_node_completed("th-1", "a", 1)

        ctx = WorkflowContext.create(workflow_id="wf-1", thread_id="th-1")
        restored = svc.restore_checkpoint("th-1", ctx)
        assert restored.state == ExecutionState.RUNNING
        assert svc.is_node_completed("th-1", "a") is True
