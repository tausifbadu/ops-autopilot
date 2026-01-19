"""Resource allowlist validation for security."""

from typing import Optional

from orchestration_sfn.config import config
from orchestration_sfn.logging import get_logger

logger = get_logger(__name__)


class Allowlist:
    """Validates resources against allowlist."""

    def __init__(self, enabled: bool = None, allowlist_file: Optional[str] = None):
        """Initialize allowlist.

        Args:
            enabled: Whether allowlist is enabled (defaults to config)
            allowlist_file: Path to allowlist file (optional, for future use)
        """
        self.enabled = enabled if enabled is not None else config.allowlist_enabled
        self.allowed_state_machines: set[str] = set()
        self.allowed_executions: set[str] = set()
        
        # TODO: Load from file if provided
        if allowlist_file:
            logger.info(f"Loading allowlist from {allowlist_file}")
            # Future: Load from YAML/JSON file

    def is_state_machine_allowed(self, state_machine_arn: str) -> bool:
        """Check if state machine ARN is allowed.

        Args:
            state_machine_arn: State machine ARN to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_state_machines:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing {state_machine_arn}")
            return True

        is_allowed = state_machine_arn in self.allowed_state_machines
        if not is_allowed:
            logger.warning(f"State machine ARN not in allowlist: {state_machine_arn}")

        return is_allowed

    def is_execution_allowed(self, execution_arn: str) -> bool:
        """Check if execution ARN is allowed.

        Args:
            execution_arn: Execution ARN to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_executions:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing {execution_arn}")
            return True

        is_allowed = execution_arn in self.allowed_executions
        if not is_allowed:
            logger.warning(f"Execution ARN not in allowlist: {execution_arn}")

        return is_allowed

    def add_state_machine(self, state_machine_arn: str):
        """Add state machine to allowlist.

        Args:
            state_machine_arn: State machine ARN to add
        """
        self.allowed_state_machines.add(state_machine_arn)
        logger.info(f"Added state machine to allowlist: {state_machine_arn}")

    def add_execution(self, execution_arn: str):
        """Add execution to allowlist.

        Args:
            execution_arn: Execution ARN to add
        """
        self.allowed_executions.add(execution_arn)
        logger.info(f"Added execution to allowlist: {execution_arn}")


# Global allowlist instance
allowlist = Allowlist()
