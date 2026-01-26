"""Policy Engine for evaluating remediation actions."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from agent_host.logging import get_logger
from agent_host.policy.tiers import Tier, TierDetector

logger = get_logger(__name__)


class PolicyDecision(BaseModel):
    """Policy evaluation decision."""

    allowed: bool = Field(..., description="Whether action is allowed")
    reason: str = Field(..., description="Reason for decision")
    requires_approval: bool = Field(
        default=False, description="Whether human approval is required"
    )
    tier: Optional[str] = Field(None, description="Detected tier")
    escalation_channel: Optional[str] = Field(
        None, description="Channel for escalation if blocked"
    )


class RemediationAction(BaseModel):
    """A remediation action to evaluate."""

    action_type: str = Field(..., description="Action type (e.g., 'restart_service')")
    target: str = Field(..., description="Target resource (ARN, name, etc.)")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    tier: Optional[str] = Field(None, description="Explicit tier (if known)")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for evaluation"
    )


class PolicyEngine:
    """Policy evaluation engine."""

    def __init__(self, rules_dir: Optional[Path] = None):
        """Initialize Policy Engine.

        Args:
            rules_dir: Directory containing policy rule YAML files
        """
        if rules_dir is None:
            # Default to policy/rules directory
            rules_dir = Path(__file__).parent / "rules"

        self.rules_dir = rules_dir
        self.tier_detector = TierDetector()
        self.prod_rules: dict[str, Any] = {}
        self.nonprod_rules: dict[str, Any] = {}
        self.allowlists: dict[str, Any] = {}
        self.rate_limit_tracker: dict[str, list[datetime]] = {}

        self._load_rules()

    def _load_rules(self):
        """Load policy rules from YAML files."""
        try:
            # Load production rules
            prod_file = self.rules_dir / "prod.yaml"
            if prod_file.exists():
                with open(prod_file) as f:
                    self.prod_rules = yaml.safe_load(f) or {}
                logger.info("Loaded production policy rules")

            # Load nonprod rules
            nonprod_file = self.rules_dir / "nonprod.yaml"
            if nonprod_file.exists():
                with open(nonprod_file) as f:
                    self.nonprod_rules = yaml.safe_load(f) or {}
                logger.info("Loaded nonprod policy rules")

            # Load allowlists
            allowlist_file = self.rules_dir / "allowlists.yaml"
            if allowlist_file.exists():
                with open(allowlist_file) as f:
                    self.allowlists = yaml.safe_load(f) or {}
                logger.info("Loaded policy allowlists")

        except Exception as e:
            logger.error(f"Failed to load policy rules: {e}", exc_info=True)
            # Use default conservative rules
            self._load_default_rules()

    def _load_default_rules(self):
        """Load default conservative rules if YAML files fail."""
        logger.warning("Using default conservative policy rules")
        self.prod_rules = {
            "auto_remediate": False,
            "requires_approval": True,
            "rules": [
                {"action": "read_only", "allowed": True},
                {"action": "*", "allowed": False, "reason": "Default deny for production"},
            ],
        }
        self.nonprod_rules = {
            "auto_remediate": True,
            "requires_approval": False,
            "rules": [
                {"action": "read_only", "allowed": True},
                {"action": "delete", "allowed": False, "always_deny": True},
            ],
        }

    def evaluate_action(self, action: RemediationAction) -> PolicyDecision:
        """Evaluate if a remediation action is allowed.

        Args:
            action: Remediation action to evaluate

        Returns:
            Policy decision
        """
        logger.info(f"Evaluating action: {action.action_type} on {action.target}")

        # Step 1: Detect tier
        tier = self._detect_tier(action)

        # Step 2: Check deny list (global, regardless of tier)
        if self._is_in_deny_list(action.target):
            return PolicyDecision(
                allowed=False,
                reason=f"Target {action.target} is in global deny list",
                requires_approval=True,
                tier=tier.value if isinstance(tier, Tier) else str(tier),
            )

        # Step 3: Check allowlist (can override tier rules)
        if self._is_in_allowlist(action.target, tier):
            logger.info(f"Target {action.target} is in allowlist, allowing action")
            return PolicyDecision(
                allowed=True,
                reason=f"Target is in allowlist for tier {tier}",
                requires_approval=False,
                tier=tier.value if isinstance(tier, Tier) else str(tier),
            )

        # Step 4: Load tier-specific rules
        rules = self._get_rules_for_tier(tier)

        # Step 5: Evaluate action against rules
        decision = self._evaluate_against_rules(action, rules, tier)

        # Step 6: Check rate limits
        if decision.allowed:
            rate_limit_check = self._check_rate_limits(action, rules)
            if not rate_limit_check["allowed"]:
                decision.allowed = False
                decision.reason = rate_limit_check["reason"]
                decision.requires_approval = True

        # Step 7: Check time windows
        if decision.allowed:
            time_window_check = self._check_time_windows(action, rules)
            if not time_window_check["allowed"]:
                decision.allowed = False
                decision.reason = time_window_check["reason"]
                decision.requires_approval = True

        logger.info(
            f"Policy decision: allowed={decision.allowed}, reason={decision.reason}"
        )

        return decision

    def _detect_tier(self, action: RemediationAction) -> Tier:
        """Detect tier from action context.

        Args:
            action: Remediation action

        Returns:
            Detected tier
        """
        # Use explicit tier if provided
        if action.tier:
            try:
                return Tier(action.tier.lower())
            except ValueError:
                logger.warning(f"Invalid tier: {action.tier}, detecting from context")

        # Detect from target (ARN or name)
        tier = self.tier_detector.detect(
            name=action.target if not action.target.startswith("arn:") else None,
            arn=action.target if action.target.startswith("arn:") else None,
            tags=action.context.get("tags"),
        )

        # If still unknown, default to PROD for safety
        if tier == Tier.UNKNOWN:
            logger.warning(
                f"Could not detect tier for {action.target}, defaulting to PROD for safety"
            )
            return Tier.PROD

        return tier

    def _get_rules_for_tier(self, tier: Tier) -> dict[str, Any]:
        """Get policy rules for tier.

        Args:
            tier: Environment tier

        Returns:
            Policy rules dictionary
        """
        if tier == Tier.PROD:
            return self.prod_rules
        elif tier in [Tier.DEV, Tier.STAGING, Tier.NONPROD]:
            return self.nonprod_rules
        else:
            # Unknown tier - use conservative prod rules
            logger.warning(f"Unknown tier {tier}, using conservative prod rules")
            return self.prod_rules

    def _evaluate_against_rules(
        self, action: RemediationAction, rules: dict[str, Any], tier: Tier
    ) -> PolicyDecision:
        """Evaluate action against tier rules.

        Args:
            action: Remediation action
            rules: Tier-specific rules
            tier: Environment tier

        Returns:
            Policy decision
        """
        # Check if tier allows auto-remediation at all
        auto_remediate = rules.get("auto_remediate", False)
        requires_approval_default = rules.get("requires_approval", True)

        # If tier doesn't allow auto-remediation, deny unless explicitly allowed
        if not auto_remediate and tier == Tier.PROD:
            # Check if specific action is allowed
            action_rules = rules.get("rules", [])
            for rule in action_rules:
                if rule.get("action") == action.action_type:
                    if rule.get("always_deny", False):
                        return PolicyDecision(
                            allowed=False,
                            reason=rule.get("reason", "Action is always denied"),
                            requires_approval=True,
                            tier=tier.value,
                        )

                    if rule.get("allowed", False):
                        # Check conditions if any
                        conditions = rule.get("conditions", [])
                        if self._evaluate_conditions(conditions, action):
                            return PolicyDecision(
                                allowed=True,
                                reason=rule.get("reason", "Action allowed by rule"),
                                requires_approval=rule.get(
                                    "requires_approval", requires_approval_default
                                ),
                                tier=tier.value,
                            )

            # No specific rule found, default deny for prod
            return PolicyDecision(
                allowed=False,
                reason=f"Production tier does not allow {action.action_type}",
                requires_approval=True,
                tier=tier.value,
            )

        # Nonprod: Check rules but default to allow
        action_rules = rules.get("rules", [])
        for rule in action_rules:
            if rule.get("action") == action.action_type:
                if rule.get("always_deny", False):
                    return PolicyDecision(
                        allowed=False,
                        reason=rule.get("reason", "Action is always denied"),
                        requires_approval=True,
                        tier=tier.value,
                    )

                if rule.get("allowed", True):  # Default to True in nonprod
                    conditions = rule.get("conditions", [])
                    if self._evaluate_conditions(conditions, action):
                        return PolicyDecision(
                            allowed=True,
                            reason=rule.get("reason", "Action allowed"),
                            requires_approval=rule.get(
                                "requires_approval", requires_approval_default
                            ),
                            tier=tier.value,
                        )

        # Default: Allow in nonprod, deny in prod
        if tier == Tier.PROD:
            return PolicyDecision(
                allowed=False,
                reason=f"Production tier does not allow {action.action_type}",
                requires_approval=True,
                tier=tier.value,
            )
        else:
            return PolicyDecision(
                allowed=True,
                reason=f"Nonprod tier allows {action.action_type}",
                requires_approval=False,
                tier=tier.value,
            )

    def _evaluate_conditions(
        self, conditions: list[Any], action: RemediationAction
    ) -> bool:
        """Evaluate rule conditions.

        Args:
            conditions: List of condition dictionaries or strings
            action: Remediation action

        Returns:
            True if all conditions are met (or if no conditions)
        """
        if not conditions:
            return True

        context = action.context

        for condition in conditions:
            # If condition is a dict, evaluate it
            if isinstance(condition, dict):
                # Check if condition is met based on context values
                for key, expected_value in condition.items():
                    actual_value = context.get(key)
                    if actual_value is None:
                        return False
                    # Simple comparison (can be enhanced)
                    if actual_value != expected_value:
                        return False
            # If condition is a string, treat as simple key check
            elif isinstance(condition, str):
                # For MVP, check if key exists in context with truthy value
                if condition not in context or not context[condition]:
                    return False

        return True

    def _check_rate_limits(
        self, action: RemediationAction, rules: dict[str, Any]
    ) -> dict[str, Any]:
        """Check rate limits for action.

        Args:
            action: Remediation action
            rules: Tier-specific rules

        Returns:
            Rate limit check result
        """
        rate_limits = rules.get("rate_limits", {})
        action_limits = rate_limits.get(action.action_type, {})

        if not action_limits:
            return {"allowed": True}

        # Track action timestamps
        key = f"{action.action_type}:{action.target}"
        now = datetime.utcnow()

        if key not in self.rate_limit_tracker:
            self.rate_limit_tracker[key] = []

        # Clean old timestamps (older than 24 hours)
        cutoff = now - timedelta(hours=24)
        self.rate_limit_tracker[key] = [
            ts for ts in self.rate_limit_tracker[key] if ts > cutoff
        ]

        # Check hourly limit
        hourly_cutoff = now - timedelta(hours=1)
        hourly_count = sum(1 for ts in self.rate_limit_tracker[key] if ts > hourly_cutoff)

        max_per_hour = action_limits.get("max_per_hour")
        if max_per_hour and hourly_count >= max_per_hour:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded: {hourly_count}/{max_per_hour} actions per hour",
            }

        # Check daily limit
        daily_count = len(self.rate_limit_tracker[key])
        max_per_day = action_limits.get("max_per_day")
        if max_per_day and daily_count >= max_per_day:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded: {daily_count}/{max_per_day} actions per day",
            }

        # Record this action
        self.rate_limit_tracker[key].append(now)

        return {"allowed": True}

    def _check_time_windows(
        self, action: RemediationAction, rules: dict[str, Any]
    ) -> dict[str, Any]:
        """Check time window restrictions.

        Args:
            action: Remediation action
            rules: Tier-specific rules

        Returns:
            Time window check result
        """
        time_windows = rules.get("time_windows", {})
        if not time_windows:
            return {"allowed": True}

        # Check peak hours restriction
        peak_hours = time_windows.get("peak_hours", {})
        if peak_hours:
            now = datetime.utcnow()
            current_hour = now.hour

            start_str = peak_hours.get("start", "09:00")
            end_str = peak_hours.get("end", "17:00")

            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])

            if start_hour <= current_hour < end_hour:
                # In peak hours
                blocked_actions = peak_hours.get("blocked_actions", [])
                if action.action_type in blocked_actions:
                    return {
                        "allowed": False,
                        "reason": f"Action {action.action_type} is blocked during peak hours ({start_str}-{end_str})",
                    }

                allowed_actions = peak_hours.get("allowed_actions", [])
                if action.action_type not in allowed_actions:
                    return {
                        "allowed": False,
                        "reason": f"Action {action.action_type} is blocked during peak hours",
                    }

        return {"allowed": True}

    def _is_in_allowlist(self, target: str, tier: Tier) -> bool:
        """Check if target is in allowlist.

        Args:
            target: Target resource
            tier: Environment tier

        Returns:
            True if in allowlist
        """
        tier_key = "prod" if tier == Tier.PROD else "nonprod"
        allowlist = self.allowlists.get(tier_key, {})

        # Check state machines
        state_machines = allowlist.get("state_machines")
        if state_machines is None:
            state_machines = []
        elif not isinstance(state_machines, list):
            logger.warning(f"state_machines in allowlist is not a list: {type(state_machines)}")
            state_machines = []
        
        if state_machines and any(target.startswith(sm) or sm in target for sm in state_machines):
            return True

        # Check services
        services = allowlist.get("services", [])
        if target in services or any(svc in target for svc in services):
            return True

        # Check executions
        executions = allowlist.get("executions", [])
        if target in executions or any(exec in target for exec in executions):
            return True

        return False

    def _is_in_deny_list(self, target: str) -> bool:
        """Check if target is in global deny list.

        Args:
            target: Target resource

        Returns:
            True if in deny list
        """
        deny_list = self.allowlists.get("deny_list", {})
        if deny_list is None:
            deny_list = {}

        # Check state machines
        state_machines = deny_list.get("state_machines")
        if state_machines is None:
            state_machines = []
        elif not isinstance(state_machines, list):
            logger.warning(f"state_machines in deny_list is not a list: {type(state_machines)}")
            state_machines = []
        
        if state_machines and any(target.startswith(sm) or sm in target for sm in state_machines):
            return True

        # Check services
        services = deny_list.get("services")
        if services is None:
            services = []
        elif not isinstance(services, list):
            logger.warning(f"services in deny_list is not a list: {type(services)}")
            services = []
        
        if services and (target in services or any(svc in target for svc in services)):
            return True

        return False

    def log_decision(self, action: RemediationAction, decision: PolicyDecision):
        """Log policy decision for audit trail.

        Args:
            action: Remediation action
            decision: Policy decision
        """
        logger.info(
            f"Policy decision logged: action={action.action_type}, "
            f"target={action.target}, allowed={decision.allowed}, "
            f"reason={decision.reason}, tier={decision.tier}"
        )
        # In production, this would write to DynamoDB or CloudWatch Logs


# Global policy engine instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get global policy engine instance.

    Returns:
        Policy engine instance
    """
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
