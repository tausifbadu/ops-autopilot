"""Base workflow class."""

from abc import ABC, abstractmethod
from typing import Any, Optional

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
        decision_packet: Optional[Any] = None,
        remediation_result: Optional[Any] = None,
    ):
        """Initialize workflow result.

        Args:
            success: Whether workflow completed successfully
            incident_id: Incident ID if created
            reason: Reason if skipped or failed
            decision_packet: Optional decision packet from Coordinator
            remediation_result: Optional remediation result
        """
        self.success = success
        self.incident_id = incident_id
        self.reason = reason
        self.decision_packet = decision_packet
        self.remediation_result = remediation_result


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
