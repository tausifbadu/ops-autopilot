"""Main entrypoint for Agent Host - handles SQS polling and local file processing."""

import argparse
import json
import sys
from pathlib import Path

from agent_host.config import config
from agent_host.dispatcher import Dispatcher
from agent_host.health_server import start_health_server
from agent_host.logging import get_logger
from shared.schemas.events import APIFailureEvent, PipelineFailureEvent

logger = get_logger(__name__)


def process_local_event(event_file: str):
    """Process a single event from a local file.

    Args:
        event_file: Path to event JSON file
    """
    logger.info(f"Processing local event file: {event_file}")

    # Load event from file
    event_path = Path(event_file)
    if not event_path.exists():
        logger.error(f"Event file not found: {event_file}")
        sys.exit(1)

    with open(event_path, "r") as f:
        event_data = json.load(f)

    # Parse event based on type
    event_type = event_data.get("event_type", "PIPELINE_FAILURE")
    
    if event_type == "PIPELINE_FAILURE":
        event = PipelineFailureEvent(**event_data)
    elif event_type == "API_FAILURE":
        event = APIFailureEvent(**event_data)
    else:
        logger.error(f"Unsupported event type for local processing: {event_type}")
        sys.exit(1)

    # Process event
    dispatcher = Dispatcher()
    result = dispatcher.dispatch(event)

    if result and result.success:
        logger.info(f"✅ Event processed successfully: incident_id={result.incident_id}")
        
        # Print human-readable summary if decision packet is available
        if result.decision_packet:
            from agent_host.utils.summary import format_decision_summary
            
            summary = format_decision_summary(
                decision_packet=result.decision_packet,
                remediation_result=result.remediation_result,
                evidence_dir=config.local_evidence_dir,
            )
            print("\n" + summary)
        else:
            # Fallback to simple message if no decision packet
            print(f"\n✅ Incident created: {result.incident_id}")
            print(f"📁 Evidence saved to: {config.local_evidence_dir}/")
    else:
        logger.warning("Event processing failed or was skipped")
        if result:
            print(f"\n⚠️  Event processing failed or was skipped: {result.reason}")
        else:
            print("\n⚠️  Event processing failed or was skipped")
        sys.exit(1)


def process_sqs_messages():
    """Process events from SQS queue (AWS mode).

    This is a long-running process that polls SQS continuously.
    """
    import os

    import boto3
    import time

    from botocore.exceptions import ClientError

    logger.info("Starting SQS polling loop (AWS mode)")

    # ECS health check expects GET /health on port 8000; without this, tasks are marked unhealthy and restarted
    start_health_server()

    if not config.sqs_queue_incidents:
        logger.error("SQS queue URL not configured")
        sys.exit(1)

    # Debug: log what AWS credentials/env the process sees (no secret values)
    _profile = os.environ.get("AWS_PROFILE", "")
    _has_ak = "set" if os.environ.get("AWS_ACCESS_KEY_ID") else "unset"
    _has_sk = "set" if os.environ.get("AWS_SECRET_ACCESS_KEY") else "unset"
    _has_token = "set" if os.environ.get("AWS_SESSION_TOKEN") else "unset"
    logger.info(
        "AWS env (this process): AWS_PROFILE=%s AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s AWS_SESSION_TOKEN=%s",
        repr(_profile) or "(not set)",
        _has_ak,
        _has_sk,
        _has_token,
    )
    try:
        sts = boto3.client("sts", region_name=config.aws_region)
        identity = sts.get_caller_identity()
        logger.info(
            "STS get_caller_identity: Account=%s Arn=%s",
            identity.get("Account"),
            identity.get("Arn"),
        )
    except Exception as e:
        logger.warning("STS get_caller_identity failed (credentials may be expired): %s", e)

    _llm_env = os.environ.get("LLM_PROVIDER", "")
    logger.info(
        "LLM: LLM_PROVIDER env=%s, resolved provider=%s (use openai in tfvars + redeploy if you want OpenAI)",
        repr(_llm_env) if _llm_env else "(not set)",
        config.llm_provider,
    )

    sqs = boto3.client("sqs", region_name=config.aws_region)
    dispatcher = Dispatcher()

    logger.info(f"Polling SQS queue: {config.sqs_queue_incidents} (long poll 20s when idle)")

    while True:
        try:
            # Receive messages from SQS (blocks up to WaitTimeSeconds when queue is empty)
            response = sqs.receive_message(
                QueueUrl=config.sqs_queue_incidents,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling
            )

            messages = response.get("Messages", [])
            if not messages:
                logger.info("Queue empty, waiting for messages (next poll in ~20s).")

            if messages:
                logger.info("Received %d message(s) from SQS", len(messages))

            for message in messages:
                try:
                    # Parse event from message body
                    event_data = json.loads(message["Body"])
                    event_type = event_data.get("event_type", "PIPELINE_FAILURE")

                    # Create event object
                    if event_type == "PIPELINE_FAILURE":
                        event = PipelineFailureEvent(**event_data)
                    elif event_type == "API_FAILURE":
                        event = APIFailureEvent(**event_data)
                    else:
                        logger.warning(f"Unsupported event type: {event_type}")
                        continue

                    # Process event
                    result = dispatcher.dispatch(event)

                    if result and result.success:
                        logger.info(f"Processed event: incident_id={result.incident_id}")
                    elif result:
                        logger.warning(f"Event processed but not successful: {result.reason}")

                    # Delete message from queue (so we don't reprocess; failed handling can go to DLQ via visibility timeout)
                    sqs.delete_message(
                        QueueUrl=config.sqs_queue_incidents,
                        ReceiptHandle=message["ReceiptHandle"],
                    )

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    # Message will be retried or sent to DLQ

        except KeyboardInterrupt:
            logger.info("Shutting down SQS polling loop")
            break
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ExpiredToken":
                # Stale keys in env (e.g. from .env). Clear so boto3 uses default chain (profile).
                for _k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
                    os.environ.pop(_k, None)
                logger.warning(
                    "ExpiredToken: cleared credential env vars; next poll will use default credential chain (e.g. AWS_PROFILE). "
                    "Update .env or re-export keys to use keys directly."
                )
                sqs = boto3.client("sqs", region_name=config.aws_region)
                # Continue loop without sleep so we retry immediately with new client
            else:
                logger.error(f"Error in SQS polling loop: {e}", exc_info=True)
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error in SQS polling loop: {e}", exc_info=True)
            time.sleep(5)  # Wait before retrying


def main():
    """Main entrypoint."""
    parser = argparse.ArgumentParser(description="Ops AutoPilot Agent Host")
    parser.add_argument(
        "--local-file",
        type=str,
        help="Process a single event from a local JSON file (local mode)",
    )
    parser.add_argument(
        "--sqs",
        action="store_true",
        help="Process events from SQS queue (AWS mode)",
    )

    args = parser.parse_args()

    logger.info(f"Starting Agent Host (environment: {config.environment})")

    if args.local_file:
        # Local mode: process single event file
        process_local_event(args.local_file)
    elif args.sqs or config.is_aws_mode():
        # AWS mode: poll SQS continuously
        process_sqs_messages()
    else:
        logger.error("No mode specified. Use --local-file or --sqs")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
