"""Tests for Workflow Engine models."""

from datetime import datetime

from src.modules.workflow_engine.models import (
    WorkflowContext,
    WorkflowGraph,
    WorkflowNode,
    RetryPolicy,
    ExecutionCheckpoint,
    ApprovalRequest,
    ApprovalStatus,
    ExecutionState,
    ExecutionError,
    WorkflowResult,
    WorkflowStatus,
    CircleDependencyError,
    MissingEntryNodeError,
)


class TestWorkflowContext:
    def test_create_context(self) -> None:
        ctx = WorkflowContext.create(
            workflow_id="wf-1",
            thread_id="th-1",
        )
        assert ctx.workflow_id == "wf-1"
        assert ctx.thread_id == "th-1"
        assert ctx.state == ExecutionState.PENDING
        assert ctx.node_outputs == {}

    def test_context_with_updates(self) -> None:
        ctx = WorkflowContext.create(workflow_id="wf-1", thread_id="th-1")
        updated = ctx.with_updates(state=ExecutionState.RUNNING, current_node="node_a")
        assert updated.state == ExecutionState.RUNNING
        assert updated.current_node == "node_a"
        assert ctx.state == ExecutionState.PENDING  # original unchanged

    def test_context_merge_outputs(self) -> None:
        ctx = WorkflowContext.create(
            workflow_id="wf-1",
            thread_id="th-1",
            node_outputs={"a": 1},
        )
        updated = ctx.with_updates(node_outputs={"b": 2})
        assert updated.node_outputs == {"a": 1, "b": 2}


class TestWorkflowGraph:
    def test_create_graph(self) -> None:
        node_a = WorkflowNode(
            name="a",
            description="Node A",
            handler=lambda x: x,
            retry_policy={"max_retries": 0},
            timeout_seconds=None,
            requires_approval=False,
        )
        node_b = WorkflowNode(
            name="b",
            description="Node B",
            handler=lambda x: x,
            retry_policy={"max_retries": 0},
            timeout_seconds=None,
            requires_approval=False,
        )
        graph = WorkflowGraph(
            graph_id="g1",
            nodes={"a": node_a, "b": node_b},
            entry_point="a",
            edges=[{"source": "a", "target": "b"}],
            conditional_edges=[],
            terminal_nodes=["b"],
        )
        assert graph.graph_id == "g1"
        assert graph.entry_point == "a"

    def test_missing_entry_node_raises(self) -> None:
        try:
            WorkflowGraph(
                graph_id="g1",
                nodes={
                    "a": WorkflowNode(
                        name="a",
                        description="A",
                        handler=lambda x: x,
                        retry_policy={},
                        timeout_seconds=None,
                        requires_approval=False,
                    )
                },
                entry_point="missing",
                edges=[],
                conditional_edges=[],
                terminal_nodes=[],
            )
            assert False, "Should have raised MissingEntryNodeError"
        except MissingEntryNodeError:
            pass


class TestWorkflowNode:
    def test_create_node(self) -> None:
        node = WorkflowNode(
            name="test",
            description="Test node",
            handler=lambda x: x,
            retry_policy={"max_retries": 3, "delay_seconds": 1.0},
            timeout_seconds=30.0,
            requires_approval=False,
        )
        assert node.name == "test"
        assert node.retry_policy["max_retries"] == 3

    def test_empty_name_raises(self) -> None:
        try:
            WorkflowNode(
                name="",
                description="A",
                handler=lambda x: x,
                retry_policy={},
                timeout_seconds=None,
                requires_approval=False,
            )
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestRetryPolicy:
    def test_create_policy(self) -> None:
        policy = RetryPolicy(max_retries=3, delay_seconds=1.0)
        assert policy.max_retries == 3
        assert policy.delay_seconds == 1.0

    def test_calculate_delay(self) -> None:
        policy = RetryPolicy(max_retries=3, delay_seconds=1.0, backoff_multiplier=2.0)
        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0

    def test_max_delay_cap(self) -> None:
        policy = RetryPolicy(
            max_retries=5,
            delay_seconds=1.0,
            backoff_multiplier=2.0,
            max_delay_seconds=5.0,
        )
        assert policy.calculate_delay(3) == 5.0  # capped


class TestApprovalRequest:
    def test_create_approval(self) -> None:
        req = ApprovalRequest(
            thread_id="th-1",
            node_name="approval_node",
            request_data={"content": "Please review"},
            status=ApprovalStatus.PENDING,
            rejection_reason=None,
            created_at=datetime.now(),
            resolved_at=None,
        )
        assert req.status == ApprovalStatus.PENDING

    def test_approve(self) -> None:
        req = ApprovalRequest(
            thread_id="th-1",
            node_name="n",
            request_data={"x": 1},
            status=ApprovalStatus.PENDING,
            rejection_reason=None,
            created_at=datetime.now(),
            resolved_at=None,
        )
        req.approve()
        assert req.status == ApprovalStatus.APPROVED
        assert req.resolved_at is not None

    def test_reject(self) -> None:
        req = ApprovalRequest(
            thread_id="th-1",
            node_name="n",
            request_data={"x": 1},
            status=ApprovalStatus.PENDING,
            rejection_reason=None,
            created_at=datetime.now(),
            resolved_at=None,
        )
        req.reject("Not ready")
        assert req.status == ApprovalStatus.REJECTED
        assert req.rejection_reason == "Not ready"


class TestWorkflowResult:
    def test_create_result(self) -> None:
        ctx = WorkflowContext.create(workflow_id="wf-1", thread_id="th-1")
        result = WorkflowResult(
            final_context=ctx,
            thread_id="th-1",
            execution_time_ms=150.0,
            node_count=3,
            completed_nodes=3,
            status=ExecutionState.COMPLETED,
        )
        assert result.status == ExecutionState.COMPLETED
        assert result.completed_nodes == result.node_count


class TestWorkflowStatus:
    def test_create_status(self) -> None:
        status = WorkflowStatus(
            thread_id="th-1",
            state=ExecutionState.RUNNING,
            current_node="b",
            completed_nodes=["a"],
            pending_nodes=["c"],
            failed_nodes=[],
            errors=[],
            checkpoint_id="cp-1",
        )
        assert status.current_node == "b"
        assert "a" in status.completed_nodes
