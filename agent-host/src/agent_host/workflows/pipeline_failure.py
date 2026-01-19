"""Pipeline failure workflow - handles Step Functions/Glue/EMR execution failures."""

from typing import Optional

from shared.schemas.events import PipelineFailureEvent
from shared.schemas.rca import PipelineIncidentAnalysis

from agent_host.agents.pipeline_rca_agent import PipelineRCAAgent
from agent_host.logging import get_logger
from agent_host.state.incident_store import IncidentStore
from agent_host.workflows.base import Workflow, WorkflowResult

logger = get_logger(__name__)


class PipelineFailureWorkflow(Workflow):
    """Workflow for handling pipeline failures."""

    def __init__(self):
        """Initialize pipeline failure workflow."""
        self.rca_agent = PipelineRCAAgent()
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

        # Step 1: Idempotency check
        incident_id = self._generate_incident_id(event)
        if self.incident_store.exists(incident_id):
            logger.info(f"Incident already processed: {incident_id}")
            return WorkflowResult(
                success=False, incident_id=incident_id, reason="duplicate"
            )

        try:
            # Step 2: Activate Pipeline RCA Agent
            logger.info("Activating Pipeline RCA Agent")
            rca_result: PipelineIncidentAnalysis = self.rca_agent.investigate(event)

            # Step 3: Store incident
            self.incident_store.save(incident_id, rca_result, event)

            logger.info(
                f"Pipeline failure processed: incident_id={incident_id}, "
                f"classification={rca_result.classification}, "
                f"confidence={rca_result.confidence.value}"
            )

            return WorkflowResult(success=True, incident_id=incident_id)

        except Exception as e:
            logger.error(f"Error processing pipeline failure: {e}", exc_info=True)
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
