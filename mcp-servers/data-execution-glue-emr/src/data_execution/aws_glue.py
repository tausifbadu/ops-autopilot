"""AWS Glue client wrapper."""

from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from data_execution.config import config
from data_execution.logging import get_logger

logger = get_logger(__name__)


class GlueClient:
    """Wrapper for AWS Glue boto3 client."""

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize Glue client.

        Args:
            region: AWS region (defaults to config)
            endpoint_url: AWS endpoint URL (for local testing)
        """
        self.region = region or config.aws_region
        self.endpoint_url = endpoint_url or config.aws_endpoint_url
        
        self.client = boto3.client(
            "glue",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        )
        logger.info(f"Initialized Glue client for region: {self.region}")

    def get_job_run(self, job_name: str, run_id: str) -> dict[str, Any]:
        """Get Glue job run details.

        Args:
            job_name: Glue job name
            run_id: Job run ID

        Returns:
            Job run details

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            response = self.client.get_job_run(JobName=job_name, RunId=run_id)
            job_run = response.get("JobRun", {})
            
            logger.info(f"Retrieved job run {run_id} for job {job_name}")
            
            return {
                "job_name": job_name,
                "run_id": run_id,
                "job_run_state": job_run.get("JobRunState"),
                "started_on": job_run.get("StartedOn"),
                "completed_on": job_run.get("CompletedOn"),
                "execution_time": job_run.get("ExecutionTime"),
                "error_message": job_run.get("ErrorMessage"),
                "error_string": job_run.get("ErrorMessage"),
                "predecessor_runs": job_run.get("PredecessorRuns", []),
                "allocated_capacity": job_run.get("AllocatedCapacity"),
                "glue_version": job_run.get("GlueVersion"),
                "arguments": job_run.get("Arguments", {}),
                "log_group_name": job_run.get("LogGroupName"),
            }

        except ClientError as e:
            logger.error(f"Failed to get Glue job run: {e}")
            raise

    def list_job_runs(
        self,
        job_name: str,
        max_results: int = 100,
        next_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """List Glue job runs.

        Args:
            job_name: Glue job name
            max_results: Maximum number of results
            next_token: Pagination token

        Returns:
            List of job runs

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            params = {
                "JobName": job_name,
                "MaxResults": min(max_results, 1000),  # AWS limit
            }
            
            if next_token:
                params["NextToken"] = next_token

            response = self.client.get_job_runs(**params)
            
            job_runs = response.get("JobRuns", [])
            logger.info(f"Retrieved {len(job_runs)} job runs for {job_name}")
            
            return {
                "job_name": job_name,
                "job_runs": job_runs,
                "next_token": response.get("NextToken"),
            }

        except ClientError as e:
            logger.error(f"Failed to list Glue job runs: {e}")
            raise

    def get_log_groups_for_job(self, job_name: str) -> list[str]:
        """Get CloudWatch log groups associated with a Glue job.

        Args:
            job_name: Glue job name

        Returns:
            List of log group names

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            # Get job details
            job_response = self.client.get_job(JobName=job_name)
            job = job_response.get("Job", {})
            
            log_groups = []
            
            # Check for default Glue log group
            default_log_group = f"/aws-glue/jobs/{job_name}"
            log_groups.append(default_log_group)
            
            # Check if job has custom log group in arguments
            arguments = job.get("DefaultArguments", {})
            if "--enable-continuous-cloudwatch-log" in arguments:
                # Continuous logging enabled
                log_groups.append(default_log_group)
            
            # Check for error log group
            error_log_group = f"/aws-glue/jobs/error/{job_name}"
            log_groups.append(error_log_group)
            
            # Also check for standard Glue log groups
            log_groups.append("/aws-glue/jobs/output")
            log_groups.append("/aws-glue/jobs/error")
            
            # Remove duplicates and return
            unique_log_groups = list(set(log_groups))
            logger.info(f"Found {len(unique_log_groups)} log groups for job {job_name}")
            
            return unique_log_groups

        except ClientError as e:
            logger.error(f"Failed to get log groups for Glue job: {e}")
            raise

    def get_job(self, job_name: str) -> dict[str, Any]:
        """Get Glue job details.

        Args:
            job_name: Glue job name

        Returns:
            Job details

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            response = self.client.get_job(JobName=job_name)
            job = response.get("Job", {})
            
            logger.info(f"Retrieved job details for {job_name}")
            
            return {
                "job_name": job.get("Name"),
                "role": job.get("Role"),
                "command": job.get("Command", {}),
                "default_arguments": job.get("DefaultArguments", {}),
                "glue_version": job.get("GlueVersion"),
                "allocated_capacity": job.get("AllocatedCapacity"),
                "max_capacity": job.get("MaxCapacity"),
                "timeout": job.get("Timeout"),
                "created_on": job.get("CreatedOn"),
                "last_modified_on": job.get("LastModifiedOn"),
            }

        except ClientError as e:
            logger.error(f"Failed to get Glue job: {e}")
            raise


# Global Glue client instance
glue_client = GlueClient()
