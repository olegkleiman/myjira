"""
Output metrics fetcher - story points delivered
"""

from typing import Optional
from .base_fetcher import BaseMetricsFetcher
from .jql_builder import JQLBuilder
from .metrics_data import MetricsData

from atlassian import Jira

class OutputMetricsFetcher(BaseMetricsFetcher):
    """Gets output metrics from Jira"""

    # "Story Points - Pulse - Estimated" (see config.yaml
    # jira.fields.story_points_pulse_estimated) - a read-only text field, not
    # a number field, so values come back as strings and need parsing.
    STORY_POINTS_FIELD = "customfield_18045"

    def __init__(self, 
                 jira_client : Jira, 
                 start_date: str, 
                 end_date: str):
        super().__init__(jira_client, 
                         start_date=start_date, 
                         end_date=end_date)
        self.jql_builder = JQLBuilder(self.start_date, self.end_date)

    @classmethod
    def _sum_story_points(cls, issues: list) -> float:
        """Sum the Story Points - Pulse - Estimated field across issues,
        skipping issues where it's missing or non-numeric."""
        total = 0.0
        for issue in issues:
            raw = issue.get('fields', {}).get(cls.STORY_POINTS_FIELD)
            if raw is None:
                continue
            try:
                total += float(raw)
            except (TypeError, ValueError):
                continue
        return total

    # ===== SQUAD-BASED METHODS =====

    def fetch_story_points_delivered_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Pulse Story Points Delivered: sum of Story Points - Pulse - Estimated
        across all non-Epic issues resolved in the report's (start_date, end_date)
        window for the squad. Always scoped to the central ENT project - story
        points are tracked there."""
        try:
            jql = self.jql_builder.story_points_delivered_query_by_squad(squad_name)
            fields = f'key,summary,issuetype,status,resolutiondate,{self.STORY_POINTS_FIELD}'
            issues = self.jira_client.jql(jql, fields=fields)

            metrics_data.story_points_delivered_tickets = issues if issues else []
            metrics_data.story_points_delivered_jql = jql

            total_points = self._sum_story_points(issues) if issues else 0.0

            self._log_query_results("Pulse Story Points Delivered", squad_name, jql, issues,
                                    f"Total story points delivered: {total_points:g}")

            return round(total_points, 1)

        except Exception as e:
            print(f"Error fetching story points delivered for squad {squad_name}: {e}")
            return None

    def fetch_story_points_delivered_previous_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Trend baseline for Pulse Story Points Delivered: same sum, but for
        the comparison window immediately preceding the current one, same
        length as the current window (see JQLBuilder._previous_period_bounds),
        so the current period can be shown against it in the summary table."""
        try:
            jql = self.jql_builder.story_points_delivered_previous_query_by_squad(squad_name)
            fields = f'key,summary,issuetype,status,resolutiondate,{self.STORY_POINTS_FIELD}'
            issues = self.jira_client.jql(jql, fields=fields)

            metrics_data.story_points_delivered_previous_tickets = issues if issues else []
            metrics_data.story_points_delivered_previous_jql = jql

            total_points = self._sum_story_points(issues) if issues else 0.0

            previous_start, previous_end = self.jql_builder._previous_period_bounds()
            self._log_query_results("Pulse Story Points Delivered (Previous Period)", squad_name, jql, issues,
                                    f"Total story points delivered ({previous_start} to {previous_end}): {total_points:g}")

            return round(total_points, 1)

        except Exception as e:
            print(f"Error fetching previous story points delivered for squad {squad_name}: {e}")
            return None

    def fetch_backlog_pulse_story_points_by_squad(self, squad_name: str, metrics_data: MetricsData) -> Optional[float]:
        """Backlog Pulse Story Points: sum of Story Points - Pulse -
        Estimated across child issues (linked via Epic Link) of the
        squad's Submitted epics, where the child is still in the "To Do"
        status category and has a non-zero points value. A point-in-time
        backlog snapshot, not a rolling window. Always scoped to the
        central ENT project, same as Pulse Story Points Delivered."""
        identifier = squad_name
        try:
            epics_jql = self.jql_builder.backlog_pulse_epics_query_by_squad(squad_name)
            epics = self.jira_client.jql(epics_jql, fields='key,summary,issuetype,status')

            metrics_data.backlog_pulse_epics_tickets = epics if epics else []
            metrics_data.backlog_pulse_epics_jql = epics_jql

            epic_keys = [issue['key'] for issue in epics] if epics else []

            if not epic_keys:
                metrics_data.backlog_pulse_story_points_tickets = []
                metrics_data.backlog_pulse_story_points_jql = ""
                self._log_query_results("Backlog Pulse Story Points", identifier, epics_jql, [],
                                        "No Submitted epics found for squad - backlog is 0")
                return 0.0

            children_jql = self.jql_builder.backlog_pulse_story_points_query_by_epics(epic_keys)
            fields = f'key,summary,issuetype,status,{self.STORY_POINTS_FIELD}'
            children = self.jira_client.jql(children_jql, fields=fields)

            # skip issues with no points value or an explicit zero
            qualifying = []
            for issue in (children or []):
                raw = issue.get('fields', {}).get(self.STORY_POINTS_FIELD)
                if raw is None:
                    continue
                try:
                    if float(raw) == 0:
                        continue
                except (TypeError, ValueError):
                    continue
                qualifying.append(issue)

            metrics_data.backlog_pulse_story_points_tickets = qualifying
            metrics_data.backlog_pulse_story_points_jql = children_jql

            total_points = self._sum_story_points(qualifying)

            self._log_query_results("Backlog Pulse Story Points", identifier, children_jql, qualifying,
                                    f"{len(epic_keys)} Submitted epic(s); total backlog story points: {total_points:g}")

            return round(total_points, 1)

        except Exception as e:
            print(f"Error fetching backlog pulse story points for squad {squad_name}: {e}")
            return None
