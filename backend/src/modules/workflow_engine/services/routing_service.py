"""Routing Service - Determines execution flow between nodes."""
from typing import Dict, Any, List, Callable
from datetime import datetime

from .models.workflow_context import WorkflowContext
from .models.approval_request import ApprovalRequest, ApprovalStatus


class RoutingService:
    """Service that determines the next node to execute based on routing rules.

    The RoutingService evaluates workflow graph edges and conditional routing
    rules to determine the correct execution path through the workflow. It
    handles both sequential and conditional routing.

    The routing decisions are based on:
    - Direct edges between nodes
    - Conditional edges with evaluation functions
    - Node properties (e.g., approval requirements)
    """

    def __init__(self):
        self._conditional_rules: Dict[str, Callable] = {}
        self._edge_mappings: Dict[str, str] = {}

    def add_conditional_rule(
        self, source_node: str, condition_func: Callable[[WorkflowContext], str]
    ) -> None:
        """Add a conditional routing rule.

        Args:
            source_node: Source node name
            condition_func: Function that evaluates condition and returns target node
        """
        self._conditional_rules[source_node] = condition_func

    def add_edge_mapping(self, source_node: str, target_node: str) -> None:
        """Add a direct edge mapping.

        Args:
            source_node: Source node name
            target_node: Target node name
        """
        self._edge_mappings[f"{source_node}->{target_node}"] = target_node

    def get_next_node(
        self,
        current_node: str,
        workflow_context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Determine the next node to execute.

        Evaluates both direct edges and conditional routing rules to determine
        the next execution step.

        Args:
            current_node: Current node name
            workflow_context: Current workflow context

        Returns:
            Dict containing:
            - next_node: Name of next node to execute
            - routing_type: Type of routing (direct or conditional)
            - condition_result: Result of condition evaluation (if conditional)
            - action: Action to take (continue or pause)
        """
        # Check conditional rules first (higher priority)
        if current_node in self._conditional_rules:
            return self._evaluate_conditional_rule(
                current_node, workflow_context
            )

        # Fall back to direct edge lookup
        return self._evaluate_direct_edge(current_node)

    def _evaluate_conditional_rule(
        self, source_node: str, workflow_context: WorkflowContext
    ) -> Dict[str, Any]:
        """Evaluate a conditional routing rule.

        Args:
            source_node: Source node name
            workflow_context: Current workflow context

        Returns:
            Routing decision
        """
        try:
            condition_func = self._conditional_rules[source_node]
            target_node = condition_func(workflow_context)

            if target_node in workflow_context.node_outputs:
                result = {
                    "next_node": target_node,
                    "routing_type": "conditional",
                    "condition_result": target_node,
                    "action": "continue",
                }
            else:
                result = {
                    "next_node": target_node,
                    "routing_type": "conditional",
                    "condition_result": target_node,
                    "action": "continue",
                }

            return result

        except Exception as e:
            return {
                "next_node": None,
                "routing_type": "conditional",
                "condition_result": str(e),
                "action": "error",
                "error": str(e),
            }

    def _evaluate_direct_edge(self, current_node: str) -> Dict[str, Any]:
        """Evaluate direct edge routing.

        Args:
            current_node: Current node name

        Returns:
            Routing decision
        """
        next_node = None
        for edge_key, target in self._edge_mappings.items():
            source, _ = edge_key.split("->")
            if source == current_node:
                next_node = target
                break

        if next_node:
            return {
                "next_node": next_node,
                "routing_type": "direct",
                "condition_result": None,
                "action": "continue",
            }
        else:
            return {
                "next_node": None,
                "routing_type": "direct",
                "condition_result": None,
                "action": "complete",
            }

    def is_approval_node(self, node_name: str, node_config: Dict[str, Any]) -> bool:
        """Check if a node requires human approval.

        Args:
            node_name: Node name
            node_config: Node configuration

        Returns:
            True if node requires approval, False otherwise
        """
        return node_config.get("requires_approval", False)

    def should_pause_for_approval(
        self, node_name: str, node_config: Dict[str, Any], workflow_context: WorkflowContext
    ) -> bool:
        """Determine if workflow should pause for human approval.

        Args:
            node_name: Node name
            node_config: Node configuration
            workflow_context: Current workflow context

        Returns:
            True if workflow should pause, False otherwise
        """
        if not self.is_approval_node(node_name, node_config):
            return False

        # Check if approval is already requested and pending
        for error in workflow_context.errors:
            if error.get("error_code") == "human_approval_required":
                if error.get("node_name") == node_name:
                    return True

        return False

    def create_approval_request(
        self, thread_id: str, node_name: str, workflow_context: WorkflowContext
    ) -> ApprovalRequest:
        """Create a human approval request.

        Args:
            thread_id: Workflow thread ID
            node_name: Node requesting approval
            workflow_context: Current workflow context

        Returns:
            ApprovalRequest instance
        """
        approval_request = ApprovalRequest(
            thread_id=thread_id,
            node_name=node_name,
            request_data=workflow_context.node_outputs.copy(),
            status=ApprovalStatus.PENDING,
            rejection_reason=None,
            created_at=datetime.now(),
            resolved_at=None,
        )

        return approval_request

    def handle_approval_decision(
        self,
        approval_request: ApprovalRequest,
        decision: str,
        approver_id: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a human approval decision.

        Args:
            approval_request: Approval request to resolve
            decision: Approval decision ("approve" or "reject")
            approver_id: ID of the approver
            comments: Optional approval comments

        Returns:
            Dict containing resolution result
        """
        if decision not in ["approve", "reject"]:
            raise ValueError("Decision must be 'approve' or 'reject'")

        if decision == "approve":
            approval_request.approve()
            return {
                "approved": True,
                "rejection_reason": None,
                "resolved_at": approval_request.resolved_at,
            }
        else:
            approval_request.reject(comments or "")
            return {
                "approved": False,
                "rejection_reason": approval_request.rejection_reason,
                "resolved_at": approval_request.resolved_at,
            }

    def cleanup_approval_requests(
        self, thread_id: str, approval_requests: List[ApprovalRequest]
    ) -> List[ApprovalRequest]:
        """Clean up resolved approval requests.

        Args:
            thread_id: Workflow thread ID
            approval_requests: List of approval requests

        Returns:
            List of active (pending) approval requests
        """
        active_requests = []
        for request in approval_requests:
            if request.status == ApprovalStatus.PENDING:
                active_requests.append(request)

        return active_requests

    def configure_routing(
        self,
        edges: List[Dict[str, Any]],
        conditional_edges: List[Dict[str, Any]],
    ) -> None:
        """Configure routing rules from workflow graph definition.

        Args:
            edges: Direct edges between nodes
            conditional_edges: Conditional routing rules
        """
        # Configure direct edges
        for edge in edges:
            self.add_edge_mapping(edge["source"], edge["target"])

        # Configure conditional edges
        for edge in conditional_edges:
            self.add_conditional_rule(edge["source"], edge["condition"])
