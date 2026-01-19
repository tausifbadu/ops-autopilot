# Policy Engine

The Policy Engine is the safety gatekeeper that controls what remediation actions the system can take. It prevents unauthorized or dangerous changes, especially to production resources.

## Overview

The Policy Engine:
- **Gates write actions** - Blocks or allows remediation actions based on rules
- **Enforces tier-based policies** - Different rules for prod vs nonprod
- **Prevents accidental changes** - Default deny, explicit allow
- **Provides audit trail** - Logs all policy decisions
- **Enables safe autonomy** - Allows automation with guardrails

## Architecture

```
Remediation Agent
    ↓
Policy Engine (evaluate_action)
    ↓
Policy Decision (allowed/denied)
    ↓
Action Executed (if allowed) OR Escalated (if denied)
```

## Components

### 1. Policy Engine (`engine.py`)

Main policy evaluation logic:
- Loads rules from YAML files
- Evaluates actions against tier-specific rules
- Checks rate limits and time windows
- Returns `PolicyDecision` with allow/deny result

### 2. Tier Detector (`tiers.py`)

Detects environment tier from:
- Resource names (e.g., "my-service-prod")
- AWS ARNs
- Resource tags (e.g., `{"tier": "prod"}`)

Tiers:
- `PROD` - Production (most restrictive)
- `STAGING` - Staging environment
- `DEV` - Development environment
- `NONPROD` - Generic nonprod
- `UNKNOWN` - Defaults to PROD for safety

### 3. Policy Rules (YAML files)

- `prod.yaml` - Production rules (default deny)
- `nonprod.yaml` - Nonprod rules (allow auto-remediation)
- `allowlists.yaml` - Resource allowlists and deny lists

## Usage

### Basic Usage

```python
from agent_host.policy import PolicyEngine, RemediationAction

# Initialize policy engine
policy_engine = PolicyEngine()

# Create remediation action
action = RemediationAction(
    action_type="restart_service",
    target="my-api-service-prod",
    context={"tags": {"tier": "prod"}}
)

# Evaluate action
decision = policy_engine.evaluate_action(action)

if decision.allowed:
    print(f"Action allowed: {decision.reason}")
    # Execute action
else:
    print(f"Action blocked: {decision.reason}")
    if decision.requires_approval:
        # Escalate to humans
        escalate_to_humans(action, decision)
```

### Integration with Remediation Agent

```python
from agent_host.policy import get_policy_engine, RemediationAction

class RemediationAgent:
    def __init__(self):
        self.policy_engine = get_policy_engine()
    
    def execute_remediation(self, plan: RemediationPlan):
        # Create action
        action = RemediationAction(
            action_type=plan.action_type,
            target=plan.target,
            context=plan.context
        )
        
        # Check policy
        decision = self.policy_engine.evaluate_action(action)
        
        if not decision.allowed:
            logger.warning(f"Remediation blocked: {decision.reason}")
            if decision.requires_approval:
                self._escalate(plan, decision)
            return
        
        # Execute action
        result = self._execute(action)
        
        # Log decision
        self.policy_engine.log_decision(action, decision)
        
        return result
```

## Policy Rules

### Production Rules (`prod.yaml`)

```yaml
tier: prod
auto_remediate: false
requires_approval: true

rules:
  - action: "read_only"
    allowed: true
  
  - action: "restart_service"
    allowed: false
    reason: "Production services should not be auto-restarted"
    requires_approval: true
  
  - action: "stop_execution"
    allowed: true
    reason: "Stopping executions is safe"
    conditions:
      - execution_time_minutes > 60
```

### Nonprod Rules (`nonprod.yaml`)

```yaml
tier: nonprod
auto_remediate: true
requires_approval: false

rules:
  - action: "restart_service"
    allowed: true
    conditions:
      - max_restarts_per_hour < 3
  
  - action: "retry_execution"
    allowed: true
    conditions:
      - retry_count < 3
```

## Policy Decision Flow

1. **Tier Detection** - Detect tier from resource name/ARN/tags
2. **Deny List Check** - Check global deny list (always blocks)
3. **Allowlist Check** - Check tier-specific allowlist (can override rules)
4. **Rule Evaluation** - Evaluate against tier-specific rules
5. **Rate Limit Check** - Check action rate limits
6. **Time Window Check** - Check time-based restrictions
7. **Return Decision** - Return allow/deny with reason

## Examples

### Example 1: Production Action Blocked

```python
action = RemediationAction(
    action_type="restart_service",
    target="api-service-prod",
    context={"tags": {"tier": "prod"}}
)

decision = policy_engine.evaluate_action(action)
# Result: PolicyDecision(
#   allowed=False,
#   reason="Production tier does not allow restart_service",
#   requires_approval=True,
#   tier="prod"
# )
```

### Example 2: Nonprod Action Allowed

```python
action = RemediationAction(
    action_type="retry_execution",
    target="pipeline-dev",
    context={"retry_count": 1, "tags": {"tier": "dev"}}
)

decision = policy_engine.evaluate_action(action)
# Result: PolicyDecision(
#   allowed=True,
#   reason="Nonprod tier allows retry_execution",
#   requires_approval=False,
#   tier="dev"
# )
```

### Example 3: Rate Limit Exceeded

```python
# After 3 restarts in 1 hour
action = RemediationAction(
    action_type="restart_service",
    target="service-dev",
    context={"tags": {"tier": "dev"}}
)

decision = policy_engine.evaluate_action(action)
# Result: PolicyDecision(
#   allowed=False,
#   reason="Rate limit exceeded: 3/3 actions per hour",
#   requires_approval=True,
#   tier="dev"
# )
```

## Configuration

### Environment Variables

- `POLICY_RULES_DIR` - Path to policy rules directory (default: `policy/rules/`)

### Rule File Location

By default, rules are loaded from:
- `agent-host/src/agent_host/policy/rules/prod.yaml`
- `agent-host/src/agent_host/policy/rules/nonprod.yaml`
- `agent-host/src/agent_host/policy/rules/allowlists.yaml`

## Safety Features

1. **Default Deny** - Production actions are denied by default
2. **Allowlist Override** - Explicit allowlist can override rules
3. **Deny List** - Global deny list blocks specific resources
4. **Rate Limiting** - Prevents action storms
5. **Time Windows** - Blocks actions during peak hours
6. **Audit Logging** - All decisions are logged

## Extending the Policy Engine

### Adding New Action Types

1. Add action type to rule files:
```yaml
- action: "new_action_type"
  allowed: true
  reason: "Description"
  conditions:
    - condition_key: expected_value
```

2. Use in remediation plans:
```python
action = RemediationAction(
    action_type="new_action_type",
    target="resource",
    context={"condition_key": "value"}
)
```

### Adding Custom Conditions

Extend `_evaluate_conditions()` method to support complex condition evaluation.

## Testing

```python
from agent_host.policy import PolicyEngine, RemediationAction, Tier

# Test production blocking
action = RemediationAction(
    action_type="restart_service",
    target="prod-service",
    tier="prod"
)
decision = policy_engine.evaluate_action(action)
assert decision.allowed == False
assert decision.requires_approval == True

# Test nonprod allowing
action = RemediationAction(
    action_type="retry_execution",
    target="dev-service",
    tier="dev"
)
decision = policy_engine.evaluate_action(action)
assert decision.allowed == True
```

## License

Part of the ops-autopilot project.
