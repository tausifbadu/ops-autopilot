"""Resource allowlist validation for security."""

from typing import Optional

from data_execution.config import config
from data_execution.logging import get_logger

logger = get_logger(__name__)


class Allowlist:
    """Validates Glue jobs and EMR clusters against allowlist."""

    def __init__(self, enabled: bool = None, allowlist_file: Optional[str] = None):
        """Initialize allowlist.

        Args:
            enabled: Whether allowlist is enabled (defaults to config)
            allowlist_file: Path to allowlist file (optional, for future use)
        """
        self.enabled = enabled if enabled is not None else config.allowlist_enabled
        self.allowed_glue_jobs: set[str] = set()
        self.allowed_emr_clusters: set[str] = set()
        
        # TODO: Load from file if provided
        if allowlist_file:
            logger.info(f"Loading allowlist from {allowlist_file}")
            # Future: Load from YAML/JSON file

    def is_glue_job_allowed(self, job_name: str) -> bool:
        """Check if Glue job is allowed.

        Args:
            job_name: Glue job name to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_glue_jobs:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing Glue job: {job_name}")
            return True

        is_allowed = job_name in self.allowed_glue_jobs
        if not is_allowed:
            logger.warning(f"Glue job not in allowlist: {job_name}")

        return is_allowed

    def is_emr_cluster_allowed(self, cluster_id: str) -> bool:
        """Check if EMR cluster is allowed.

        Args:
            cluster_id: EMR cluster ID to check

        Returns:
            True if allowed or allowlist disabled, False otherwise
        """
        if not self.enabled:
            return True  # Allowlist disabled, allow all

        if not self.allowed_emr_clusters:
            # Empty allowlist means allow all (for MVP)
            logger.debug(f"Allowlist empty, allowing EMR cluster: {cluster_id}")
            return True

        is_allowed = cluster_id in self.allowed_emr_clusters
        if not is_allowed:
            logger.warning(f"EMR cluster not in allowlist: {cluster_id}")

        return is_allowed

    def add_glue_job(self, job_name: str):
        """Add Glue job to allowlist.

        Args:
            job_name: Glue job name to add
        """
        self.allowed_glue_jobs.add(job_name)
        logger.info(f"Added Glue job to allowlist: {job_name}")

    def add_emr_cluster(self, cluster_id: str):
        """Add EMR cluster to allowlist.

        Args:
            cluster_id: EMR cluster ID to add
        """
        self.allowed_emr_clusters.add(cluster_id)
        logger.info(f"Added EMR cluster to allowlist: {cluster_id}")


# Global allowlist instance
allowlist = Allowlist()
