"""AWS Step Functions client wrapper with multi-region support."""

import json
import re
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from orchestration_sfn.config import config
from orchestration_sfn.logging import get_logger

logger = get_logger(__name__)


def extract_region_from_arn(arn: str) -> Optional[str]:
    """Extract AWS region from an ARN.

    ARN format: arn:aws:service:region:account-id:resource-type/resource-id

    Args:
        arn: AWS resource ARN

    Returns:
        Region if found, None otherwise
    """
    # ARN format: arn:partition:service:region:account-id:resource
    # Example: arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine
    match = re.match(r"arn:aws:[^:]+:([^:]+):", arn)
    if match:
        return match.group(1)
    return None


class StepFunctionsClient:
    """Wrapper for AWS Step Functions boto3 client with multi-region support."""

    def __init__(self, default_region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize Step Functions client manager.

        Args:
            default_region: Default AWS region (defaults to config)
            endpoint_url: AWS endpoint URL for local testing
        """
        self.default_region = default_region or config.aws_region
        # Use provided endpoint_url, or from config, but convert empty string to None
        endpoint = endpoint_url or config.aws_endpoint_url
        self.endpoint_url = endpoint if endpoint and endpoint.strip() else None
        self._clients: dict[str, Any] = {}  # Cache clients per region
        
        logger.info(f"Initialized Step Functions client manager (default region: {self.default_region})")

    def _get_client(self, region: Optional[str] = None) -> Any:
        """Get or create boto3 client for a specific region.

        Args:
            region: AWS region (defaults to default_region)

        Returns:
            boto3 Step Functions client
        """
        region = region or self.default_region
        
        # Return cached client if exists
        if region in self._clients:
            return self._clients[region]
        
        # Create new client for this region
        client_kwargs = {"region_name": region}
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
            
        client = boto3.client("stepfunctions", **client_kwargs)
        self._clients[region] = client
        logger.debug(f"Created Step Functions client for region {region}")
        
        return client

    def _get_region_from_arn(self, arn: str, override_region: Optional[str] = None) -> str:
        """Determine region from ARN or use override/default.

        Args:
            arn: Resource ARN
            override_region: Explicitly provided region (takes precedence)

        Returns:
            AWS region to use
        """
        if override_region:
            return override_region
        
        extracted_region = extract_region_from_arn(arn)
        if extracted_region:
            return extracted_region
        
        return self.default_region

    def list_executions(
        self,
        state_machine_arn: str,
        status_filter: Optional[str] = None,
        max_results: int = 100,
        next_token: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict[str, Any]:
        """List executions for a state machine.

        Args:
            state_machine_arn: State machine ARN
            status_filter: Filter by status (RUNNING, SUCCEEDED, FAILED, etc.)
            max_results: Maximum number of results
            next_token: Pagination token
            region: AWS region (auto-detected from ARN if not provided)

        Returns:
            Execution list response

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            target_region = self._get_region_from_arn(state_machine_arn, region)
            client = self._get_client(target_region)
            
            params = {
                "stateMachineArn": state_machine_arn,
                "maxResults": min(max_results, 1000),  # AWS limit
            }
            
            if status_filter:
                params["statusFilter"] = status_filter
            if next_token:
                params["nextToken"] = next_token

            response = client.list_executions(**params)
            
            logger.info(
                f"Listed {len(response.get('executions', []))} executions for {state_machine_arn} (region: {target_region})"
            )
            
            return response

        except ClientError as e:
            logger.error(f"Failed to list executions: {e}")
            raise

    def describe_execution(
        self, execution_arn: str, region: Optional[str] = None
    ) -> dict[str, Any]:
        """Describe an execution.

        Args:
            execution_arn: Execution ARN
            region: AWS region (auto-detected from ARN if not provided)

        Returns:
            Execution details

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            target_region = self._get_region_from_arn(execution_arn, region)
            client = self._get_client(target_region)
            
            response = client.describe_execution(executionArn=execution_arn)
            
            logger.info(f"Described execution: {execution_arn} (region: {target_region})")
            
            return response

        except ClientError as e:
            logger.error(f"Failed to describe execution {execution_arn}: {e}")
            raise

    def get_execution_history(
        self,
        execution_arn: str,
        max_results: int = 1000,
        next_token: Optional[str] = None,
        reverse_order: bool = False,
        region: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get execution history (events).

        Args:
            execution_arn: Execution ARN
            max_results: Maximum number of events
            next_token: Pagination token
            reverse_order: Return events in reverse chronological order
            region: AWS region (auto-detected from ARN if not provided)

        Returns:
            Execution history response

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            target_region = self._get_region_from_arn(execution_arn, region)
            client = self._get_client(target_region)
            
            params = {
                "executionArn": execution_arn,
                "maxResults": min(max_results, 10000),  # AWS limit
                "reverseOrder": reverse_order,
            }
            
            if next_token:
                params["nextToken"] = next_token

            response = client.get_execution_history(**params)
            
            events = response.get("events", [])
            logger.info(
                f"Retrieved {len(events)} events for execution {execution_arn} (region: {target_region})"
            )
            
            return response

        except ClientError as e:
            logger.error(f"Failed to get execution history for {execution_arn}: {e}")
            raise

    def start_execution(
        self,
        state_machine_arn: str,
        input_data: Optional[dict[str, Any]] = None,
        name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict[str, Any]:
        """Start a new execution.

        Args:
            state_machine_arn: State machine ARN
            input_data: Execution input (will be JSON serialized)
            name: Execution name (optional)
            region: AWS region (auto-detected from ARN if not provided)

        Returns:
            Start execution response with executionArn

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            target_region = self._get_region_from_arn(state_machine_arn, region)
            client = self._get_client(target_region)
            
            params = {"stateMachineArn": state_machine_arn}
            
            if input_data is not None:
                params["input"] = json.dumps(input_data)
            if name:
                params["name"] = name

            response = client.start_execution(**params)
            
            execution_arn = response.get("executionArn")
            logger.info(f"Started execution: {execution_arn} (region: {target_region})")
            
            return response

        except ClientError as e:
            logger.error(f"Failed to start execution: {e}")
            raise

    def stop_execution(
        self,
        execution_arn: str,
        error: Optional[str] = None,
        cause: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict[str, Any]:
        """Stop a running execution.

        Args:
            execution_arn: Execution ARN
            error: Error code (optional)
            cause: Error cause (optional)
            region: AWS region (auto-detected from ARN if not provided)

        Returns:
            Stop execution response

        Raises:
            ClientError: If AWS API call fails
        """
        try:
            target_region = self._get_region_from_arn(execution_arn, region)
            client = self._get_client(target_region)
            
            params = {"executionArn": execution_arn}
            
            if error:
                params["error"] = error
            if cause:
                params["cause"] = cause

            response = client.stop_execution(**params)
            
            logger.info(f"Stopped execution: {execution_arn} (region: {target_region})")
            
            return response

        except ClientError as e:
            logger.error(f"Failed to stop execution {execution_arn}: {e}")
            raise


# Global client instance
sfn_client = StepFunctionsClient()
