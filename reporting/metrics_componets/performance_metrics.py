"""
Performance metrics fetcher - epic status rate and defects resolution rate
"""

from typing import Optional
from .base_fetcher import BaseMetricsFetcher
from .jql_builder import JQLBuilder
from .metrics_data import MetricsData

from atlassian import Jira

class PerformanceMetricsFetcher(BaseMetricsFetcher):
    """Gets performance metrics from Jira"""

    def __init__(self, 
                 jira_client: Jira, 
                 start_date: str, 
                 end_date: str):
        super().__init__(jira_client, 
                         start_date=start_date, 
                         end_date=end_date)
        self.jql_builder = JQLBuilder(self.start_date, self.end_date)

    def fetch_defects_resolution_rate_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Fetch defects resolution rate for a squad."""
        try:
            created_jql = self.jql_builder.all_defects_created_query_by_squad(squad_name)
            resolved_jql = self.jql_builder.all_defects_resolved_query_by_squad(squad_name)

            created_issues = self.jira_client.jql(created_jql)
            resolved_issues = self.jira_client.jql(resolved_jql)

            metrics_data.defects_resolution_created_tickets = created_issues if created_issues else []
            metrics_data.defects_resolution_resolved_tickets = resolved_issues if resolved_issues else []
            metrics_data.defects_resolution_created_jql = created_jql
            metrics_data.defects_resolution_resolved_jql = resolved_jql

            created_count = len(created_issues) if created_issues else 0
            resolved_count = len(resolved_issues) if resolved_issues else 0

            self._log_query_results(
                "Defects Created (Inflow)", squad_name, created_jql, created_issues)
            self._log_query_results(
                "Defects Resolved (Outflow)", squad_name, resolved_jql, resolved_issues)

            if created_count == 0:
                return None

            resolution_rate = (resolved_count / created_count) * 100
            return round(resolution_rate, 1)

        except Exception as e:
            print(
                f"Error fetching defects resolution rate for squad {squad_name}: {e}")
            return None

    def fetch_defects_resolution_rate_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Trend baseline for DFR: same rate, previous comparison window."""
        try:
            created_jql = self.jql_builder.all_defects_created_previous_query_by_squad(squad_name)
            resolved_jql = self.jql_builder.all_defects_resolved_previous_query_by_squad(squad_name)

            created_issues = self.jira_client.jql(created_jql)
            resolved_issues = self.jira_client.jql(resolved_jql)

            created_count = len(created_issues) if created_issues else 0
            resolved_count = len(resolved_issues) if resolved_issues else 0

            self._log_query_results(
                "Defects Created (Previous Period)", squad_name, created_jql, created_issues)
            self._log_query_results(
                "Defects Resolved (Previous Period)", squad_name, resolved_jql, resolved_issues)

            if created_count == 0:
                return None

            resolution_rate = (resolved_count / created_count) * 100
            return round(resolution_rate, 1)

        except Exception as e:
            print(
                f"Error fetching previous defects resolution rate for squad {squad_name}: {e}")
            return None
