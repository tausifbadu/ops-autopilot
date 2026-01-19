"""Base MCP client for HTTP communication with MCP servers."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from agent_host.logging import get_logger

logger = get_logger(__name__)


class MCPError(Exception):
    """Base exception for MCP client errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""

    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP call times out."""

    pass


class MCPServerError(MCPError):
    """Raised when MCP server returns an error."""

    def __init__(self, message: str, status_code: int, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Simple circuit breaker implementation."""

    failure_threshold: int = 5  # Open after N failures
    success_threshold: int = 2  # Close after N successes in half-open
    timeout_seconds: int = 60  # Time before trying half-open
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED

    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker closed after successful calls")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Failed during half-open, go back to open
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            logger.warning("Circuit breaker reopened after failure in half-open state")
        elif self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

    def can_attempt(self) -> bool:
        """Check if a call can be attempted."""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.timeout_seconds
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker entering half-open state")
                return True
            return False

        # HALF_OPEN state
        return True


class MCPToolRequest(BaseModel):
    """MCP tool call request."""

    tool: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPToolResponse(BaseModel):
    """MCP tool call response."""

    result: Any = Field(..., description="Tool result")
    evidence_refs: Optional[list[str]] = Field(
        None, description="S3 references to evidence"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class MCPClientConfig(BaseModel):
    """Configuration for MCP client."""

    base_url: str = Field(..., description="MCP server base URL")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(
        default=1.0, description="Exponential backoff factor"
    )
    retry_on_status: list[int] = Field(
        default_factory=lambda: [500, 502, 503, 504],
        description="HTTP status codes to retry on",
    )
    circuit_breaker_enabled: bool = Field(
        default=True, description="Enable circuit breaker"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Failures before opening circuit"
    )
    circuit_breaker_timeout: int = Field(
        default=60, description="Seconds before trying half-open"
    )


class MCPClient:
    """Base HTTP client for MCP protocol communication."""

    def __init__(self, config: MCPClientConfig):
        """Initialize MCP client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.circuit_breaker: Optional[CircuitBreaker] = None

        if config.circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout_seconds=config.circuit_breaker_timeout,
            )

        # Create HTTP client with timeout
        self.client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            follow_redirects=True,
        )

    def call_tool(
        self, tool_name: str, arguments: dict[str, Any] = None
    ) -> MCPToolResponse:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response

        Raises:
            MCPError: If the call fails
        """
        if arguments is None:
            arguments = {}

        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_attempt():
            raise MCPError(
                f"Circuit breaker is OPEN for {self.config.base_url}. "
                "Too many recent failures."
            )

        request = MCPToolRequest(tool=tool_name, arguments=arguments)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._make_request(request)

                # Success - record and return
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"MCP call failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    if self.circuit_breaker:
                        self.circuit_breaker.record_failure()
                    raise MCPConnectionError(
                        f"Failed to connect to MCP server after {self.config.max_retries + 1} attempts: {e}"
                    ) from e

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code

                # Check if we should retry this status code
                if status_code in self.config.retry_on_status and attempt < self.config.max_retries:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"MCP server returned {status_code} (attempt {attempt + 1}/{self.config.max_retries + 1}). "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # Don't retry - record failure and raise
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

                error_response = None
                try:
                    error_response = e.response.json()
                except Exception:
                    pass

                raise MCPServerError(
                    f"MCP server returned error {status_code}: {e.response.text}",
                    status_code=status_code,
                    response=error_response,
                ) from e

            except Exception as e:
                last_exception = e
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                raise MCPError(f"Unexpected error calling MCP tool: {e}") from e

        # Should not reach here, but just in case
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
        raise MCPError(
            f"Failed to call MCP tool after {self.config.max_retries + 1} attempts"
        ) from last_exception

    def _make_request(self, request: MCPToolRequest) -> MCPToolResponse:
        """Make HTTP request to MCP server.

        Args:
            request: Tool request

        Returns:
            Tool response

        Raises:
            httpx.HTTPError: For HTTP errors
        """
        try:
            response = self.client.post(
                "/tools",
                json=request.model_dump(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            response_data = response.json()

            # Handle error response
            if "error" in response_data and response_data["error"]:
                raise MCPServerError(
                    f"MCP tool '{request.tool}' returned error: {response_data['error']}",
                    status_code=response.status_code,
                    response=response_data,
                )

            return MCPToolResponse(**response_data)

        except httpx.TimeoutException as e:
            raise MCPTimeoutError(
                f"Request to {self.config.base_url} timed out after {self.config.timeout_seconds}s"
            ) from e
        except httpx.ConnectError as e:
            raise MCPConnectionError(
                f"Failed to connect to {self.config.base_url}: {e}"
            ) from e

    def health_check(self) -> bool:
        """Check if MCP server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.client.get("/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {self.config.base_url}: {e}")
            return False

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
