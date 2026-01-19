"""Pipeline RCA Agent - investigates pipeline failures and generates root cause analysis."""

import json
from pathlib import Path

from typing import Optional

from shared.schemas.common import Confidence
from shared.schemas.events import PipelineFailureEvent
from shared.schemas.evidence import EvidencePack
from shared.schemas.rca import (
    FailureClassification,
    PipelineIncidentAnalysis,
    RecommendedAction,
)

from agent_host.config import config
from agent_host.llm import get_llm_provider
from agent_host.logging import get_logger
from agent_host.mcp_client.base import MCPClient, MCPClientConfig
from agent_host.mcp_client.devtools import GitHubMCPClient
from agent_host.state.evidence_store import EvidenceStore

logger = get_logger(__name__)


class PipelineRCAAgent:
    """Agent that performs root cause analysis for pipeline failures."""

    def __init__(self, llm_provider_name: Optional[str] = None, llm_model: Optional[str] = None):
        """Initialize Pipeline RCA Agent.

        Args:
            llm_provider_name: LLM provider name (optional, uses config default)
            llm_model: LLM model name (optional, uses provider default)
        """
        self.config = config
        self.evidence_store = EvidenceStore()

        # Initialize MCP clients
        self.orchestration_client = MCPClient(
            MCPClientConfig(base_url=config.mcp_orchestration_url)
        )
        self.github_client = GitHubMCPClient()

        # Initialize LLM provider
        self.llm = get_llm_provider(provider_name=llm_provider_name, model=llm_model)
        logger.info(f"Initialized Pipeline RCA Agent with LLM: {llm_provider_name or config.llm_provider}")

    def investigate(
        self, event: PipelineFailureEvent
    ) -> PipelineIncidentAnalysis:
        """Investigate pipeline failure and generate RCA.

        Args:
            event: Pipeline failure event

        Returns:
            Pipeline incident analysis with root cause
        """
        logger.info(f"Investigating pipeline failure: {event.execution_arn}")

        # Step 1: Gather evidence
        evidence = self._gather_evidence(event)

        # Step 2: Store evidence
        incident_id = f"incident_{event.event_id}"
        self.evidence_store.save(incident_id, evidence)

        # Step 3: Generate initial RCA (using LLM or rule-based for MVP)
        rca_result = self._generate_rca(event, evidence)

        # Step 4: If CODE_REGRESSION detected, investigate code
        if rca_result.classification == FailureClassification.CODE_REGRESSION:
            logger.info("CODE_REGRESSION detected - investigating code changes")
            code_analysis = self._investigate_code_bug(event, evidence, rca_result)
            if code_analysis:
                # Update evidence with code analysis
                evidence.additional_data["code_analysis"] = code_analysis
                # Re-generate RCA with code evidence
                rca_result = self._generate_rca(event, evidence)

        return rca_result

    def _gather_evidence(self, event: PipelineFailureEvent) -> EvidencePack:
        """Gather evidence about the pipeline failure.

        Args:
            event: Pipeline failure event

        Returns:
            Evidence pack with collected data
        """
        logger.info("Gathering evidence for pipeline failure")

        evidence = EvidencePack(
            incident_id=f"incident_{event.event_id}",
            collector="pipeline_rca_agent",
        )

        # If we have an execution ARN, gather execution details
        if event.execution_arn:
            try:
                # Get execution details
                exec_details_response = self.orchestration_client.call_tool(
                    tool_name="get_execution_details",
                    arguments={"execution_arn": event.execution_arn.value},
                )

                if exec_details_response.result:
                    from shared.schemas.evidence import ExecutionDetails

                    # Convert dict to ExecutionDetails model
                    exec_dict = exec_details_response.result
                    evidence.execution_details = ExecutionDetails(**exec_dict)

                # Get execution history
                exec_history_response = self.orchestration_client.call_tool(
                    tool_name="get_execution_history",
                    arguments={"execution_arn": event.execution_arn.value},
                )

                if exec_history_response.result:
                    from shared.schemas.evidence import ExecutionHistory

                    # Convert dict to ExecutionHistory model
                    history_dict = exec_history_response.result
                    evidence.execution_history = ExecutionHistory(**history_dict)

                logger.info("Collected execution evidence")

            except Exception as e:
                logger.warning(f"Failed to gather execution evidence: {e}")

        return evidence

    def _generate_rca(
        self, event: PipelineFailureEvent, evidence: EvidencePack
    ) -> PipelineIncidentAnalysis:
        """Generate root cause analysis from evidence using LLM.

        Args:
            event: Pipeline failure event
            evidence: Collected evidence

        Returns:
            Pipeline incident analysis
        """
        logger.info("Generating root cause analysis using LLM")

        # Load prompt template
        prompt_template = self._load_prompt_template()
        
        # Format prompt with evidence
        prompt = self._format_prompt(prompt_template, event, evidence)
        
        # Define response schema
        response_schema = {
            "type": "object",
            "properties": {
                "classification": {
                    "type": "string",
                    "enum": [
                        "DATA_LATE_MISSING",
                        "SCHEMA_DRIFT",
                        "DEPENDENCY_OUTAGE",
                        "RESOURCE_LIMIT",
                        "OOM_TIMEOUT",
                        "PERMISSIONS",
                        "CODE_REGRESSION",
                        "UNKNOWN",
                    ],
                },
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "root_cause_hypothesis": {"type": "string"},
                "recommended_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "safe_to_autofix": {"type": "boolean"},
                "evidence_gaps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "classification",
                "confidence",
                "root_cause_hypothesis",
                "recommended_actions",
                "safe_to_autofix",
            ],
        }

        try:
            # Call LLM with structured output
            result = self.llm.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_prompt="You are an expert DevOps engineer analyzing pipeline failures.",
                temperature=0.3,  # Lower temperature for more consistent analysis
            )

            # Map to PipelineIncidentAnalysis
            classification = FailureClassification(result["classification"])
            confidence = Confidence(value=float(result["confidence"]))
            root_cause = result["root_cause_hypothesis"]
            recommended_actions = [
                RecommendedAction(action_type=action, description=action)
                for action in result.get("recommended_actions", [])
            ]
            safe_to_autofix = result.get("safe_to_autofix", False)
            evidence_gaps = result.get("evidence_gaps", [])

            logger.info(
                f"LLM RCA generated: classification={classification}, "
                f"confidence={confidence.value}, safe_to_autofix={safe_to_autofix}"
            )

            return PipelineIncidentAnalysis(
                classification=classification,
                confidence=confidence,
                root_cause_hypothesis=root_cause,
                evidence_refs=[],
                recommended_actions=recommended_actions,
                safe_to_autofix=safe_to_autofix,
                evidence_gaps=evidence_gaps,
            )

        except Exception as e:
            logger.error(f"LLM RCA generation failed: {e}", exc_info=True)
            # Fallback to rule-based classification
            logger.warning("Falling back to rule-based classification")
            return self._generate_rca_fallback(event, evidence)

    def _load_prompt_template(self) -> str:
        """Load RCA prompt template.

        Returns:
            Prompt template text
        """
        prompt_file = Path(__file__).parent.parent / "prompts" / "rca_prompt.md"
        
        if prompt_file.exists():
            return prompt_file.read_text()
        else:
            # Fallback template
            return """Analyze the pipeline failure evidence and provide root cause analysis.

Evidence:
- Execution details: {execution_details}
- Error messages: {error_messages}

Provide structured analysis with classification, confidence, root cause, and recommendations."""

    def _format_prompt(
        self, template: str, event: PipelineFailureEvent, evidence: EvidencePack
    ) -> str:
        """Format prompt template with evidence.

        Args:
            template: Prompt template
            event: Pipeline failure event
            evidence: Evidence pack

        Returns:
            Formatted prompt
        """
        # Extract evidence summaries
        execution_details = "N/A"
        execution_history = "N/A"
        error_messages = event.error_message or "N/A"
        logs_summary = "N/A"
        metrics_summary = "N/A"

        if evidence.execution_details:
            execution_details = json.dumps(
                {
                    "status": evidence.execution_details.status,
                    "error": evidence.execution_details.error,
                    "cause": evidence.execution_details.cause,
                },
                indent=2,
            )

        if evidence.execution_history:
            events_count = len(evidence.execution_history.events)
            failing_state = evidence.execution_history.failing_state
            execution_history = f"Events: {events_count}, Failing state: {failing_state}"

        if evidence.logs:
            logs_summary = f"{len(evidence.logs)} log entries collected"

        if evidence.metrics:
            metrics_summary = f"{len(evidence.metrics)} metric series collected"

        # Include code analysis if available
        code_analysis_summary = "N/A"
        if evidence.additional_data.get("code_analysis"):
            code_analysis = evidence.additional_data["code_analysis"]
            likely_bug = code_analysis.get("likely_bug_location", {})
            code_analysis_summary = (
                f"Repository: {code_analysis.get('repository', 'N/A')}, "
                f"Files analyzed: {len(code_analysis.get('files_analyzed', []))}, "
                f"Recent commits: {len(code_analysis.get('recent_commits', []))}, "
                f"Likely bug: {likely_bug.get('likely_file', 'N/A')} "
                f"(confidence: {likely_bug.get('confidence', 0.0):.2f})"
            )

        return template.format(
            execution_details=execution_details,
            execution_history=execution_history,
            error_messages=error_messages,
            logs_summary=logs_summary,
            metrics_summary=metrics_summary,
            code_analysis=code_analysis_summary,
        )

    def _generate_rca_fallback(
        self, event: PipelineFailureEvent, evidence: EvidencePack
    ) -> PipelineIncidentAnalysis:
        """Fallback rule-based RCA if LLM fails.

        Args:
            event: Pipeline failure event
            evidence: Collected evidence

        Returns:
            Pipeline incident analysis
        """
        logger.info("Using fallback rule-based classification")

        classification = FailureClassification.UNKNOWN
        confidence = 0.5
        root_cause = "Investigation in progress - LLM analysis unavailable"

        # Simple heuristics based on execution details
        if evidence.execution_details:
            error = evidence.execution_details.error or ""
            cause = evidence.execution_details.cause or ""

            # Classify based on error patterns
            if "timeout" in error.lower() or "timeout" in cause.lower():
                classification = FailureClassification.OOM_TIMEOUT
                confidence = 0.7
                root_cause = "Execution timed out - possible resource exhaustion"
            elif "permission" in error.lower() or "access denied" in error.lower():
                classification = FailureClassification.PERMISSIONS
                confidence = 0.8
                root_cause = "Permission or access issue detected"
            elif "503" in error or "service unavailable" in error.lower():
                classification = FailureClassification.DEPENDENCY_OUTAGE
                confidence = 0.75
                root_cause = "Dependency service unavailable (503 error)"
            elif "data" in error.lower() or "schema" in error.lower():
                classification = FailureClassification.SCHEMA_DRIFT
                confidence = 0.7
                root_cause = "Data or schema issue detected"

        return PipelineIncidentAnalysis(
            classification=classification,
            confidence=Confidence(value=confidence),
            root_cause_hypothesis=root_cause,
            evidence_refs=[],
            recommended_actions=[],
            safe_to_autofix=False,
        )

    def _investigate_code_bug(
        self,
        event: PipelineFailureEvent,
        evidence: EvidencePack,
        initial_rca: PipelineIncidentAnalysis,
    ) -> Optional[dict[str, Any]]:
        """Investigate code bug using GitHub integration.

        Args:
            event: Pipeline failure event
            evidence: Collected evidence
            initial_rca: Initial RCA result suggesting CODE_REGRESSION

        Returns:
            Code analysis results or None if investigation fails
        """
        logger.info("Investigating code bug via GitHub")

        try:
            # Extract error fingerprints from evidence
            error_fingerprints = self._extract_error_fingerprints(evidence, event)

            if not error_fingerprints:
                logger.warning("No error fingerprints extracted - skipping code investigation")
                return None

            # Get repository info from config or event metadata
            repository = self._get_repository_from_event(event)
            if not repository:
                logger.warning("No repository information available - skipping code investigation")
                return None

            code_analysis = {
                "repository": repository,
                "error_fingerprints": error_fingerprints,
                "searches": [],
                "files_analyzed": [],
                "recent_commits": [],
                "likely_bug_location": None,
            }

            # Search for relevant code files based on error fingerprints
            for fingerprint in error_fingerprints[:3]:  # Limit to top 3 searches
                try:
                    search_results = self.github_client.search_code(
                        query=f"{fingerprint}",
                        repository=repository,
                    )
                    if search_results:
                        code_analysis["searches"].append({
                            "query": fingerprint,
                            "results_count": len(search_results),
                            "files": [r.get("path", "") for r in search_results[:5]],
                        })
                        logger.info(f"Found {len(search_results)} files matching '{fingerprint}'")
                except Exception as e:
                    logger.warning(f"Code search failed for '{fingerprint}': {e}")

            # Get recent commits (last 7 days) to check for regressions
            try:
                from datetime import datetime, timedelta
                since = (datetime.utcnow() - timedelta(days=7)).isoformat()
                recent_commits = self.github_client.get_recent_commits(
                    repository=repository,
                    since=since,
                    limit=20,
                )
                code_analysis["recent_commits"] = recent_commits
                logger.info(f"Found {len(recent_commits)} recent commits")
            except Exception as e:
                logger.warning(f"Failed to get recent commits: {e}")

            # Analyze top search results
            for search in code_analysis["searches"]:
                for file_path in search.get("files", [])[:3]:  # Analyze top 3 files per search
                    try:
                        # Read file content
                        file_content = self.github_client.read_file(
                            repository=repository,
                            file_path=file_path,
                        )

                        # Get git blame to see recent changes
                        blame_info = self.github_client.get_file_blame(
                            repository=repository,
                            file_path=file_path,
                        )

                        code_analysis["files_analyzed"].append({
                            "path": file_path,
                            "content_length": len(file_content.get("content", "")),
                            "recent_changes": blame_info.get("recent_changes", []),
                        })

                    except Exception as e:
                        logger.warning(f"Failed to analyze file {file_path}: {e}")

            # Use LLM to identify likely bug location
            if code_analysis["files_analyzed"]:
                likely_bug = self._identify_likely_bug_location(
                    error_fingerprints, code_analysis, evidence
                )
                code_analysis["likely_bug_location"] = likely_bug

            logger.info("Code investigation completed")
            return code_analysis

        except Exception as e:
            logger.error(f"Code investigation failed: {e}", exc_info=True)
            return None

    def _extract_error_fingerprints(
        self, evidence: EvidencePack, event: PipelineFailureEvent
    ) -> list[str]:
        """Extract error fingerprints from evidence for code search.

        Args:
            evidence: Evidence pack
            event: Pipeline failure event

        Returns:
            List of error fingerprints (exception names, function names, etc.)
        """
        fingerprints = []

        # Extract from execution details
        if evidence.execution_details:
            error = evidence.execution_details.error or ""
            cause = evidence.execution_details.cause or ""

            # Extract exception class names
            import re
            exception_pattern = r"(\w+Exception|\w+Error|\w+Failure)"
            exceptions = re.findall(exception_pattern, error + " " + cause)
            fingerprints.extend(exceptions)

            # Extract function/method names
            function_pattern = r"(\w+\.\w+\(|\w+\([^)]*\))"
            functions = re.findall(function_pattern, error + " " + cause)
            fingerprints.extend([f.split("(")[0] for f in functions])

        # Extract from execution history
        if evidence.execution_history and evidence.execution_history.events:
            for event_item in evidence.execution_history.events:
                if isinstance(event_item, dict):
                    error_msg = event_item.get("executionFailedEventDetails", {}).get("error", "")
                    if error_msg:
                        # Extract exception names
                        import re
                        exception_pattern = r"(\w+Exception|\w+Error)"
                        exceptions = re.findall(exception_pattern, error_msg)
                        fingerprints.extend(exceptions)

        # Extract from event error message
        if event.error_message:
            import re
            exception_pattern = r"(\w+Exception|\w+Error|\w+Failure)"
            exceptions = re.findall(exception_pattern, event.error_message)
            fingerprints.extend(exceptions)

        # Deduplicate and filter
        fingerprints = list(set([f for f in fingerprints if len(f) > 3]))
        return fingerprints[:10]  # Limit to top 10

    def _get_repository_from_event(self, event: PipelineFailureEvent) -> Optional[str]:
        """Extract repository information from event.

        Args:
            event: Pipeline failure event

        Returns:
            Repository name (owner/repo) or None
        """
        # Check event metadata
        if event.metadata:
            repo = event.metadata.get("repository")
            if repo:
                return repo

        # Check config for default repository
        if self.config.default_repository:
            return self.config.default_repository

        # Try to infer from execution ARN or state machine name
        # This is a placeholder - in production, you'd have a registry mapping
        logger.warning("No repository information found in event or config")
        return None

    def _identify_likely_bug_location(
        self,
        error_fingerprints: list[str],
        code_analysis: dict[str, Any],
        evidence: EvidencePack,
    ) -> Optional[dict[str, Any]]:
        """Use LLM to identify likely bug location from code analysis.

        Args:
            error_fingerprints: Error fingerprints
            code_analysis: Code analysis results
            evidence: Evidence pack

        Returns:
            Likely bug location analysis
        """
        try:
            # Prepare prompt for LLM
            prompt = f"""Analyze the following code investigation results to identify the likely bug location.

Error Fingerprints:
{json.dumps(error_fingerprints, indent=2)}

Recent Commits ({len(code_analysis.get('recent_commits', []))}):
{json.dumps(code_analysis.get('recent_commits', [])[:5], indent=2)}

Files Analyzed:
{json.dumps(code_analysis.get('files_analyzed', []), indent=2)}

Based on the error fingerprints and recent code changes, identify:
1. The most likely file where the bug exists
2. The likely cause (recent change, logic error, etc.)
3. Confidence level (0.0-1.0)

Provide a structured analysis."""

            response_schema = {
                "type": "object",
                "properties": {
                    "likely_file": {"type": "string"},
                    "likely_cause": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reasoning": {"type": "string"},
                },
                "required": ["likely_file", "likely_cause", "confidence"],
            }

            result = self.llm.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_prompt="You are an expert code reviewer analyzing bug locations.",
                temperature=0.2,
            )

            return result

        except Exception as e:
            logger.warning(f"Failed to identify bug location with LLM: {e}")
            return None
