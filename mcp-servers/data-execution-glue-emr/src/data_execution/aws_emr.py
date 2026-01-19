"""AWS EMR client wrapper."""

from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from data_execution.config import config
from data_execution.logging import get_logger

logger = get_logger(__name__)


class EMRClient:
    """Wrapper for AWS EMR boto3 client."""

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize EMR client.

        Args:
            region: AWS region (defaults to config)
            endpoint_url: AWS endpoint URL (for local testing)
        """
        self.region = region or config.aws_region
        self.endpoint_url = endpoint_url or config.aws_endpoint_url
        
        self.client = boto3.client(
            "emr",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        )
        logger.info(f"Initialized EMR client for region: {self.region}")

    def get_step(self, cluster_id: str, step_id: str) -> dict[str, Any]:
        """Get EMR step details.

        Args:
            cluster_id: EMR cluster ID
            step_id: Step ID

        Returns:
            Step details

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            response = self.client.describe_step(ClusterId=cluster_id, StepId=step_id)
            step = response.get("Step", {})
            
            status = step.get("Status", {})
            config = step.get("Config", {})
            
            logger.info(f"Retrieved step {step_id} for cluster {cluster_id}")
            
            return {
                "cluster_id": cluster_id,
                "step_id": step_id,
                "name": step.get("Name"),
                "state": status.get("State"),
                "state_change_reason": status.get("StateChangeReason", {}).get("Message"),
                "action_on_failure": step.get("ActionOnFailure"),
                "started_on": status.get("Timeline", {}).get("CreationDateTime"),
                "ended_on": status.get("Timeline", {}).get("EndDateTime"),
                "jar": config.get("Jar"),
                "main_class": config.get("MainClass"),
                "args": config.get("Args", []),
                "properties": config.get("Properties", {}),
            }

        except ClientError as e:
            logger.error(f"Failed to get EMR step: {e}")
            raise

    def list_steps(
        self,
        cluster_id: str,
        step_states: Optional[list[str]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> dict[str, Any]:
        """List EMR steps for a cluster.

        Args:
            cluster_id: EMR cluster ID
            step_states: Optional list of step states to filter (PENDING, RUNNING, COMPLETED, etc.)
            max_results: Maximum number of results
            marker: Pagination marker

        Returns:
            List of steps

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            params = {
                "ClusterId": cluster_id,
                "MaxResults": min(max_results, 1000),  # AWS limit
            }
            
            if step_states:
                params["StepStates"] = step_states
            
            if marker:
                params["Marker"] = marker

            response = self.client.list_steps(**params)
            
            steps = response.get("Steps", [])
            logger.info(f"Retrieved {len(steps)} steps for cluster {cluster_id}")
            
            return {
                "cluster_id": cluster_id,
                "steps": steps,
                "marker": response.get("Marker"),
            }

        except ClientError as e:
            logger.error(f"Failed to list EMR steps: {e}")
            raise

    def get_cluster(self, cluster_id: str) -> dict[str, Any]:
        """Get EMR cluster details.

        Args:
            cluster_id: EMR cluster ID

        Returns:
            Cluster details

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            response = self.client.describe_cluster(ClusterId=cluster_id)
            cluster = response.get("Cluster", {})
            status = cluster.get("Status", {})
            
            logger.info(f"Retrieved cluster details for {cluster_id}")
            
            return {
                "cluster_id": cluster_id,
                "name": cluster.get("Name"),
                "state": status.get("State"),
                "state_change_reason": status.get("StateChangeReason", {}).get("Message"),
                "release_label": cluster.get("ReleaseLabel"),
                "created_on": status.get("Timeline", {}).get("CreationDateTime"),
                "ready_on": status.get("Timeline", {}).get("ReadyDateTime"),
                "ended_on": status.get("Timeline", {}).get("EndDateTime"),
                "log_uri": cluster.get("LogUri"),
                "instance_count": cluster.get("InstanceCollectionType"),
            }

        except ClientError as e:
            logger.error(f"Failed to get EMR cluster: {e}")
            raise

    def get_log_groups_for_cluster(self, cluster_id: str) -> list[str]:
        """Get CloudWatch log groups associated with an EMR cluster.

        Args:
            cluster_id: EMR cluster ID

        Returns:
            List of log group names

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            cluster = self.get_cluster(cluster_id)
            log_uri = cluster.get("log_uri", "")
            
            log_groups = []
            
            # EMR typically uses S3 for logs, but also has CloudWatch integration
            # Standard EMR log groups
            log_groups.append(f"/aws/emr/{cluster_id}")
            log_groups.append(f"/aws/emr/{cluster_id}/containers")
            
            # If cluster has a name, also check by name
            cluster_name = cluster.get("name", "")
            if cluster_name:
                log_groups.append(f"/aws/emr/{cluster_name}")
            
            # Standard EMR log groups
            log_groups.append("/aws/emr/containers")
            
            # Remove duplicates and return
            unique_log_groups = list(set([lg for lg in log_groups if lg]))
            logger.info(f"Found {len(unique_log_groups)} log groups for cluster {cluster_id}")
            
            return unique_log_groups

        except ClientError as e:
            logger.error(f"Failed to get log groups for EMR cluster: {e}")
            raise


# Global EMR client instance
emr_client = EMRClient()
