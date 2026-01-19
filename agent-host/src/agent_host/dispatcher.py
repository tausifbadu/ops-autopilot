"""Event dispatcher - routes events to appropriate workflows."""

from typing import Optional

from shared.schemas.events import (
    APIFailureEvent,
    CostDailyScanEvent,
    CostWeeklyReviewEvent,
    DailySweepEvent,
    DQCheckRequestEvent,
    DQScheduledCheckEvent,
    Event,
    EventType,
    PipelineFailureEvent,
    PipelineSLACheckEvent,
)

from agent_host.logging import get_logger
from agent_host.workflows.api_failure import APIFailureWorkflow
from agent_host.workflows.cost_daily_scan import CostDailyScanWorkflow
from agent_host.workflows.daily_sweep import DailySweepWorkflow
from agent_host.workflows.dq_check import DQCheckWorkflow
from agent_host.workflows.pipeline_failure import PipelineFailureWorkflow

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

    def dispatch(self, event: Event) -> Optional[str]:
        """Dispatch event to appropriate workflow.

        Args:
            event: Event to process

        Returns:
            Incident ID if event was processed, None if skipped/error

        Raises:
            ValueError: If event type is not supported
        """
        event_type = event.event_type

        logger.info(f"Dispatching event: {event_type} (event_id: {event.event_id})")

        # Get workflow for this event type
        workflow = self.workflows.get(event_type)

        if workflow is None:
            logger.error(f"No workflow registered for event type: {event_type}")
            raise ValueError(f"Unsupported event type: {event_type}")

        try:
            # Process event through workflow
            result = workflow.handle(event)

            if result.success:
                logger.info(
                    f"Event processed successfully: {event_type} -> incident_id: {result.incident_id}"
                )
                return result.incident_id
            else:
                logger.warning(
                    f"Event processing skipped/failed: {event_type} -> reason: {result.reason}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Error processing event {event_type} (event_id: {event.event_id}): {e}",
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
