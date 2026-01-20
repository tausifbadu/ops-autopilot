"""Pipeline failure workflow - handles Step Functions/Glue/EMR execution failures."""

from typing import Optional

from shared.schemas.events import PipelineFailureEvent

from agent_host.agents.coordinator import CoordinatorAgent
from agent_host.agents.remediation_agent import RemediationAgent, RemediationPlan
from agent_host.logging import get_logger
from agent_host.state.incident_store import IncidentStore
from agent_host.workflows.base import Workflow, WorkflowResult

logger = get_logger(__name__)


class PipelineFailureWorkflow(Workflow):
    """Workflow for handling pipeline failures."""

    def __init__(self):
        """Initialize pipeline failure workflow."""
        self.coordinator = CoordinatorAgent()
        self.remediation_agent = RemediationAgent()
        self.incident_store = IncidentStore()

    def handle(self, event: PipelineFailureEvent) -> WorkflowResult:
        """Handle pipeline failure event.

        Args:
            event: Pipeline failure event

        Returns:
            Workflow result with incident ID
        """
        logger.info(
            f"Processing pipeline failure: execution_arn={event.execution_arn}, "
            f"state_machine_arn={event.state_machine_arn}"
        )

        try:
            # Step 1: Coordinator orchestrates investigation
            logger.info("Coordinating investigation via Coordinator Agent")
            decision_packet = self.coordinator.coordinate(event)

            incident_id = decision_packet.incident_id

            # Step 2: Execute remediation if safe to autofix
            remediation_result = None
            if decision_packet.safe_to_autofix and decision_packet.actions_allowed:
                logger.info(
                    f"Safe to autofix: executing {len(decision_packet.actions_allowed)} actions"
                )

                # Extract RecommendedAction objects from allowed actions
                allowed_actions = []
                for action_dict in decision_packet.actions_allowed:
                    if "recommended_action" in action_dict:
                        allowed_actions.append(action_dict["recommended_action"])

                # Create remediation plan from allowed actions
                remediation_plan = RemediationPlan(
                    incident_id=incident_id,
                    actions=allowed_actions,
                    target_tier=event.tier.value if event.tier else None,
                    context={
                        "execution_arn": event.execution_arn.value if event.execution_arn else None,
                        "state_machine_arn": event.state_machine_arn.value if event.state_machine_arn else None,
                        "target": event.execution_arn.value if event.execution_arn else event.state_machine_arn.value if event.state_machine_arn else None,
                    },
                )

                # Execute remediation
                remediation_result = self.remediation_agent.execute_remediation(remediation_plan)

                logger.info(
                    f"Remediation complete: success={remediation_result.success}, "
                    f"actions_taken={len(remediation_result.actions_taken)}"
                )
            else:
                logger.info(
                    f"Not safe to autofix or no actions allowed. "
                    f"Needs human: {len(decision_packet.needs_human)} items"
                )

            logger.info(
                f"Pipeline failure processed: incident_id={incident_id}, "
                f"classification={decision_packet.root_cause.get('classification')}, "
                f"confidence={decision_packet.root_cause.get('confidence')}"
            )

            return WorkflowResult(
                success=True,
                incident_id=incident_id,
                decision_packet=decision_packet,
                remediation_result=remediation_result,
            )

        except Exception as e:
            logger.error(f"Error processing pipeline failure: {e}", exc_info=True)
            incident_id = self._generate_incident_id(event)
            return WorkflowResult(
                success=False, incident_id=incident_id, reason=f"error: {str(e)}"
            )

    def _generate_incident_id(self, event: PipelineFailureEvent) -> str:
        """Generate unique incident ID from event.

        Args:
            event: Pipeline failure event

        Returns:
            Incident ID
        """
        # Use execution ARN if available, otherwise use event ID
        if event.execution_arn:
            # Extract execution name from ARN
            arn_parts = event.execution_arn.value.split(":")
            execution_name = arn_parts[-1] if len(arn_parts) > 0 else "unknown"
            return f"incident_{execution_name}_{event.timestamp.strftime('%Y%m%d%H%M%S')}"
        else:
            return f"incident_{event.event_id}"
