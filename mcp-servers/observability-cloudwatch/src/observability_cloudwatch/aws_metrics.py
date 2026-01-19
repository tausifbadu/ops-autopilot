"""AWS CloudWatch Metrics client wrapper."""

from datetime import datetime, timedelta
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from observability_cloudwatch.config import config
from observability_cloudwatch.logging import get_logger

logger = get_logger(__name__)


class CloudWatchMetricsClient:
    """Wrapper for AWS CloudWatch Metrics boto3 client."""

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize CloudWatch Metrics client.

        Args:
            region: AWS region (defaults to config)
            endpoint_url: AWS endpoint URL (for local testing)
        """
        self.region = region or config.aws_region
        self.endpoint_url = endpoint_url or config.aws_endpoint_url
        
        self.client = boto3.client(
            "cloudwatch",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        )
        logger.info(f"Initialized CloudWatch Metrics client for region: {self.region}")

    def get_metric_statistics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: Optional[list[dict[str, str]]] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        period: int = 300,
        statistics: list[str] = None,
        unit: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get CloudWatch metric statistics.

        Args:
            namespace: Metric namespace (e.g., "AWS/ECS", "AWS/Glue")
            metric_name: Metric name (e.g., "CPUUtilization", "MemoryUtilization")
            dimensions: Optional metric dimensions
            start_time: Start time for metric data
            end_time: End time for metric data
            period: Period in seconds (default: 300 = 5 minutes)
            statistics: List of statistics (e.g., ["Average", "Maximum", "Sum"])
            unit: Optional metric unit

        Returns:
            Metric statistics with datapoints

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            if start_time is None:
                start_time = datetime.utcnow() - timedelta(hours=1)
            if end_time is None:
                end_time = datetime.utcnow()
            if statistics is None:
                statistics = ["Average", "Maximum", "Minimum", "Sum"]

            params = {
                "Namespace": namespace,
                "MetricName": metric_name,
                "StartTime": start_time,
                "EndTime": end_time,
                "Period": period,
                "Statistics": statistics,
            }

            if dimensions:
                params["Dimensions"] = dimensions

            if unit:
                params["Unit"] = unit

            response = self.client.get_metric_statistics(**params)

            datapoints = response.get("Datapoints", [])
            # Sort by timestamp
            datapoints.sort(key=lambda x: x["Timestamp"])

            logger.info(
                f"Retrieved {len(datapoints)} datapoints for {namespace}/{metric_name}"
            )

            return {
                "namespace": namespace,
                "metric_name": metric_name,
                "label": response.get("Label", metric_name),
                "datapoints": datapoints,
            }

        except ClientError as e:
            logger.error(f"Failed to get metric statistics: {e}")
            raise

    def list_metrics(
        self,
        namespace: Optional[str] = None,
        metric_name: Optional[str] = None,
        dimensions: Optional[list[dict[str, str]]] = None,
    ) -> list[dict[str, Any]]:
        """List available CloudWatch metrics.

        Args:
            namespace: Optional namespace filter
            metric_name: Optional metric name filter
            dimensions: Optional dimension filters

        Returns:
            List of metrics

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            params = {}

            if namespace:
                params["Namespace"] = namespace

            if metric_name:
                params["MetricName"] = metric_name

            if dimensions:
                params["Dimensions"] = dimensions

            response = self.client.list_metrics(**params)

            metrics = response.get("Metrics", [])
            logger.info(f"Found {len(metrics)} metrics")

            return metrics

        except ClientError as e:
            logger.error(f"Failed to list metrics: {e}")
            raise


# Global CloudWatch Metrics client instance
metrics_client = CloudWatchMetricsClient()
