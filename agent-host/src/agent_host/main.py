"""Main entrypoint for Agent Host - handles SQS polling and local file processing."""

import argparse
import json
import sys
from pathlib import Path

from shared.schemas.events import Event, PipelineFailureEvent

from agent_host.config import config
from agent_host.dispatcher import Dispatcher
from agent_host.logging import get_logger

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
    else:
        logger.error(f"Unsupported event type for local processing: {event_type}")
        sys.exit(1)

    # Process event
    dispatcher = Dispatcher()
    incident_id = dispatcher.dispatch(event)

    if incident_id:
        logger.info(f"✅ Event processed successfully: incident_id={incident_id}")
        print(f"\n✅ Incident created: {incident_id}")
        print(f"📁 Evidence saved to: {config.local_evidence_dir}/")
    else:
        logger.warning("Event processing failed or was skipped")
        print("\n⚠️  Event processing failed or was skipped")
        sys.exit(1)


def process_sqs_messages():
    """Process events from SQS queue (AWS mode).

    This is a long-running process that polls SQS continuously.
    """
    import boto3
    import time

    logger.info("Starting SQS polling loop (AWS mode)")

    if not config.sqs_queue_incidents:
        logger.error("SQS queue URL not configured")
        sys.exit(1)

    sqs = boto3.client("sqs", region_name=config.aws_region)
    dispatcher = Dispatcher()

    logger.info(f"Polling SQS queue: {config.sqs_queue_incidents}")

    while True:
        try:
            # Receive messages from SQS
            response = sqs.receive_message(
                QueueUrl=config.sqs_queue_incidents,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling
            )

            messages = response.get("Messages", [])

            for message in messages:
                try:
                    # Parse event from message body
                    event_data = json.loads(message["Body"])
                    event_type = event_data.get("event_type", "PIPELINE_FAILURE")

                    # Create event object
                    if event_type == "PIPELINE_FAILURE":
                        event = PipelineFailureEvent(**event_data)
                    else:
                        logger.warning(f"Unsupported event type: {event_type}")
                        continue

                    # Process event
                    incident_id = dispatcher.dispatch(event)

                    if incident_id:
                        logger.info(f"Processed event: incident_id={incident_id}")

                    # Delete message from queue
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
