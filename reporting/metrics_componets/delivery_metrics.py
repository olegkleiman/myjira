"""
Delivery metrics fetcher - release frequency and on-time delivery
"""

from typing import Optional
from datetime import datetime
from .base_fetcher import BaseMetricsFetcher
from .jql_builder import JQLBuilder
from .metrics_data import MetricsData

from atlassian import Jira

class DeliveryMetricsFetcher(BaseMetricsFetcher):
    """Gets delivery metrics from Jira"""

    # Locked custom field holding the committed target date for an epic (see
    # config.yaml jira.fields.commit_date). This field is meant to be locked
    # once an epic enters Delivery Phase - do not let this code write to it,
    # or ODR gets artificially inflated as target dates drift to match actuals.
    COMMIT_DATE_FIELD = "customfield_14768"

    def __init__(self, 
                 jira_client : Jira, 
                 start_date: str, 
                 end_date: str):
        super().__init__(jira_client, 
                         start_date=start_date, 
                         end_date=end_date)
        self.jql_builder = JQLBuilder(self.start_date, self.end_date)

    @classmethod
    def _split_by_commit_date(cls, issues: list) -> tuple:
        """Split epics into those with a locked Commit Date and those
        without. Epics without a Commit Date can't be evaluated for on-time
        status and must be excluded from ODR entirely."""
        with_commit_date = []
        excluded = []
        for issue in issues:
            fields = issue.get('fields', {})
            if fields.get(cls.COMMIT_DATE_FIELD):
                with_commit_date.append(issue)
            else:
                excluded.append(issue)
        return with_commit_date, excluded

    @classmethod
    def _filter_ontime_issues(cls, issues: list) -> list:
        """Filter issues where resolutionDate <= Commit Date (on-time delivery).
        Issues with no Commit Date are excluded rather than assumed on-time."""
        ontime = []
        late = []
        skipped = []
        for issue in issues:
            key = issue.get('key', '?')
            fields = issue.get('fields', {})
            resolved = fields.get('resolutiondate') or fields.get('resolved')
            commit_date = fields.get(cls.COMMIT_DATE_FIELD)

            print(f"[ODR FILTER] {key}: resolutiondate={fields.get('resolutiondate')}, "
                  f"resolved={fields.get('resolved')}, commit_date={commit_date}")

            if resolved and commit_date:
                resolved_date = resolved[:10]
                commit_date_str = commit_date[:10]
                is_ontime = resolved_date <= commit_date_str
                print(f"[ODR FILTER] {key}: resolved_date={resolved_date}, commit_date={commit_date_str}, "
                      f"on_time={is_ontime}")
                if is_ontime:
                    ontime.append(issue)
                else:
                    late.append(issue)
            else:
                print(f"[ODR FILTER] {key}: SKIPPED (missing resolved={resolved}, commit_date={commit_date})")
                skipped.append(issue)

        print(f"[ODR FILTER] Summary: {len(ontime)} on-time, {len(late)} late, "
              f"{len(skipped)} skipped (missing dates), {len(issues)} total input")
        return ontime

    def fetch_release_frequency_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Fetch release frequency for a squad."""
        try:
            jql = self.jql_builder.release_frequency_query_by_squad(squad_name)
            issues = self.jira_client.jql(jql)

            metrics_data.release_frequency_tickets = issues if issues else []
            metrics_data.release_frequency_jql = jql

            total_releases = len(issues) if issues else 0
            self._log_query_results("Release Frequency", squad_name, jql, issues,
                                    f"Total releases: {total_releases}. Release issues with Prod EMEA Date in reporting period.")

            return total_releases

        except Exception as e:
            print(f"Error fetching release frequency for squad {squad_name}: {e}")
            return None

    def fetch_release_frequency_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[int]:
        """Trend baseline for Release Frequency: same count, previous comparison window."""
        try:
            jql = self.jql_builder.release_frequency_previous_query_by_squad(squad_name)
            issues = self.jira_client.jql(jql)

            total_releases = len(issues) if issues else 0
            self._log_query_results("Release Frequency (Previous Period)", squad_name, jql, issues,
                                    f"Total releases: {total_releases}. Release issues with Prod EMEA Date in the previous comparison window.")

            return total_releases

        except Exception as e:
            print(f"Error fetching previous release frequency for squad {squad_name}: {e}")
            return None

    def fetch_ontime_delivery_rate_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Fetch on-time delivery rate for a squad. ODR (On-time Delivery
        Rate): percentage of epics delivered in the trailing 30 days that
        were resolved on or before their locked Commit Date
        (customfield_14768). Epics without a Commit Date are excluded from
        this calculation. This is a rolling window, recalculated relative to
        the time the report is run - not a fixed calendar month."""
        try:
            denominator_jql = self.jql_builder.ontime_delivery_query_by_squad(squad_name)
            numerator_jql = self.jql_builder.ontime_delivery_numerator_query_by_squad(squad_name)

            fields = f'key,summary,status,issuetype,created,resolved,resolutiondate,{self.COMMIT_DATE_FIELD}'

            denominator_issues_raw = self.jira_client.jql(denominator_jql, fields=fields)
            numerator_issues_raw = self.jira_client.jql(numerator_jql, fields=fields)

            print(f"[ODR SQUAD DEBUG] Denominator issues (pre-filter): {len(denominator_issues_raw) if denominator_issues_raw else 0}")
            print(f"[ODR SQUAD DEBUG] Numerator issues (pre-filter): {len(numerator_issues_raw) if numerator_issues_raw else 0}")

            denominator_issues, excluded_issues = self._split_by_commit_date(denominator_issues_raw or [])
            excluded_count = len(excluded_issues)
            print(f"[ODR SQUAD DEBUG] Excluded {excluded_count} epics with no Commit Date ({self.COMMIT_DATE_FIELD}) from denominator")

            numerator_issues = self._filter_ontime_issues(numerator_issues_raw) if numerator_issues_raw else []

            total_epics = len(denominator_issues)
            ontime_epics = len(numerator_issues)

            print(f"[ODR SQUAD DEBUG] Numerator (on-time after filter): {ontime_epics}")

            metrics_data.ontime_delivery_tickets = denominator_issues
            metrics_data.ontime_delivery_jql = denominator_jql
            metrics_data.ontime_delivery_numerator_tickets = numerator_issues
            metrics_data.ontime_delivery_numerator_jql = numerator_jql
            metrics_data.ontime_delivery_excluded_count = excluded_count

            self._log_query_results("On-Time Delivery Rate", squad_name, denominator_jql, denominator_issues,
                                    f"Total epics: {total_epics}, On-time epics: {ontime_epics}, Excluded (no Commit Date): {excluded_count}")

            if total_epics == 0:
                return None

            completion_rate = (ontime_epics / total_epics) * 100
            return round(completion_rate, 1)

        except Exception as e:
            print(f"Error fetching on-time delivery rate for squad {squad_name}: {e}")
            return None

    def fetch_ontime_delivery_rate_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Trend baseline for ODR: same rate, previous comparison window."""
        try:
            denominator_jql = self.jql_builder.ontime_delivery_previous_query_by_squad(squad_name)
            numerator_jql = self.jql_builder.ontime_delivery_numerator_previous_query_by_squad(squad_name)

            fields = f'key,summary,status,issuetype,created,resolved,resolutiondate,{self.COMMIT_DATE_FIELD}'

            denominator_issues_raw = self.jira_client.jql(denominator_jql, fields=fields)
            numerator_issues_raw = self.jira_client.jql(numerator_jql, fields=fields)

            denominator_issues, excluded_issues = self._split_by_commit_date(denominator_issues_raw or [])
            numerator_issues = self._filter_ontime_issues(numerator_issues_raw) if numerator_issues_raw else []

            total_epics = len(denominator_issues)
            ontime_epics = len(numerator_issues)

            self._log_query_results("On-Time Delivery Rate (Previous Period)", squad_name, denominator_jql, denominator_issues,
                                    f"Total epics: {total_epics}, On-time epics: {ontime_epics}, Excluded (no Commit Date): {len(excluded_issues)}")

            if total_epics == 0:
                return None

            completion_rate = (ontime_epics / total_epics) * 100
            return round(completion_rate, 1)

        except Exception as e:
            print(f"Error fetching previous on-time delivery rate for squad {squad_name}: {e}")
            return None
