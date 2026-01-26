"""Coordinator Agent - orchestrates specialist agents and applies policy."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from shared.schemas.events import (
    APIFailureEvent,
    EventType,
    PipelineFailureEvent,
)
from shared.schemas.rca import (
    PipelineIncidentAnalysis,
    RecommendedAction,
)

from agent_host.agents.pipeline_rca_agent import PipelineRCAAgent
from agent_host.config import config
from agent_host.logging import get_logger
from agent_host.policy import PolicyDecision, RemediationAction, get_policy_engine
from agent_host.state.evidence_store import EvidenceStore
from agent_host.state.incident_store import IncidentStore

logger = get_logger(__name__)


class DecisionPacket(BaseModel):
    """Coordinator's decision packet - merged output from all agents."""

    incident_id: str
    event_type: EventType
    what_happened: str
    root_cause: dict[str, Any]
    recommended_actions: list[RecommendedAction]
    actions_allowed: list[dict[str, Any]]  # Actions that passed policy
    actions_blocked: list[dict[str, Any]]  # Actions blocked by policy
    safe_to_autofix: bool
    needs_human: list[dict[str, Any]]
    evidence_refs: list[str]
    created_at: datetime


class CoordinatorAgent:
    """Coordinator agent that orchestrates specialist agents and applies policy."""

    def __init__(self):
        """Initialize Coordinator Agent."""
        self.config = config
        self.policy_engine = get_policy_engine()
        self.incident_store = IncidentStore()
        self.evidence_store = EvidenceStore()

        # Initialize specialist agents
        self.pipeline_rca_agent = PipelineRCAAgent()

        # Budget tracking
        self.tool_call_count: int = 0
        self.max_tool_calls: int = 50  # Budget per incident
        self.start_time: Optional[datetime] = None

        logger.info("Initialized Coordinator Agent")

    def coordinate(
        self, event: PipelineFailureEvent | APIFailureEvent
    ) -> DecisionPacket:
        """Coordinate investigation and remediation for an event.

        Args:
            event: Event to process

        Returns:
            Decision packet with merged results
        """
        logger.info("Coordinating investigation for event: %s", event.event_type)
        self.start_time = datetime.utcnow()
        self.tool_call_count = 0

        # Step 1: Generate incident ID and check idempotency
        incident_id = self._generate_incident_id(event)
        if self.incident_store.exists(incident_id):
            logger.info("Incident already processed: %s", incident_id)
            # Return existing decision packet
            return self._load_existing_decision(incident_id)

        try:
            # Step 2: Select and activate specialist agents
            investigation_result = self._investigate(event)

            # Step 3: Extract recommended actions
            recommended_actions_raw = investigation_result.get("recommended_actions")
            recommended_actions = recommended_actions_raw if recommended_actions_raw is not None else []

            # Step 4: Apply policy to each action
            actions_allowed, actions_blocked = self._apply_policy(
                recommended_actions, event, investigation_result
            )

            # Step 5: Determine if safe to autofix
            safe_to_autofix = (
                investigation_result.get("safe_to_autofix", False)
                and len(actions_allowed) > 0
            )

            # Step 6: Build decision packet
            decision_packet = DecisionPacket(
                incident_id=incident_id,
                event_type=event.event_type,
                what_happened=investigation_result.get("what_happened", "Unknown"),
                root_cause={
                    "classification": investigation_result.get("classification"),
                    "confidence": investigation_result.get("confidence"),
                    "hypothesis": investigation_result.get("root_cause_hypothesis"),
                },
                recommended_actions=recommended_actions,
                actions_allowed=actions_allowed,
                actions_blocked=actions_blocked,
                safe_to_autofix=safe_to_autofix,
                needs_human=self._determine_human_needs(actions_blocked or [], investigation_result),
                evidence_refs=investigation_result.get("evidence_refs") or [],
                created_at=datetime.utcnow(),
            )

            # Step 7: Store decision packet
            self._store_decision(incident_id, decision_packet, event)

            logger.info(
                "Coordination complete: incident_id=%s, actions_allowed=%d, actions_blocked=%d",
                incident_id,
                len(actions_allowed),
                len(actions_blocked),
            )

            return decision_packet

        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # Handle expected errors (data validation, missing attributes, etc.)
            logger.error("Expected error during investigation: %s", e, exc_info=True)
            return DecisionPacket(
                incident_id=incident_id,
                event_type=event.event_type,
                what_happened=f"Error during investigation: {str(e)}",
                root_cause={"classification": "UNKNOWN", "confidence": 0.0, "hypothesis": str(e)},
                recommended_actions=[],
                actions_allowed=[],
                actions_blocked=[],
                safe_to_autofix=False,
                needs_human=[{"reason": "investigation_error", "error": str(e)}],
                evidence_refs=[],
                created_at=datetime.utcnow(),
            )
        except Exception as e:
            # Handle unexpected errors (log critically and re-raise for monitoring)
            logger.critical("Unexpected error during investigation: %s", e, exc_info=True)
            # Still return error decision packet to prevent complete failure
            return DecisionPacket(
                incident_id=incident_id,
                event_type=event.event_type,
                what_happened=f"Unexpected error during investigation: {str(e)}",
                root_cause={"classification": "UNKNOWN", "confidence": 0.0, "hypothesis": "Unexpected error occurred"},
                recommended_actions=[],
                actions_allowed=[],
                actions_blocked=[],
                safe_to_autofix=False,
                needs_human=[{"reason": "unexpected_error", "error": str(e)}],
                evidence_refs=[],
                created_at=datetime.utcnow(),
            )

    def _investigate(self, event: PipelineFailureEvent | APIFailureEvent) -> dict[str, Any]:
        """Investigate event using appropriate specialist agent.

        Args:
            event: Event to investigate

        Returns:
            Investigation result dictionary
        """
        if isinstance(event, PipelineFailureEvent):
            return self._investigate_pipeline_failure(event)
        elif isinstance(event, APIFailureEvent):
            return self._investigate_api_failure(event)
        else:
            logger.warning("Unknown event type: %s", event.event_type)
            return {
                "what_happened": f"Unknown event type: {event.event_type}",
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "root_cause_hypothesis": "Event type not supported",
                "recommended_actions": [],
                "safe_to_autofix": False,
                "evidence_refs": [],
            }

    def _investigate_pipeline_failure(
        self, event: PipelineFailureEvent
    ) -> dict[str, Any]:
        """Investigate pipeline failure using Pipeline RCA Agent.

        Args:
            event: Pipeline failure event

        Returns:
            Investigation result
        """
        logger.info("Activating Pipeline RCA Agent")
        rca_result: PipelineIncidentAnalysis = self.pipeline_rca_agent.investigate(event)

        # Extract evidence refs as S3 URIs
        evidence_refs = []
        if rca_result.evidence_refs is not None:
            for ref in rca_result.evidence_refs:
                if ref is not None:
                    evidence_refs.append(ref.to_uri())
        
        return {
            "what_happened": f"Pipeline failure: {event.execution_arn}",
            "classification": rca_result.classification.value,
            "confidence": rca_result.confidence.value,
            "root_cause_hypothesis": rca_result.root_cause_hypothesis,
            "recommended_actions": rca_result.recommended_actions,
            "safe_to_autofix": rca_result.safe_to_autofix,
            "evidence_refs": evidence_refs,
        }

    def _investigate_api_failure(self, event: APIFailureEvent) -> dict[str, Any]:
        """Investigate API failure (placeholder for Phase 0).

        Args:
            event: API failure event

        Returns:
            Investigation result
        """
        logger.warning("API failure investigation not yet implemented in Phase 0")
        return {
            "what_happened": f"API failure: {event.service_name}",
            "classification": "UNKNOWN",
            "confidence": 0.0,
            "root_cause_hypothesis": "API failure investigation not implemented",
            "recommended_actions": [],
            "safe_to_autofix": False,
            "evidence_refs": [],
        }

    def _apply_policy(
        self,
        recommended_actions: list[RecommendedAction],
        event: PipelineFailureEvent | APIFailureEvent,
        investigation_result: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Apply policy engine to recommended actions.

        Args:
            recommended_actions: List of recommended actions
            event: Original event
            investigation_result: Investigation result

        Returns:
            Tuple of (allowed_actions, blocked_actions)
        """
        allowed_actions = []
        blocked_actions = []

        # Ensure recommended_actions is a list, not None
        if recommended_actions is None:
            logger.warning("recommended_actions is None, using empty list")
            recommended_actions = []

        for action in recommended_actions:
            # Skip None actions
            if action is None:
                logger.warning("Skipping None action in recommended_actions")
                continue
            # Create remediation action for policy evaluation
            # Safely extract tier value (Tier is an Enum with .value attribute)
            tier_value = None
            if event.tier:
                if hasattr(event.tier, 'value'):
                    tier_value = event.tier.value
                else:
                    # Fallback: convert to string if it's already a string
                    tier_value = str(event.tier)
            
            # Safely extract action attributes
            action_type = action.action_type if action.action_type else "unknown"
            action_parameters = action.parameters if action.parameters is not None else {}
            
            remediation_action = RemediationAction(
                action_type=action_type,
                target=self._extract_target_from_action(action, event),
                parameters=action_parameters,
                tier=tier_value,
                context={
                    "event_type": event.event_type.value,
                    "classification": investigation_result.get("classification"),
                    "confidence": investigation_result.get("confidence"),
                },
            )

            # Evaluate policy
            decision: PolicyDecision = self.policy_engine.evaluate_action(remediation_action)

            action_dict = {
                "action_type": action_type,
                "description": action.description if action.description else "",
                "parameters": action_parameters,
                "recommended_action": action,  # Keep original action for remediation agent
                "policy_decision": {
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "requires_approval": decision.requires_approval,
                },
            }

            if decision.allowed:
                allowed_actions.append(action_dict)
                logger.info(
                    "Action allowed by policy: %s - %s", action.action_type, decision.reason
                )
            else:
                blocked_actions.append(action_dict)
                logger.warning(
                    "Action blocked by policy: %s - %s", action.action_type, decision.reason
                )

        return allowed_actions, blocked_actions

    def _extract_target_from_action(
        self, action: RecommendedAction, event: PipelineFailureEvent | APIFailureEvent
    ) -> str:
        """Extract target resource from action and event.

        Args:
            action: Recommended action
            event: Original event

        Returns:
            Target resource identifier
        """
        # Try to get target from action parameters
        if "target" in action.parameters:
            return action.parameters["target"]

        # Fallback to event resources
        if isinstance(event, PipelineFailureEvent):
            if event.execution_arn:
                return event.execution_arn.value
            elif event.state_machine_arn:
                return event.state_machine_arn.value
            elif event.glue_job_name:
                return event.glue_job_name
        elif isinstance(event, APIFailureEvent):
            return event.service_name

        return "unknown"

    def _determine_human_needs(
        self, blocked_actions: list[dict[str, Any]], investigation_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Determine what needs human intervention.

        Args:
            blocked_actions: Actions blocked by policy
            investigation_result: Investigation result

        Returns:
            List of human intervention needs
        """
        needs = []

        # Ensure blocked_actions is a list, not None
        if blocked_actions is None:
            blocked_actions = []

        # Add blocked actions that require approval
        for action in blocked_actions:
            # Skip None actions
            if action is None:
                continue
            if action.get("policy_decision", {}).get("requires_approval", False):
                needs.append({
                    "reason": "policy_blocked",
                    "action": action["action_type"],
                    "description": action["description"],
                    "policy_reason": action["policy_decision"]["reason"],
                })

        # Add high-risk classifications
        classification = investigation_result.get("classification")
        if classification in ["CODE_REGRESSION", "UNKNOWN"]:
            needs.append({
                "reason": "high_risk_classification",
                "classification": classification,
                "action": "manual_review",
            })

        return needs

    def _generate_incident_id(
        self, event: PipelineFailureEvent | APIFailureEvent
    ) -> str:
        """Generate unique incident ID from event.

        Args:
            event: Event

        Returns:
            Incident ID
        """
        if isinstance(event, PipelineFailureEvent) and event.execution_arn:
            arn_parts = event.execution_arn.value.split(":")
            execution_name = arn_parts[-1] if arn_parts else "unknown"
            return f"incident_{execution_name}_{event.timestamp.strftime('%Y%m%d%H%M%S')}"
        else:
            return f"incident_{event.event_id}"

    def _store_decision(
        self,
        incident_id: str,
        decision: DecisionPacket,
        event: PipelineFailureEvent | APIFailureEvent,
    ):
        """Store decision packet.

        Args:
            incident_id: Incident ID
            decision: Decision packet
            event: Original event
        """
        logger.info("Storing decision packet for incident: %s", incident_id)

        # Convert DecisionPacket to dictionary for storage
        decision_dict = decision.model_dump()

        # Store using incident store
        if isinstance(event, PipelineFailureEvent):
            self.incident_store.save_decision_packet(
                incident_id=incident_id,
                decision_packet=decision_dict,
                event=event,
            )
        else:
            # For API failure events, store without event (or convert if needed)
            self.incident_store.save_decision_packet(
                incident_id=incident_id,
                decision_packet=decision_dict,
                event=None,
            )

    def _load_existing_decision(self, incident_id: str) -> DecisionPacket:
        """Load existing decision packet.

        Args:
            incident_id: Incident ID

        Returns:
            Decision packet
        """
        logger.info("Loading existing decision packet for incident: %s", incident_id)

        # Load from incident store
        decision_dict = self.incident_store.load_decision_packet(incident_id)

        if decision_dict is None:
            logger.warning("Decision packet not found for %s, returning minimal packet", incident_id)
            # Return a minimal decision packet if not found
            return DecisionPacket(
                incident_id=incident_id,
                event_type=EventType.PIPELINE_FAILURE,
                what_happened="Incident already processed (decision packet not found)",
                root_cause={"classification": "UNKNOWN", "confidence": 0.0, "hypothesis": "Duplicate - packet not found"},
                recommended_actions=[],
                actions_allowed=[],
                actions_blocked=[],
                safe_to_autofix=False,
                needs_human=[],
                evidence_refs=[],
                created_at=datetime.utcnow(),
            )

        try:
            # Reconstruct DecisionPacket from dictionary
            # Handle datetime conversion if needed
            if "created_at" in decision_dict:
                if isinstance(decision_dict["created_at"], str):
                    # Parse ISO format datetime string
                    dt_str = decision_dict["created_at"]
                    if dt_str.endswith("Z"):
                        dt_str = dt_str.replace("Z", "+00:00")
                    decision_dict["created_at"] = datetime.fromisoformat(dt_str)
                elif isinstance(decision_dict["created_at"], dict):
                    # Handle if stored as dict (shouldn't happen, but be safe)
                    logger.warning("created_at is dict, converting: %s", decision_dict['created_at'])
                    decision_dict["created_at"] = datetime.utcnow()

            # Handle EventType enum conversion
            if "event_type" in decision_dict and isinstance(decision_dict["event_type"], str):
                decision_dict["event_type"] = EventType(decision_dict["event_type"])

            return DecisionPacket(**decision_dict)
        except (ValueError, KeyError, TypeError) as e:
            # Handle expected errors (missing fields, type mismatches, etc.)
            logger.error("Failed to reconstruct DecisionPacket from stored data: %s", e, exc_info=True)
            return DecisionPacket(
                incident_id=incident_id,
                event_type=EventType.PIPELINE_FAILURE,
                what_happened="Error loading existing decision packet",
                root_cause={"classification": "UNKNOWN", "confidence": 0.0, "hypothesis": f"Error: {str(e)}"},
                recommended_actions=[],
                actions_allowed=[],
                actions_blocked=[],
                safe_to_autofix=False,
                needs_human=[],
                evidence_refs=[],
                created_at=datetime.utcnow(),
            )
        except Exception as e:
            # Handle unexpected errors
            logger.critical("Unexpected error reconstructing DecisionPacket: %s", e, exc_info=True)
            return DecisionPacket(
                incident_id=incident_id,
                event_type=EventType.PIPELINE_FAILURE,
                what_happened="Unexpected error loading existing decision packet",
                root_cause={"classification": "UNKNOWN", "confidence": 0.0, "hypothesis": "Unexpected error occurred"},
                recommended_actions=[],
                actions_allowed=[],
                actions_blocked=[],
                safe_to_autofix=False,
                needs_human=[],
                evidence_refs=[],
                created_at=datetime.utcnow(),
            )
