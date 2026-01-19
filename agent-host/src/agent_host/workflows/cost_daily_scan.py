"""Cost daily scan workflow - placeholder for future implementation."""

from shared.schemas.events import CostDailyScanEvent, CostWeeklyReviewEvent, Event

from agent_host.logging import get_logger
from agent_host.workflows.base import Workflow, WorkflowResult

logger = get_logger(__name__)


class CostDailyScanWorkflow(Workflow):
    """Workflow for cost optimization scans - placeholder."""

    def handle(self, event: Event) -> WorkflowResult:
        """Handle cost scan event - not implemented yet."""
        logger.warning("Cost scan workflow not implemented yet")
        return WorkflowResult(success=False, reason="not_implemented")

