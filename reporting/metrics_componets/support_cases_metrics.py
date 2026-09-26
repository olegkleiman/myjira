"""
Support Cases metrics - SLA tracking for customer support cases
"""

from datetime import datetime, timedelta
from typing import Any, List, Dict, Tuple, Optional

from models import SupportCase, SupportCasesMetrics, JiraStatus, JiraProject
from .base_fetcher import BaseMetricsFetcher
from .jql_builder import JQLBuilder
from atlassian import Jira

import logging
logger = logging.getLogger(__name__)

class SupportCasesMetricsFetcher(BaseMetricsFetcher):
    """Fetches and calculates SLA metrics for support cases"""

    def __init__(self, 
                 jira_client: Jira, 
                 support_case_issue_type: str = "Support Case",
                 start_date: str = None, 
                 end_date: str = None):
        super().__init__(jira_client, start_date=start_date, end_date=end_date)
        self.support_case_issue_type = support_case_issue_type
        self.jql_builder = JQLBuilder(self.start_date, self.end_date)

    def _parse_support_case(self, issue_data: Dict[str, Any]) -> SupportCase:
        """Parse a support case from Jira API response."""
        fields = issue_data.get('fields', {})

        # Parse basic fields
        key = issue_data.get('key', '')
        summary = fields.get('summary', '')
        priority = fields.get('priority', {}).get(
            'name', 'Medium') if fields.get('priority') else 'Medium'
        created = fields.get('created', '')
        resolved = fields.get('resolutiondate')

        # Parse status
        status_data = fields.get('status', {})
        status_category = status_data.get('statusCategory', {})
        status = JiraStatus(
            name=status_data.get('name', ''),
            status_category_key=status_category.get('key', '')
        )

        # Parse project
        project_data = fields.get('project', {})
        project = JiraProject(
            key=project_data.get('key', ''),
            name=project_data.get('name', '')
        )

        # Get squad field
        squad = fields.get('customfield_14829', {})
        squad_name = squad.get('value', '') if isinstance(
            squad, dict) else str(squad) if squad else None

        return SupportCase(
            key=key,
            summary=summary,
            priority=priority,
            created=created,
            resolved=resolved,
            status=status,
            project=project,
            squad=squad_name
        )

    def _substitute_date_placeholders(self, jql: str) -> str:
        """Substitute {start_date}/{end_date} placeholders in a custom JQL
        override (see support_cases.jql_overrides in config.yaml)."""
        jql = jql.replace('{start_date}', self.start_date)
        jql = jql.replace('{end_date}', self.end_date)
        return jql

    def fetch_support_cases_metrics_by_squad(
        self,
        squad_name: str,
        environment: str = "all",
        custom_created_jql: Optional[str] = None,
        custom_resolved_jql: Optional[str] = None
    ) -> SupportCasesMetrics:
        """
        Fetch support cases metrics for a squad.

        Args:
            squad_name: Name of the squad
            environment: Environment filter ("all", "production", "non_production")
            custom_created_jql: Optional custom JQL query for created cases (overrides default)
            custom_resolved_jql: Optional custom JQL query for resolved cases (overrides default)

        Returns:
            SupportCasesMetrics object with calculated metrics
        """
        # Use custom JQL queries if provided, otherwise build default queries
        if custom_created_jql:
            created_jql = self._substitute_date_placeholders(custom_created_jql)
            if environment == "production":
                created_jql = f'({created_jql}) AND "Found by:" in ("Customer - Production")'
            elif environment == "non_production":
                created_jql = f'({created_jql}) AND ("Found by:" not in ("Customer - Production") OR "Found by:" is EMPTY)'
        else:
            created_jql = self.jql_builder.support_cases_created_query(
                squad_name, self.support_case_issue_type, environment=environment
            )

        if custom_resolved_jql:
            resolved_jql = self._substitute_date_placeholders(custom_resolved_jql)
            if environment == "production":
                resolved_jql = f'({resolved_jql}) AND "Found by:" in ("Customer - Production")'
            elif environment == "non_production":
                resolved_jql = f'({resolved_jql}) AND ("Found by:" not in ("Customer - Production") OR "Found by:" is EMPTY)'
        else:
            resolved_jql = self.jql_builder.support_cases_resolved_query(
                squad_name, self.support_case_issue_type, environment=environment
            )

        # Log queries
        logger.info(f"[Support Cases] Squad: {squad_name} | Environment: {environment}")
        logger.info(f"[Support Cases] Created JQL: {created_jql}")
        logger.info(f"[Support Cases] Resolved JQL: {resolved_jql}")

        # Fetch issues
        created_issues = self.jira_client.jql(
            created_jql,
            fields='key,summary,priority,created,updated,status,project,resolutiondate,customfield_14829'
        )
        resolved_issues = self.jira_client.jql(
            resolved_jql,
            fields='key,summary,priority,created,updated,resolved,status,project,resolutiondate,customfield_14829'
        )

        # Log results
        self._log_query_results(
            f"Support Cases Ingress (Created) - {squad_name}",
            squad_name,
            created_jql,
            created_issues
        )
        self._log_query_results(
            f"Support Cases Egress (Resolved) - {squad_name}",
            squad_name,
            resolved_jql,
            resolved_issues
        )

        # Parse support cases
        cases = [self._parse_support_case(issue) for issue in created_issues]

        # Calculate metrics
        ingress = len(cases)  # Cases created in timeframe
        egress = len(resolved_issues)  # Cases resolved in timeframe

        return SupportCasesMetrics(
            squad_name=squad_name,
            project_name=None,
            environment=environment,
            ingress=ingress,
            egress=egress,
            cases=cases
        )
