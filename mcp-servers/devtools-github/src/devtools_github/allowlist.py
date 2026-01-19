"""Resource allowlist validation for security."""

from typing import Optional

from devtools_github.config import config
from devtools_github.logging import get_logger

logger = get_logger(__name__)


class Allowlist:
    """Validates repositories against allowlist."""

    def __init__(self, enabled: bool = None, allowlist_file: Optional[str] = None):
        """Initialize allowlist.

        Args:
            enabled: Whether allowlist is enabled (defaults to config)
            allowlist_file: Path to allowlist file (optional, for future use)
        """
        self.enabled = enabled if enabled is not None else config.allowlist_enabled
        self.allowed_repositories: set[str] = set()
        
        # TODO: Load from file if provided
        if allowlist_file:
            logger.info(f"Loading allowlist from {allowlist_file}")
            # Future: Load from YAML/JSON file

    def is_repository_allowed(self, repository: str) -> bool:
        """Check if repository is allowed.

        Args:
            repository: Repository name (owner/repo) to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_repositories:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing {repository}")
            return True

        is_allowed = repository in self.allowed_repositories
        if not is_allowed:
            logger.warning(f"Repository not in allowlist: {repository}")

        return is_allowed

    def add_repository(self, repository: str):
        """Add repository to allowlist.

        Args:
            repository: Repository name (owner/repo) to add
        """
        self.allowed_repositories.add(repository)
        logger.info(f"Added repository to allowlist: {repository}")


# Global allowlist instance
allowlist = Allowlist()
