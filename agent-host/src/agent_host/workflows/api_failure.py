"""API failure workflow - placeholder for future implementation."""

from shared.schemas.events import APIFailureEvent

from agent_host.logging import get_logger
from agent_host.workflows.base import Workflow, WorkflowResult

logger = get_logger(__name__)


class APIFailureWorkflow(Workflow):
    """Workflow for handling API failures - placeholder."""

    def handle(self, event: APIFailureEvent) -> WorkflowResult:
        """Handle API failure event - not implemented yet."""
        logger.warning(f"API failure workflow not implemented yet: {event.service_name}")
        return WorkflowResult(success=False, reason="not_implemented")

