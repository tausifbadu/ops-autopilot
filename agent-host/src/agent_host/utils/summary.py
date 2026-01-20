"""Utilities for formatting human-readable summaries."""

from datetime import datetime
from typing import Any, Optional

from agent_host.agents.coordinator import DecisionPacket
from agent_host.agents.remediation_agent import RemediationResult


def format_decision_summary(
    decision_packet: DecisionPacket,
    remediation_result: Optional[RemediationResult] = None,
    evidence_dir: Optional[str] = None,
) -> str:
    """Format DecisionPacket as a human-readable summary.

    Args:
        decision_packet: Decision packet from Coordinator
        remediation_result: Optional remediation result
        evidence_dir: Optional evidence directory path

    Returns:
        Formatted human-readable summary string
    """
    lines = []

    # Header
    lines.append("╔" + "═" * 70 + "╗")
    lines.append("║" + " " * 20 + "INCIDENT SUMMARY" + " " * 33 + "║")
    lines.append("╚" + "═" * 70 + "╝")
    lines.append("")

    # Basic Info
    lines.append(f"Incident ID: {decision_packet.incident_id}")
    lines.append(f"Event Type: {decision_packet.event_type.value}")
    lines.append(f"Timestamp: {decision_packet.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # What Happened
    lines.append("━" * 72)
    lines.append("WHAT HAPPENED")
    lines.append("━" * 72)
    lines.append(decision_packet.what_happened)
    lines.append("")

    # Root Cause Analysis
    lines.append("━" * 72)
    lines.append("ROOT CAUSE ANALYSIS")
    lines.append("━" * 72)
    classification = decision_packet.root_cause.get("classification", "UNKNOWN")
    confidence = decision_packet.root_cause.get("confidence", 0.0)
    hypothesis = decision_packet.root_cause.get("hypothesis", "No hypothesis available")

    # Format confidence as percentage
    confidence_pct = confidence * 100 if isinstance(confidence, float) else confidence
    confidence_label = _get_confidence_label(confidence)

    lines.append(f"Classification: {classification}")
    lines.append(f"Confidence: {confidence_label} ({confidence_pct:.0f}%)")
    lines.append("")
    lines.append("Hypothesis:")
    lines.append(_indent_text(hypothesis, 2))
    lines.append("")

    # Recommended Actions
    if decision_packet.recommended_actions:
        lines.append("━" * 72)
        lines.append("RECOMMENDED ACTIONS")
        lines.append("━" * 72)
        for i, action in enumerate(decision_packet.recommended_actions, 1):
            lines.append(f"{i}. {action.action_type}")
            if action.description:
                lines.append(_indent_text(f"Description: {action.description}", 3))
            if action.parameters:
                # Format parameters nicely
                params_str = _format_parameters(action.parameters)
                if params_str:
                    lines.append(_indent_text(f"Parameters: {params_str}", 3))
            lines.append("")
    else:
        lines.append("━" * 72)
        lines.append("RECOMMENDED ACTIONS")
        lines.append("━" * 72)
        lines.append("(none)")
        lines.append("")

    # Policy Evaluation
    lines.append("━" * 72)
    lines.append("POLICY EVALUATION")
    lines.append("━" * 72)

    # Detect tier from root cause or actions
    tier = decision_packet.root_cause.get("tier") or "unknown"
    if tier != "unknown":
        lines.append(f"Tier: {tier}")
        lines.append("")

    # Allowed Actions
    if decision_packet.actions_allowed:
        lines.append(f"✅ ALLOWED ACTIONS ({len(decision_packet.actions_allowed)}):")
        for action_dict in decision_packet.actions_allowed:
            action_type = action_dict.get("action_type", "unknown")
            description = action_dict.get("description", "")
            policy_reason = action_dict.get("policy_decision", {}).get("reason", "")
            lines.append(f"  • {action_type}")
            if description:
                lines.append(_indent_text(description, 4))
            if policy_reason:
                lines.append(_indent_text(f"Reason: {policy_reason}", 4))
        lines.append("")
    else:
        lines.append("✅ ALLOWED ACTIONS (0):")
        lines.append("  (none)")
        lines.append("")

    # Blocked Actions
    if decision_packet.actions_blocked:
        lines.append(f"❌ BLOCKED ACTIONS ({len(decision_packet.actions_blocked)}):")
        for action_dict in decision_packet.actions_blocked:
            action_type = action_dict.get("action_type", "unknown")
            description = action_dict.get("description", "")
            policy_reason = action_dict.get("policy_decision", {}).get("reason", "")
            lines.append(f"  • {action_type}")
            if description:
                lines.append(_indent_text(description, 4))
            if policy_reason:
                lines.append(_indent_text(f"Reason: {policy_reason}", 4))
        lines.append("")
    else:
        lines.append("❌ BLOCKED ACTIONS (0):")
        lines.append("  (none)")
        lines.append("")

    # Remediation Status
    lines.append("━" * 72)
    lines.append("REMEDIATION STATUS")
    lines.append("━" * 72)

    safe_icon = "✅" if decision_packet.safe_to_autofix else "❌"
    lines.append(f"{safe_icon} Safe to Autofix: {'YES' if decision_packet.safe_to_autofix else 'NO'}")

    if remediation_result:
        lines.append(f"{'✅' if remediation_result.success else '❌'} Actions Executed: {len(remediation_result.actions_taken)}")
        lines.append("")

        if remediation_result.actions_taken:
            lines.append("Executed Actions:")
            for action_result in remediation_result.actions_taken:
                action_type = action_result.get("action", "unknown")
                result_status = action_result.get("result", "unknown")
                details = action_result.get("details", {})
                lines.append(f"  ✓ {action_type}")
                if result_status != "success":
                    lines.append(_indent_text(f"Status: {result_status}", 4))
                if details:
                    # Format details nicely
                    details_str = _format_details(details)
                    if details_str:
                        lines.append(_indent_text(details_str, 4))
            lines.append("")

        if remediation_result.actions_failed:
            lines.append("Failed Actions:")
            for action_result in remediation_result.actions_failed:
                action_type = action_result.get("action", "unknown")
                reason = action_result.get("reason", "unknown")
                lines.append(f"  ✗ {action_type}")
                lines.append(_indent_text(f"Reason: {reason}", 4))
            lines.append("")

        if remediation_result.verification:
            lines.append("Verification:")
            verification = remediation_result.verification
            status = verification.get("status", "unknown")
            checks = verification.get("checks", [])
            lines.append(_indent_text(f"Status: {status}", 2))
            if checks:
                for check in checks:
                    execution_arn = check.get("execution_arn", "N/A")
                    check_status = check.get("status", "unknown")
                    verified = check.get("verified", False)
                    status_icon = "✓" if verified else "✗"
                    lines.append(_indent_text(f"{status_icon} {execution_arn}: {check_status}", 4))
            lines.append("")
    else:
        if decision_packet.safe_to_autofix and decision_packet.actions_allowed:
            lines.append("⚠️  Remediation was not executed (remediation result not available)")
        else:
            lines.append("ℹ️  No remediation executed")
        lines.append("")

    # Human Intervention Needed
    lines.append("━" * 72)
    lines.append("HUMAN INTERVENTION NEEDED")
    lines.append("━" * 72)
    if decision_packet.needs_human:
        for i, need in enumerate(decision_packet.needs_human, 1):
            reason = need.get("reason", "unknown")
            action = need.get("action", "")
            description = need.get("description", "")
            policy_reason = need.get("policy_reason", "")

            lines.append(f"{i}. {reason}")
            if action:
                lines.append(_indent_text(f"Action: {action}", 2))
            if description:
                lines.append(_indent_text(f"Description: {description}", 2))
            if policy_reason:
                lines.append(_indent_text(f"Policy Reason: {policy_reason}", 2))
            lines.append("")
    else:
        lines.append("(none) - All actions were automatically executed or no actions required")
        lines.append("")

    # Evidence
    lines.append("━" * 72)
    lines.append("EVIDENCE")
    lines.append("━" * 72)
    if evidence_dir:
        lines.append(f"Evidence saved to: {evidence_dir}")
    if decision_packet.evidence_refs:
        lines.append(f"Evidence references ({len(decision_packet.evidence_refs)}):")
        for ref in decision_packet.evidence_refs[:5]:  # Show first 5
            lines.append(f"  • {ref}")
        if len(decision_packet.evidence_refs) > 5:
            lines.append(f"  ... and {len(decision_packet.evidence_refs) - 5} more")
    else:
        lines.append("Evidence references: (none)")
    lines.append("")

    return "\n".join(lines)


def _get_confidence_label(confidence: float) -> str:
    """Get confidence label from numeric value."""
    if confidence >= 0.8:
        return "HIGH"
    elif confidence >= 0.5:
        return "MEDIUM"
    elif confidence >= 0.2:
        return "LOW"
    else:
        return "VERY LOW"


def _indent_text(text: str, indent: int) -> str:
    """Indent text by specified number of spaces, wrapping if needed."""
    indent_str = " " * indent
    # Simple wrapping at 70 characters (accounting for indent)
    max_width = 70 - indent
    words = text.split()
    lines = []
    current_line = indent_str

    for word in words:
        if len(current_line) + len(word) + 1 <= 70:
            if current_line.strip():
                current_line += " " + word
            else:
                current_line += word
        else:
            lines.append(current_line)
            current_line = indent_str + word

    if current_line.strip():
        lines.append(current_line)

    return "\n".join(lines)


def _format_parameters(params: dict[str, Any]) -> str:
    """Format parameters dictionary as a readable string."""
    if not params:
        return ""

    # Filter out None values and format nicely
    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return ""

    # Format as key=value pairs, truncate long values
    parts = []
    for k, v in list(filtered.items())[:3]:  # Show first 3 params
        if isinstance(v, str) and len(v) > 50:
            v = v[:47] + "..."
        parts.append(f"{k}={v}")

    if len(filtered) > 3:
        parts.append(f"... and {len(filtered) - 3} more")

    return ", ".join(parts)


def _format_details(details: dict[str, Any]) -> str:
    """Format details dictionary as a readable string."""
    if not details:
        return ""

    parts = []
    for k, v in details.items():
        if isinstance(v, str) and len(v) > 40:
            v = v[:37] + "..."
        parts.append(f"{k}: {v}")

    return ", ".join(parts)
