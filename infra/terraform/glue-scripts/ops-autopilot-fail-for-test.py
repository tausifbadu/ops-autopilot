# ops-autopilot Glue test job: fails on purpose to trigger EventBridge -> Lambda -> SQS
# Use this job in AWS Glue to verify the failure pipeline (Glue Job State Change -> EventBridge -> Lambda -> SQS).

import sys

print("ops-autopilot-fail-for-test: starting (will fail intentionally)")
raise RuntimeError("Intentional failure for ops-autopilot EventBridge/Lambda/SQS test")
