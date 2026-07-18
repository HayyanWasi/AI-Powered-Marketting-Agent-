"""Execution Service - Coordinates workflow node execution."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .models.workflow_context import WorkflowContext
from .models.execution_state import ExecutionState
from .models.execution_error import ExecutionError
from .services.retry_service import RetryService
from .services.state_manager import StateManager


class ExecutionService:
    """Service that orchestrates workflow execution.

    The ExecutionService is responsible for coordinating the execution
    of workflow nodes in the correct order according to the workflow graph.
    It manages state transitions, handles completions, and coordinates
    with retry and state management services.
    """

    def __init__(self):
        self._retry_service = RetryService()
        self._state_manager = StateManager()

    def execute_workflow(
        self,
        workflow_graph,
        initial_context: WorkflowContext,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow.

        Args:
            workflow_graph: WorkflowGraph definition
            initial_context: Initial workflow context
            options: Execution options

        Returns:
            Dict containing execution results
        """
        from ..models.execution_state import ExecutionState

        context = initial_context

        # Update initial context state
        context = context.update(state=ExecutionState.RUNNING)
        self._state_manager.update_workflow_state(workflow_graph.graph_id, context)

        results = {
            "workflow_id": workflow_graph.graph_id,
            "thread_id": context.thread_id,
            "started_at": datetime.now().isoformat(),
            "completed_nodes": [],
            "failed_nodes": [],
            "execution_path": [],
            "final_context": None,
            "status": "completed",
            "errors": [],
        }

        try:
            # Execute each node in order
            for node_name in workflow_graph.execution_order:
                # Skip if node is already completed
                if node_name in results["completed_nodes"]:
                    continue

                current_node = workflow_graph.nodes[node_name]
                context = context.update(current_node=node_name)

                # Execute node
                execution_result = self._execute_single_node(current_node, context, options or {})

                # Update context based on execution result
                context = execution_result["context"]
                if execution_result["success"]:
                    results["completed_nodes"].append(node_name)
                    results["execution_path"].append(node_name)
                else:
                    results["failed_nodes"].append(node_name)
                    results["errors"].append(execution_result.get("error", {}))

                    # If node failed and retries exhausted, stop workflow
                    if execution_result.get("retries_exhausted", False):
                        results["status"] = "failed"
                        results["final_context"] = context.to_dict()
                        break

                # Check if we've reached terminal nodes
                if node_name in workflow_graph.terminal_nodes:
                    results["reached_terminal_nodes"] = True

            # Update final context
            results["final_context"] = context.to_dict()
            results["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            results["final_context"] = context.to_dict()
            results["errors"].append(
                {
                    "code": "execution_error",
                    "message": str(e),
                }
            )

        # Update state manager with final state
        self._state_manager.update_workflow_state(workflow_graph.graph_id, context)

        return results

    def _execute_single_node(
        self,
        node: Any,
        context: WorkflowContext,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single node.

        Args:
            node: WorkflowNode to execute
            context: WorkflowContext
            options: Execution options

        Returns:
            Dict containing execution result
        """
        try:
            # Check if retries are needed
            retry_policy = node.retry_policy
            retry_count = 0

            while retry_count <= retry_policy.max_retries:
                try:
                    # Execute node handler
                    result_context = node.handler(context)

                    # Update retry count
                    node.retry_count = retry_count

                    return {
                        "success": True,
                        "context": result_context,
                        "retries_attempted": retry_count,
                    }

                except Exception as e:
                    retry_count += 1

                    # Check if retries exhausted
                    if retry_count > retry_policy.max_retries:
                        error = ExecutionError(
                            node_name=node.name,
                            error_code="node_failed",
                            message=str(e),
                            retry_count=retry_count,
                            timestamp=datetime.now(),
                            recoverable=False,
                        )

                        error_context = context.add_error(error.to_dict())
                        return {
                            "success": False,
                            "context": error_context,
                            "retries_exhausted": True,
                            "error": {
                                "code": error.error_code,
                                "message": error.message,
                                "node": error.node_name,
                                "retry_count": error.retry_count,
                            },
                        }

                    # Wait for retry delay
                    import time

                    delay = retry_policy.calculate_delay(retry_count - 1)
                    if delay > 0:
                        time.sleep(delay)

            # Fallback (should not reach here)
            error = ExecutionError(
                node_name=node.name,
                error_code="execution_error",
                message="Unexpected error in retry loop",
                retry_count=retry_count,
                timestamp=datetime.now(),
                recoverable=False,
            )

            error_context = context.add_error(error.to_dict())
            return {
                "success": False,
                "context": error_context,
                "error": {
                    "code": error.error_code,
                    "message": error.message,
                },
            }

        except Exception as e:
            error = ExecutionError(
                node_name=node.name,
                error_code="execution_error",
                message=str(e),
                retry_count=0,
                timestamp=datetime.now(),
                recoverable=False,
            )

            error_context = context.add_error(error.to_dict())
            return {
                "success": False,
                "context": error_context,
                "error": {
                    "code": error.error_code,
                    "message": error.message,
                },
            }
