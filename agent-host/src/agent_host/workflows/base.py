"""Base workflow class."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.schemas.events import Event

from agent_host.logging import get_logger

logger = get_logger(__name__)


class WorkflowResult:
    """Result of workflow execution."""

    def __init__(
        self,
        success: bool,
        incident_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Initialize workflow result.

        Args:
            success: Whether workflow completed successfully
            incident_id: Incident ID if created
            reason: Reason if skipped or failed
        """
        self.success = success
        self.incident_id = incident_id
        self.reason = reason


class Workflow(ABC):
    """Base class for all workflows."""

    @abstractmethod
    def handle(self, event: Event) -> WorkflowResult:
        """Handle an event.

        Args:
            event: Event to process

        Returns:
            Workflow result
        """
        pass
