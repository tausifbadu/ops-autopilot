"""Event dispatcher - routes events to appropriate workflows."""

from typing import TYPE_CHECKING, Optional

from shared.schemas.events import (
    Event,
    EventType,
)

from agent_host.logging import get_logger
from agent_host.workflows.api_failure import APIFailureWorkflow
from agent_host.workflows.cost_daily_scan import CostDailyScanWorkflow
from agent_host.workflows.daily_sweep import DailySweepWorkflow
from agent_host.workflows.dq_check import DQCheckWorkflow
from agent_host.workflows.pipeline_failure import PipelineFailureWorkflow

if TYPE_CHECKING:
    from agent_host.workflows.base import WorkflowResult

logger = get_logger(__name__)


class Dispatcher:
    """Routes events to appropriate workflows based on event type."""

    def __init__(self):
        """Initialize dispatcher with workflow instances."""
        self.workflows = {
            EventType.PIPELINE_FAILURE: PipelineFailureWorkflow(),
            EventType.API_FAILURE: APIFailureWorkflow(),
            EventType.DQ_CHECK_REQUEST: DQCheckWorkflow(),
            EventType.DQ_SCHEDULED_CHECK: DQCheckWorkflow(),
            EventType.DAILY_SWEEP: DailySweepWorkflow(),
            EventType.COST_DAILY_SCAN: CostDailyScanWorkflow(),
            EventType.COST_WEEKLY_REVIEW: CostDailyScanWorkflow(),  # Reuse for now
            EventType.PIPELINE_SLA_CHECK: PipelineFailureWorkflow(),  # Similar to failure
        }

    def dispatch(self, event: Event) -> Optional["WorkflowResult"]:
        """Dispatch event to appropriate workflow.

        Args:
            event: Event to process

        Returns:
            WorkflowResult if event was processed, None if skipped/error

        Raises:
            ValueError: If event type is not supported
        """
        from agent_host.workflows.base import WorkflowResult

        event_type = event.event_type

        logger.info("Dispatching event: %s (event_id: %s)", event_type, event.event_id)

        # Get workflow for this event type
        workflow = self.workflows.get(event_type)

        if workflow is None:
            logger.error("No workflow registered for event type: %s", event_type)
            raise ValueError(f"Unsupported event type: {event_type}")

        try:
            # Process event through workflow
            result = workflow.handle(event)

            if result.success:
                logger.info(
                    "Event processed successfully: %s -> incident_id: %s", event_type, result.incident_id
                )
                return result
            else:
                logger.warning(
                    "Event processing skipped/failed: %s -> reason: %s", event_type, result.reason
                )
                return None

        except Exception as e:
            logger.error(
                "Error processing event %s (event_id: %s): %s",
                event_type,
                event.event_id,
                e,
                exc_info=True,
            )
            raise

    def get_workflow(self, event_type: EventType):
        """Get workflow for event type.

        Args:
            event_type: Event type

        Returns:
            Workflow instance or None
        """
        return self.workflows.get(event_type)
