"""Tier detection and definitions for policy evaluation."""

import re
from enum import Enum
from typing import Optional

from agent_host.logging import get_logger

logger = get_logger(__name__)


class Tier(str, Enum):
    """Environment tier definitions."""

    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"
    NONPROD = "nonprod"  # Generic nonprod (dev, staging, test, etc.)
    UNKNOWN = "unknown"


class TierDetector:
    """Detects tier from resource names, tags, or ARNs."""

    # Tier patterns (case-insensitive)
    PROD_PATTERNS = [
        r"prod",
        r"production",
        r"prd",
        r"live",
    ]

    STAGING_PATTERNS = [
        r"staging",
        r"stage",
        r"stg",
        r"preprod",
    ]

    DEV_PATTERNS = [
        r"dev",
        r"development",
        r"test",
        r"testing",
        r"qa",
        r"local",
    ]

    @classmethod
    def detect_from_name(cls, name: str) -> Tier:
        """Detect tier from resource name.

        Args:
            name: Resource name (e.g., "my-service-prod", "pipeline-dev")

        Returns:
            Detected tier
        """
        if not name:
            return Tier.UNKNOWN

        name_lower = name.lower()

        # Check prod patterns
        for pattern in cls.PROD_PATTERNS:
            if re.search(pattern, name_lower):
                logger.debug(f"Detected PROD tier from name: {name}")
                return Tier.PROD

        # Check staging patterns
        for pattern in cls.STAGING_PATTERNS:
            if re.search(pattern, name_lower):
                logger.debug(f"Detected STAGING tier from name: {name}")
                return Tier.STAGING

        # Check dev patterns
        for pattern in cls.DEV_PATTERNS:
            if re.search(pattern, name_lower):
                logger.debug(f"Detected DEV tier from name: {name}")
                return Tier.DEV

        # Default to unknown if no pattern matches
        logger.debug(f"Could not detect tier from name: {name}, defaulting to UNKNOWN")
        return Tier.UNKNOWN

    @classmethod
    def detect_from_arn(cls, arn: str) -> Tier:
        """Detect tier from AWS ARN.

        Args:
            arn: AWS resource ARN

        Returns:
            Detected tier
        """
        if not arn:
            return Tier.UNKNOWN

        # Extract resource name from ARN (last part after /)
        parts = arn.split("/")
        if len(parts) > 1:
            resource_name = parts[-1]
            return cls.detect_from_name(resource_name)

        # Try to detect from ARN itself
        return cls.detect_from_name(arn)

    @classmethod
    def detect_from_tags(cls, tags: dict[str, str]) -> Optional[Tier]:
        """Detect tier from resource tags.

        Args:
            tags: Resource tags dictionary

        Returns:
            Detected tier or None if not found
        """
        if not tags:
            return None

        # Check common tag keys
        tier_tag_keys = ["tier", "environment", "env", "stage", "stage_name"]

        for key in tier_tag_keys:
            if key in tags:
                tier_value = tags[key].lower()
                
                if tier_value in ["prod", "production", "prd", "live"]:
                    return Tier.PROD
                elif tier_value in ["staging", "stage", "stg", "preprod"]:
                    return Tier.STAGING
                elif tier_value in ["dev", "development", "test", "testing", "qa"]:
                    return Tier.DEV

        return None

    @classmethod
    def detect(
        self,
        name: Optional[str] = None,
        arn: Optional[str] = None,
        tags: Optional[dict[str, str]] = None,
    ) -> Tier:
        """Detect tier from multiple sources (priority: tags > name > arn).

        Args:
            name: Resource name
            arn: AWS resource ARN
            tags: Resource tags

        Returns:
            Detected tier
        """
        # Priority 1: Tags (most reliable)
        if tags:
            tier = self.detect_from_tags(tags)
            if tier:
                logger.debug(f"Detected tier {tier} from tags")
                return tier

        # Priority 2: Name
        if name:
            tier = self.detect_from_name(name)
            if tier != Tier.UNKNOWN:
                logger.debug(f"Detected tier {tier} from name: {name}")
                return tier

        # Priority 3: ARN
        if arn:
            tier = self.detect_from_arn(arn)
            if tier != Tier.UNKNOWN:
                logger.debug(f"Detected tier {tier} from ARN: {arn}")
                return tier

        # Default to UNKNOWN (will be treated conservatively)
        logger.warning("Could not detect tier, defaulting to UNKNOWN (will be treated as PROD for safety)")
        return Tier.UNKNOWN

    @classmethod
    def is_prod(cls, tier: Tier) -> bool:
        """Check if tier is production.

        Args:
            tier: Tier to check

        Returns:
            True if production tier
        """
        return tier == Tier.PROD

    @classmethod
    def is_nonprod(cls, tier: Tier) -> bool:
        """Check if tier is non-production.

        Args:
            tier: Tier to check

        Returns:
            True if non-production tier
        """
        return tier in [Tier.DEV, Tier.STAGING, Tier.NONPROD]
