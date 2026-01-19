"""Incident store - manages incident records."""

from typing import Optional

from shared.schemas.events import PipelineFailureEvent
from shared.schemas.rca import PipelineIncidentAnalysis

from agent_host.config import config
from agent_host.logging import get_logger

logger = get_logger(__name__)


class IncidentStore:
    """Stores and retrieves incident records."""

    def __init__(self):
        """Initialize incident store."""
        self.config = config
        # TODO: Initialize DynamoDB client if in AWS mode
        # TODO: Initialize local file storage if in local mode

    def exists(self, incident_id: str) -> bool:
        """Check if incident already exists.

        Args:
            incident_id: Incident ID

        Returns:
            True if incident exists, False otherwise
        """
        # TODO: Check DynamoDB or local file
        logger.debug(f"Checking if incident exists: {incident_id}")
        return False  # Placeholder

    def save(
        self,
        incident_id: str,
        rca_result: PipelineIncidentAnalysis,
        event: PipelineFailureEvent,
    ):
        """Save incident record.

        Args:
            incident_id: Incident ID
            rca_result: RCA analysis result
            event: Original event
        """
        logger.info(f"Saving incident: {incident_id}")

        if self.config.is_local_mode():
            # Save to local file
            self._save_local(incident_id, rca_result, event)
        else:
            # Save to DynamoDB
            self._save_dynamodb(incident_id, rca_result, event)

    def _save_local(
        self,
        incident_id: str,
        rca_result: PipelineIncidentAnalysis,
        event: PipelineFailureEvent,
    ):
        """Save incident to local file.

        Args:
            incident_id: Incident ID
            rca_result: RCA analysis result
            event: Original event
        """
        import json
        import os
        from pathlib import Path

        # Create evidence directory if it doesn't exist
        evidence_dir = Path(self.config.local_evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Save incident record
        incident_file = evidence_dir / f"{incident_id}.json"
        incident_data = {
            "incident_id": incident_id,
            "event": event.model_dump(),
            "rca_result": rca_result.model_dump(),
            "timestamp": event.timestamp.isoformat(),
        }

        with open(incident_file, "w") as f:
            json.dump(incident_data, f, indent=2, default=str)

        logger.info(f"Saved incident to local file: {incident_file}")

    def _save_dynamodb(
        self,
        incident_id: str,
        rca_result: PipelineIncidentAnalysis,
        event: PipelineFailureEvent,
    ):
        """Save incident to DynamoDB.

        Args:
            incident_id: Incident ID
            rca_result: RCA analysis result
            event: Original event
        """
        # TODO: Implement DynamoDB save
        logger.info(f"Would save to DynamoDB: {incident_id} (not implemented yet)")
