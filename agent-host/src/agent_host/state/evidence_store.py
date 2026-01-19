"""Evidence store - manages evidence packs."""

from shared.schemas.evidence import EvidencePack

from agent_host.config import config
from agent_host.logging import get_logger

logger = get_logger(__name__)


class EvidenceStore:
    """Stores and retrieves evidence packs."""

    def __init__(self):
        """Initialize evidence store."""
        self.config = config
        # TODO: Initialize S3 client if in AWS mode
        # TODO: Initialize local file storage if in local mode

    def save(self, incident_id: str, evidence: EvidencePack):
        """Save evidence pack.

        Args:
            incident_id: Incident ID
            evidence: Evidence pack to save
        """
        logger.info(f"Saving evidence pack: {incident_id}")

        if self.config.is_local_mode():
            self._save_local(incident_id, evidence)
        else:
            self._save_s3(incident_id, evidence)

    def _save_local(self, incident_id: str, evidence: EvidencePack):
        """Save evidence to local file.

        Args:
            incident_id: Incident ID
            evidence: Evidence pack
        """
        import json
        from pathlib import Path

        # Create evidence directory if it doesn't exist
        evidence_dir = Path(self.config.local_evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Save evidence pack
        evidence_file = evidence_dir / f"{incident_id}_evidence.json"
        evidence_data = evidence.model_dump()

        with open(evidence_file, "w") as f:
            json.dump(evidence_data, f, indent=2, default=str)

        logger.info(f"Saved evidence to local file: {evidence_file}")

    def _save_s3(self, incident_id: str, evidence: EvidencePack):
        """Save evidence to S3.

        Args:
            incident_id: Incident ID
            evidence: Evidence pack
        """
        # TODO: Implement S3 save
        logger.info(f"Would save to S3: {incident_id} (not implemented yet)")
