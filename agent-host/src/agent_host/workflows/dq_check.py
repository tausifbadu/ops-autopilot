"""Data quality check workflow - placeholder for future implementation."""

from shared.schemas.events import DQCheckRequestEvent, DQScheduledCheckEvent, Event

from agent_host.logging import get_logger
from agent_host.workflows.base import Workflow, WorkflowResult

logger = get_logger(__name__)


class DQCheckWorkflow(Workflow):
    """Workflow for handling data quality checks - placeholder."""

    def handle(self, event: Event) -> WorkflowResult:
        """Handle DQ check event - not implemented yet."""
        logger.warning("DQ check workflow not implemented yet")
        return WorkflowResult(success=False, reason="not_implemented")

