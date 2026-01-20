"""Incident store - manages incident records and decision packets."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

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
        if self.config.is_local_mode():
            # Check local file
            evidence_dir = Path(self.config.local_evidence_dir)
            incident_file = evidence_dir / f"{incident_id}.json"
            decision_file = evidence_dir / f"{incident_id}_decision.json"
            return incident_file.exists() or decision_file.exists()
        else:
            # Check DynamoDB
            return self._exists_dynamodb(incident_id)

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

    def _exists_dynamodb(self, incident_id: str) -> bool:
        """Check if incident exists in DynamoDB.

        Args:
            incident_id: Incident ID

        Returns:
            True if incident exists, False otherwise
        """
        # TODO: Implement DynamoDB exists check
        logger.debug(f"Would check DynamoDB for incident: {incident_id} (not implemented yet)")
        return False

    def save_decision_packet(
        self,
        incident_id: str,
        decision_packet: dict[str, Any],
        event: Optional[PipelineFailureEvent] = None,
    ):
        """Save decision packet.

        Args:
            incident_id: Incident ID
            decision_packet: Decision packet dictionary
            event: Optional original event
        """
        logger.info(f"Saving decision packet for incident: {incident_id}")

        if self.config.is_local_mode():
            self._save_decision_local(incident_id, decision_packet, event)
        else:
            self._save_decision_dynamodb(incident_id, decision_packet, event)

    def _save_decision_local(
        self,
        incident_id: str,
        decision_packet: dict[str, Any],
        event: Optional[PipelineFailureEvent] = None,
    ):
        """Save decision packet to local file.

        Args:
            incident_id: Incident ID
            decision_packet: Decision packet dictionary
            event: Optional original event
        """
        # Create evidence directory if it doesn't exist
        evidence_dir = Path(self.config.local_evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Save decision packet
        decision_file = evidence_dir / f"{incident_id}_decision.json"
        decision_data = {
            "incident_id": incident_id,
            "decision_packet": decision_packet,
            "event": event.model_dump() if event else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        with open(decision_file, "w") as f:
            json.dump(decision_data, f, indent=2, default=str)

        logger.info(f"Saved decision packet to local file: {decision_file}")

    def _save_decision_dynamodb(
        self,
        incident_id: str,
        decision_packet: dict[str, Any],
        event: Optional[PipelineFailureEvent] = None,
    ):
        """Save decision packet to DynamoDB.

        Args:
            incident_id: Incident ID
            decision_packet: Decision packet dictionary
            event: Optional original event
        """
        # TODO: Implement DynamoDB save
        logger.info(f"Would save decision packet to DynamoDB: {incident_id} (not implemented yet)")

    def load_decision_packet(self, incident_id: str) -> Optional[dict[str, Any]]:
        """Load decision packet.

        Args:
            incident_id: Incident ID

        Returns:
            Decision packet dictionary if found, None otherwise
        """
        if self.config.is_local_mode():
            return self._load_decision_local(incident_id)
        else:
            return self._load_decision_dynamodb(incident_id)

    def _load_decision_local(self, incident_id: str) -> Optional[dict[str, Any]]:
        """Load decision packet from local file.

        Args:
            incident_id: Incident ID

        Returns:
            Decision packet dictionary if found, None otherwise
        """
        evidence_dir = Path(self.config.local_evidence_dir)
        decision_file = evidence_dir / f"{incident_id}_decision.json"

        if not decision_file.exists():
            logger.debug(f"Decision packet file not found: {decision_file}")
            return None

        try:
            with open(decision_file, "r") as f:
                data = json.load(f)
                return data.get("decision_packet")
        except Exception as e:
            logger.error(f"Failed to load decision packet from {decision_file}: {e}")
            return None

    def _load_decision_dynamodb(self, incident_id: str) -> Optional[dict[str, Any]]:
        """Load decision packet from DynamoDB.

        Args:
            incident_id: Incident ID

        Returns:
            Decision packet dictionary if found, None otherwise
        """
        # TODO: Implement DynamoDB load
        logger.debug(f"Would load decision packet from DynamoDB: {incident_id} (not implemented yet)")
        return None
