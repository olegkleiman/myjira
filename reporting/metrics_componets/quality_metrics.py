"""
Quality metrics fetcher - CFDs, hotfixes, reopen rate, fix rate
"""

from atlassian import Jira

from typing import Optional
from .base_fetcher import BaseMetricsFetcher
from .jql_builder import JQLBuilder
from .metrics_data import MetricsData

import logging
logger = logging.getLogger(__name__)

class QualityMetricsFetcher(BaseMetricsFetcher):
    """Gets quality metrics from Jira"""

    def __init__(self, 
                 jira_client: Jira, 
                 start_date: str, 
                 end_date: str):
        super().__init__(jira_client, 
                         start_date=start_date, 
                         end_date=end_date)
        self.jql_builder = JQLBuilder(self.start_date, self.end_date)

    def fetch_customer_found_defects_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Get customer found defects for a squad."""
        try:
            jql = self.jql_builder.customer_found_defects_query_by_squad(squad_name)
            issues = self.jira_client.jql(jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            metrics_data.customer_found_defect_tickets = issues if issues else []
            metrics_data.customer_found_defects_jql = jql

            result_count = len(issues) if issues else 0
            self._log_query_results("Customer Found Defects", squad_name, jql, issues,
                                    f"Total customer defects found: {result_count}")

            return result_count

        except Exception as e:
            logger.error(f"Error fetching CFDs for squad {squad_name}: {e}")
            return None

    def fetch_customer_found_defects_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Trend baseline for CFDs: same count, previous comparison window."""
        try:
            jql = self.jql_builder.customer_found_defects_previous_query_by_squad(squad_name)
            issues = self.jira_client.jql(jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            result_count = len(issues) if issues else 0
            self._log_query_results("Customer Found Defects (Previous Period)", squad_name, jql, issues,
                                    f"Total customer defects found: {result_count}")

            return result_count

        except Exception as e:
            print(f"Error fetching previous CFDs for squad {squad_name}: {e}")
            return None

    def fetch_hotfix_frequency_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Fetch hotfix frequency for a squad."""
        try:
            jql = self.jql_builder.hotfix_frequency_query_by_squad(squad_name)
            fields = 'key,summary,issuetype,status,created,updated,project,fixVersions,customfield_13700'
            issues = self.jira_client.jql(jql, fields=fields)

            metrics_data.hotfix_tickets = issues if issues else []
            metrics_data.hotfix_jql = jql

            unique_hotfix_versions = set()
            if issues:
                for issue in issues:
                    fields_data = issue.get('fields', {})
                    fix_versions = fields_data.get('fixVersions', [])
                    for version in fix_versions:
                        if version and version.get('name'):
                            unique_hotfix_versions.add(version['name'])

            result_count = len(unique_hotfix_versions)
            version_info = f"Unique hotfix versions: {result_count}"
            self._log_query_results(
                "Hotfix Frequency", squad_name, jql, issues, version_info)

            return result_count

        except Exception as e:
            print(
                f"Error fetching hotfix frequency for squad {squad_name}: {e}")
            return None

    def fetch_hotfix_frequency_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Trend baseline for Hotfix Frequency: same count, previous comparison window."""
        try:
            jql = self.jql_builder.hotfix_frequency_previous_query_by_squad(squad_name)
            fields = 'key,summary,issuetype,status,created,updated,project,fixVersions,customfield_13700'
            issues = self.jira_client.jql(jql, fields=fields)

            unique_hotfix_versions = set()
            if issues:
                for issue in issues:
                    fields_data = issue.get('fields', {})
                    fix_versions = fields_data.get('fixVersions', [])
                    for version in fix_versions:
                        if version and version.get('name'):
                            unique_hotfix_versions.add(version['name'])

            result_count = len(unique_hotfix_versions)
            self._log_query_results(
                "Hotfix Frequency (Previous Period)", squad_name, jql, issues,
                f"Unique hotfix versions: {result_count}")

            return result_count

        except Exception as e:
            print(
                f"Error fetching previous hotfix frequency for squad {squad_name}: {e}")
            return None

    def fetch_reopen_rate_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Fetch customer defect reopen rate for a squad."""
        try:
            resolved_jql = self.jql_builder.customer_defects_resolved_query_by_squad(squad_name)
            reopened_jql = self.jql_builder.customer_defects_reopened_query_by_squad(squad_name)

            resolved_issues = self.jira_client.jql(resolved_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')
            reopened_issues = self.jira_client.jql(reopened_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            metrics_data.customer_defect_reopen_resolved_tickets = resolved_issues if resolved_issues else []
            metrics_data.customer_defect_reopen_reopened_tickets = reopened_issues if reopened_issues else []
            metrics_data.customer_defect_reopen_resolved_jql = resolved_jql
            metrics_data.customer_defect_reopen_reopened_jql = reopened_jql

            resolved_count = len(resolved_issues) if resolved_issues else 0
            reopened_count = len(reopened_issues) if reopened_issues else 0

            self._log_query_results(
                "Customer Defects Resolved", squad_name, resolved_jql, resolved_issues)
            self._log_query_results(
                "Customer Defects Reopened", squad_name, reopened_jql, reopened_issues)

            if resolved_count == 0:
                return None

            reopen_rate = (reopened_count / resolved_count) * 100
            return round(reopen_rate, 1)

        except Exception as e:
            print(f"Error fetching reopen rate for squad {squad_name}: {e}")
            return None

    def fetch_reopen_rate_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Trend baseline for CDRR: same rate, previous comparison window."""
        try:
            resolved_jql = self.jql_builder.customer_defects_resolved_previous_query_by_squad(squad_name)
            reopened_jql = self.jql_builder.customer_defects_reopened_previous_query_by_squad(squad_name)

            resolved_issues = self.jira_client.jql(resolved_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')
            reopened_issues = self.jira_client.jql(reopened_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            resolved_count = len(resolved_issues) if resolved_issues else 0
            reopened_count = len(reopened_issues) if reopened_issues else 0

            self._log_query_results(
                "Customer Defects Resolved (Previous Period)", squad_name, resolved_jql, resolved_issues)
            self._log_query_results(
                "Customer Defects Reopened (Previous Period)", squad_name, reopened_jql, reopened_issues)

            if resolved_count == 0:
                return None

            reopen_rate = (reopened_count / resolved_count) * 100
            return round(reopen_rate, 1)

        except Exception as e:
            print(f"Error fetching previous reopen rate for squad {squad_name}: {e}")
            return None

    def fetch_customer_defect_fix_rate_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Fetch customer defect fix rate for a squad."""
        try:
            all_created_jql = self.jql_builder.customer_defects_all_created_query_by_squad(squad_name)
            fixed_jql = self.jql_builder.customer_defects_resolved_with_fix_query_by_squad(squad_name)

            all_created_issues = self.jira_client.jql(
                all_created_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')
            fixed_issues = self.jira_client.jql(fixed_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            metrics_data.customer_defect_fix_total_tickets = all_created_issues if all_created_issues else []
            metrics_data.customer_defect_fix_resolved_tickets = fixed_issues if fixed_issues else []
            metrics_data.customer_defect_fix_total_jql = all_created_jql
            metrics_data.customer_defect_fix_resolved_jql = fixed_jql

            total_count = len(all_created_issues) if all_created_issues else 0
            resolved_count = len(fixed_issues) if fixed_issues else 0

            self._log_query_results(
                "Customer Defects Created", squad_name, all_created_jql, all_created_issues)
            self._log_query_results(
                "Customer Defects Fixed", squad_name, fixed_jql, fixed_issues)

            if total_count == 0:
                return None

            fix_rate = (resolved_count / total_count) * 100
            return round(fix_rate, 1)

        except Exception as e:
            print(
                f"Error fetching customer defect fix rate for squad {squad_name}: {e}")
            return None

    def fetch_customer_defect_fix_rate_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Trend baseline for CDFR: same rate, previous comparison window."""
        try:
            all_created_jql = self.jql_builder.customer_defects_all_created_previous_query_by_squad(squad_name)
            fixed_jql = self.jql_builder.customer_defects_resolved_with_fix_previous_query_by_squad(squad_name)

            all_created_issues = self.jira_client.jql(
                all_created_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')
            fixed_issues = self.jira_client.jql(fixed_jql, fields='key,summary,issuetype,status,created,resolutiondate,project')

            total_count = len(all_created_issues) if all_created_issues else 0
            resolved_count = len(fixed_issues) if fixed_issues else 0

            self._log_query_results(
                "Customer Defects Created (Previous Period)", squad_name, all_created_jql, all_created_issues)
            self._log_query_results(
                "Customer Defects Fixed (Previous Period)", squad_name, fixed_jql, fixed_issues)

            if total_count == 0:
                return None

            fix_rate = (resolved_count / total_count) * 100
            return round(fix_rate, 1)

        except Exception as e:
            print(
                f"Error fetching previous customer defect fix rate for squad {squad_name}: {e}")
            return None
