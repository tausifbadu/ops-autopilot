"""Resource allowlist validation for security."""

from typing import Optional

from observability_cloudwatch.config import config
from observability_cloudwatch.logging import get_logger

logger = get_logger(__name__)


class Allowlist:
    """Validates log groups against allowlist."""

    def __init__(self, enabled: bool = None, allowlist_file: Optional[str] = None):
        """Initialize allowlist.

        Args:
            enabled: Whether allowlist is enabled (defaults to config)
            allowlist_file: Path to allowlist file (optional, for future use)
        """
        self.enabled = enabled if enabled is not None else config.allowlist_enabled
        self.allowed_log_groups: set[str] = set()
        
        # TODO: Load from file if provided
        if allowlist_file:
            logger.info(f"Loading allowlist from {allowlist_file}")
            # Future: Load from YAML/JSON file

    def is_log_group_allowed(self, log_group: str) -> bool:
        """Check if log group is allowed.

        Args:
            log_group: Log group name to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_log_groups:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing {log_group}")
            return True

        is_allowed = log_group in self.allowed_log_groups
        if not is_allowed:
            logger.warning(f"Log group not in allowlist: {log_group}")

        return is_allowed

    def add_log_group(self, log_group: str):
        """Add log group to allowlist.

        Args:
            log_group: Log group name to add
        """
        self.allowed_log_groups.add(log_group)
        logger.info(f"Added log group to allowlist: {log_group}")


# Global allowlist instance
allowlist = Allowlist()
