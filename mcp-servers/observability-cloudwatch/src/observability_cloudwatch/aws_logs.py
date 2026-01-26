"""AWS CloudWatch Logs client wrapper."""

from datetime import datetime, timedelta
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from observability_cloudwatch.config import config
from observability_cloudwatch.logging import get_logger

logger = get_logger(__name__)


class CloudWatchLogsClient:
    """Wrapper for AWS CloudWatch Logs boto3 client."""

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize CloudWatch Logs client.

        Args:
            region: AWS region (defaults to config)
            endpoint_url: AWS endpoint URL (for local testing)
        """
        self.region = region or config.aws_region
        # Use provided endpoint_url, or from config, but convert empty string to None
        endpoint = endpoint_url or config.aws_endpoint_url
        self.endpoint_url = endpoint if endpoint and endpoint.strip() else None
        
        # Only pass endpoint_url if it's not None (boto3 doesn't accept empty strings)
        client_kwargs = {
            "service_name": "logs",
            "region_name": self.region,
        }
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        
        self.client = boto3.client(**client_kwargs)
        logger.info(f"Initialized CloudWatch Logs client for region: {self.region}")

    def query_logs_insights(
        self,
        log_groups: list[str],
        query: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Query CloudWatch Logs Insights.

        Args:
            log_groups: List of log group names
            query: CloudWatch Logs Insights query string
            start_time: Query start time
            end_time: Query end time
            limit: Maximum number of results

        Returns:
            Query results with fields and results

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            # Convert datetime to Unix timestamp (milliseconds)
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            response = self.client.start_query(
                logGroupNames=log_groups,
                startTime=start_ms,
                endTime=end_ms,
                queryString=query,
                limit=limit,
            )

            query_id = response["queryId"]
            logger.info(f"Started query {query_id} for {len(log_groups)} log groups")

            # Poll for results (with timeout)
            max_wait = 30  # seconds
            wait_interval = 1  # seconds
            elapsed = 0

            while elapsed < max_wait:
                result = self.client.get_query_results(queryId=query_id)
                status = result["status"]

                if status == "Complete":
                    logger.info(f"Query {query_id} completed with {len(result.get('results', []))} results")
                    return {
                        "query_id": query_id,
                        "status": status,
                        "statistics": result.get("statistics", {}),
                        "results": result.get("results", []),
                    }
                elif status == "Failed" or status == "Cancelled":
                    error_msg = result.get("statistics", {}).get("recordsScanned", 0)
                    logger.error(f"Query {query_id} {status.lower()}")
                    raise Exception(f"Query {status.lower()}: {error_msg}")

                # Wait before next poll
                import time
                time.sleep(wait_interval)
                elapsed += wait_interval

            # Timeout
            logger.warning(f"Query {query_id} timed out after {max_wait} seconds")
            raise Exception(f"Query timed out after {max_wait} seconds")

        except ClientError as e:
            logger.error(f"Failed to query logs: {e}")
            raise

    def get_log_events(
        self,
        log_group: str,
        log_stream: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        filter_pattern: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get log events from a log group/stream.

        Args:
            log_group: Log group name
            log_stream: Optional log stream name
            start_time: Optional start time
            end_time: Optional end time
            limit: Maximum number of events
            filter_pattern: Optional filter pattern

        Returns:
            Log events

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            params = {
                "logGroupName": log_group,
                "limit": min(limit, 10000),  # AWS limit
            }

            if log_stream:
                params["logStreamName"] = log_stream

            if start_time:
                params["startTime"] = int(start_time.timestamp() * 1000)

            if end_time:
                params["endTime"] = int(end_time.timestamp() * 1000)

            if filter_pattern:
                params["filterPattern"] = filter_pattern

            response = self.client.filter_log_events(**params)

            events = response.get("events", [])
            logger.info(f"Retrieved {len(events)} log events from {log_group}")

            return {
                "log_group": log_group,
                "events": events,
                "next_token": response.get("nextToken"),
            }

        except ClientError as e:
            logger.error(f"Failed to get log events: {e}")
            raise

    def extract_error_fingerprints(
        self, log_events: list[dict[str, Any]]
    ) -> list[str]:
        """Extract error fingerprints from log events.

        Args:
            log_events: List of log event dictionaries

        Returns:
            List of error fingerprints (exception names, error patterns)
        """
        import re

        fingerprints = set()

        for event in log_events:
            message = event.get("message", "")

            # Extract exception class names
            exception_pattern = r"(\w+Exception|\w+Error|\w+Failure)"
            exceptions = re.findall(exception_pattern, message, re.IGNORECASE)
            fingerprints.update(exceptions)

            # Extract common error patterns
            if "timeout" in message.lower():
                fingerprints.add("TIMEOUT")
            if "permission denied" in message.lower() or "access denied" in message.lower():
                fingerprints.add("PERMISSION_DENIED")
            if "connection refused" in message.lower():
                fingerprints.add("CONNECTION_REFUSED")
            if "out of memory" in message.lower() or "oom" in message.lower():
                fingerprints.add("OUT_OF_MEMORY")

        result = list(fingerprints)
        logger.info(f"Extracted {len(result)} error fingerprints")
        return result


# Global CloudWatch Logs client instance
logs_client = CloudWatchLogsClient()
