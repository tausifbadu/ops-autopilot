"""Remediation Agent - executes remediation plans with policy gating."""

import time
from typing import Any, Optional

from pydantic import BaseModel

from shared.schemas.rca import RecommendedAction

from agent_host.config import config
from agent_host.logging import get_logger
from agent_host.mcp_client.base import MCPClient, MCPClientConfig
from agent_host.policy import PolicyDecision, RemediationAction, get_policy_engine

logger = get_logger(__name__)


class RemediationResult(BaseModel):
    """Result of remediation execution."""

    success: bool
    actions_taken: list[dict[str, Any]]
    actions_failed: list[dict[str, Any]]
    verification: Optional[dict[str, Any]] = None
    rollback_needed: bool = False
    error: Optional[str] = None


class RemediationPlan(BaseModel):
    """Remediation plan with actions to execute."""

    incident_id: str
    actions: list[RecommendedAction]
    target_tier: Optional[str] = None
    context: dict[str, Any] = {}


class RemediationAgent:
    """Agent that executes remediation plans with policy gating."""

    def __init__(self):
        """Initialize Remediation Agent."""
        self.config = config
        self.policy_engine = get_policy_engine()

        # Initialize MCP clients
        self.orchestration_client = MCPClient(
            MCPClientConfig(base_url=config.mcp_orchestration_url)
        )

        logger.info("Initialized Remediation Agent")

    def execute_remediation(
        self, plan: RemediationPlan
    ) -> RemediationResult:
        """Execute remediation plan with policy gating.

        Args:
            plan: Remediation plan

        Returns:
            Remediation result
        """
        logger.info(f"Executing remediation plan for incident: {plan.incident_id}")

        actions_taken = []
        actions_failed = []

        for action in plan.actions:
            try:
                # Step 1: Policy check
                policy_result = self._check_policy(action, plan)
                if not policy_result.allowed:
                    logger.warning(
                        f"Action blocked by policy: {action.action_type} - {policy_result.reason}"
                    )
                    actions_failed.append({
                        "action": action.action_type,
                        "reason": "policy_blocked",
                        "policy_reason": policy_result.reason,
                    })
                    continue

                # Step 2: Execute action
                logger.info(f"Executing action: {action.action_type}")
                execution_result = self._execute_action(action, plan)

                if execution_result["success"]:
                    actions_taken.append({
                        "action": action.action_type,
                        "result": "success",
                        "details": execution_result.get("details", {}),
                    })
                    logger.info(f"Action succeeded: {action.action_type}")
                else:
                    actions_failed.append({
                        "action": action.action_type,
                        "reason": execution_result.get("error", "unknown"),
                        "details": execution_result.get("details", {}),
                    })
                    logger.error(f"Action failed: {action.action_type} - {execution_result.get('error')}")

            except Exception as e:
                logger.error(f"Error executing action {action.action_type}: {e}", exc_info=True)
                actions_failed.append({
                    "action": action.action_type,
                    "reason": "execution_error",
                    "error": str(e),
                })

        # Step 3: Verify remediation (if actions were taken)
        verification = None
        if actions_taken:
            verification = self._verify_remediation(plan, actions_taken)

        # Determine overall success
        success = len(actions_taken) > 0 and len(actions_failed) == 0

        return RemediationResult(
            success=success,
            actions_taken=actions_taken,
            actions_failed=actions_failed,
            verification=verification,
            rollback_needed=False,  # MVP: no rollback logic yet
        )

    def _check_policy(
        self, action: RecommendedAction, plan: RemediationPlan
    ) -> PolicyDecision:
        """Check if action is allowed by policy.

        Args:
            action: Recommended action
            plan: Remediation plan

        Returns:
            Policy decision
        """
        # Extract target from action or plan context
        target = action.parameters.get("target") or plan.context.get("target", "unknown")

        remediation_action = RemediationAction(
            action_type=action.action_type,
            target=target,
            parameters=action.parameters,
            tier=plan.target_tier,
            context=plan.context,
        )

        return self.policy_engine.evaluate_action(remediation_action)

    def _execute_action(
        self, action: RecommendedAction, plan: RemediationPlan
    ) -> dict[str, Any]:
        """Execute a remediation action.

        Args:
            action: Action to execute
            plan: Remediation plan

        Returns:
            Execution result
        """
        action_type = action.action_type

        try:
            if action_type == "retry_execution" or action_type == "start_execution":
                return self._execute_retry_or_start(action, plan)
            elif action_type == "stop_execution":
                return self._execute_stop(action, plan)
            elif action_type == "restart_service":
                return self._execute_restart_service(action, plan)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                }

        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    def _execute_retry_or_start(
        self, action: RecommendedAction, plan: RemediationPlan
    ) -> dict[str, Any]:
        """Execute retry or start execution action.

        Args:
            action: Action to execute
            plan: Remediation plan

        Returns:
            Execution result
        """
        # Get state machine ARN from parameters or context
        state_machine_arn = (
            action.parameters.get("state_machine_arn")
            or plan.context.get("state_machine_arn")
        )

        if not state_machine_arn:
            return {
                "success": False,
                "error": "state_machine_arn not provided",
            }

        # Get input data (if provided)
        input_data = action.parameters.get("input_data") or plan.context.get("input_data")

        try:
            # Call orchestration MCP server
            response = self.orchestration_client.call_tool(
                tool_name="start_execution",
                arguments={
                    "state_machine_arn": state_machine_arn,
                    "input_data": input_data,
                    "name": action.parameters.get("execution_name"),
                },
            )

            if response.result:
                execution_arn = response.result.get("executionArn")
                logger.info(f"Started execution: {execution_arn}")

                return {
                    "success": True,
                    "details": {
                        "execution_arn": execution_arn,
                        "start_date": response.result.get("startDate"),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "No execution ARN returned",
                }

        except Exception as e:
            logger.error(f"Failed to start execution: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _execute_stop(
        self, action: RecommendedAction, plan: RemediationPlan
    ) -> dict[str, Any]:
        """Execute stop execution action.

        Args:
            action: Action to execute
            plan: Remediation plan

        Returns:
            Execution result
        """
        execution_arn = (
            action.parameters.get("execution_arn")
            or plan.context.get("execution_arn")
        )

        if not execution_arn:
            return {
                "success": False,
                "error": "execution_arn not provided",
            }

        try:
            response = self.orchestration_client.call_tool(
                tool_name="stop_execution",
                arguments={
                    "execution_arn": execution_arn,
                    "error": action.parameters.get("error", "UserRequested"),
                    "cause": action.parameters.get("cause", "Stopped by Remediation Agent"),
                },
            )

            if response.result:
                logger.info(f"Stopped execution: {execution_arn}")

                return {
                    "success": True,
                    "details": {
                        "execution_arn": execution_arn,
                        "stop_date": response.result.get("stopDate"),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "Stop execution failed",
                }

        except Exception as e:
            logger.error(f"Failed to stop execution: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _execute_restart_service(
        self, action: RecommendedAction, plan: RemediationPlan
    ) -> dict[str, Any]:
        """Execute restart service action (placeholder for Phase 0).

        Args:
            action: Action to execute
            plan: Remediation plan

        Returns:
            Execution result
        """
        logger.warning("Restart service action not yet implemented in Phase 0")
        return {
            "success": False,
            "error": "Restart service not implemented in Phase 0",
        }

    def _verify_remediation(
        self, plan: RemediationPlan, actions_taken: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Verify that remediation was successful.

        Args:
            plan: Remediation plan
            actions_taken: Actions that were executed

        Returns:
            Verification result
        """
        logger.info("Verifying remediation")

        # For MVP, do basic verification
        # Check if executions were started successfully
        verification = {
            "status": "pending",
            "checks": [],
        }

        for action_result in actions_taken:
            if action_result["action"] in ["retry_execution", "start_execution"]:
                execution_arn = action_result.get("details", {}).get("execution_arn")
                if execution_arn:
                    # Wait a bit for execution to start
                    time.sleep(2)

                    # Check execution status
                    try:
                        response = self.orchestration_client.call_tool(
                            tool_name="get_execution_details",
                            arguments={"execution_arn": execution_arn},
                        )

                        if response.result:
                            status = response.result.get("status")
                            verification["checks"].append({
                                "execution_arn": execution_arn,
                                "status": status,
                                "verified": status in ["RUNNING", "SUCCEEDED"],
                            })

                            if status == "SUCCEEDED":
                                verification["status"] = "verified"
                            elif status == "RUNNING":
                                verification["status"] = "in_progress"
                            elif status in ["FAILED", "TIMED_OUT", "ABORTED"]:
                                verification["status"] = "failed"

                    except Exception as e:
                        logger.warning(f"Failed to verify execution: {e}")
                        verification["checks"].append({
                            "execution_arn": execution_arn,
                            "status": "unknown",
                            "verified": False,
                            "error": str(e),
                        })

        return verification
