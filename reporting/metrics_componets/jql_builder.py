"""
JQL query builder - builds queries for metrics
"""

from datetime import datetime
from typing import List


class JQLBuilder:
    """Builds JQL queries for different metrics"""

    def __init__(self, start_date: str, end_date: str, squad_field: str = "customfield_14829"):
        # every query is scoped to this resolved (start_date, end_date) pair
        self.start_date = start_date
        self.end_date = end_date
        self.squad_field = squad_field

    def _upper_bound(self, field: str, end_date: str = None) -> str:
        """Upper-bound clause appended after a '>= start_date' clause."""
        end_date = end_date or self.end_date
        return f'\n            AND {field} <= "{end_date}"'

    def _changed_window(self, status_clause: str, start_date: str = None, end_date: str = None) -> str:
        """'status changed ... AFTER start_date BEFORE end_date'."""
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        return f'{status_clause} AFTER "{start_date}" BEFORE "{end_date}"'

    def _fixed_window_clause(self, field: str, start_date: str = None, end_date: str = None) -> str:
        """Bounds a field to the (start_date, end_date) metric window used
        by ODR / Story Points."""
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        return f'{field} >= "{start_date}" AND {field} <= "{end_date}"'

    def _previous_period_bounds(self) -> tuple:
        """Bounds of the comparison window immediately preceding the metric
        window, same length as that window."""
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        length = end - start
        previous_start = start - length
        return previous_start.strftime('%Y-%m-%d'), start.strftime('%Y-%m-%d')

    def _epic_status_history_clause(self, start_date: str = None, end_date: str = None) -> str:
        """Status-history scope for ODR: epics that were resident in
        Transition or Implementation at any point during the (start_date,
        end_date) metric window.

        WAS IN...DURING is used deliberately over 'changed to...during' - see
        epic status history semantics; do not simplify back to a changed-to
        filter. 'changed to' only catches transitions that happen inside the
        window, so it silently drops epics that entered the status before the
        window but were still sitting in it during the window.
        """
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        return f'status WAS IN ("Transition", "Implementation") DURING ("{start_date}", "{end_date}")'

    def _build_squad_filter(self, squad_name: str) -> str:
        """Build the squad filter portion of JQL query.

        Args:
            squad_name: Name of the squad

        Returns:
            JQL filter string for squad
        """
        # Use cf[XXXXX] format for custom fields in JQL
        field_id = self.squad_field.replace('customfield_', '')
        return f'cf[{field_id}] = "{squad_name}"'

    # ===== SQUAD-BASED QUERIES =====

    def customer_found_defects_query_by_squad(self, squad_name: str) -> str:
        """Build query for customer found defects by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND created >= "{self.start_date}"{self._upper_bound('created')}
            AND "Found by:" in ("Customer - Production")
        '''.strip()

    def customer_found_defects_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for CFDs: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND created >= "{previous_start}"{self._upper_bound('created', previous_end)}
            AND "Found by:" in ("Customer - Production")
        '''.strip()

    def hotfix_frequency_query_by_squad(self, squad_name: str) -> str:
        """Build query for hotfix frequency by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Release
            AND labels = "hotfix"
            AND "Prod EMEA Date" >= "{self.start_date}"{self._upper_bound('"Prod EMEA Date"')}
        '''.strip()

    def hotfix_frequency_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for Hotfix Frequency: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Release
            AND labels = "hotfix"
            AND "Prod EMEA Date" >= "{previous_start}"{self._upper_bound('"Prod EMEA Date"', previous_end)}
        '''.strip()

    def customer_defects_resolved_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for resolved customer defects by squad (denominator for CDRR)."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed to Done')}
        '''.strip()

    def customer_defects_resolved_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for CDRR denominator: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed to Done', previous_start, previous_end)}
        '''.strip()

    def customer_defects_reopened_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for reopened customer defects by squad (numerator for CDRR)."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed from Done')}
        '''.strip()

    def customer_defects_reopened_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for CDRR numerator: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed from Done', previous_start, previous_end)}
        '''.strip()

    def customer_defects_all_created_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for all created customer defects by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND created >= "{self.start_date}"{self._upper_bound('created')}
        '''.strip()

    def customer_defects_all_created_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for CDFR denominator: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND created >= "{previous_start}"{self._upper_bound('created', previous_end)}
        '''.strip()

    def customer_defects_resolved_with_fix_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for customer defects resolved with actual fixes by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed to Done')}
        '''.strip()

    def customer_defects_resolved_with_fix_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for CDFR numerator: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND "Found by:" in ("Customer - Production")
            AND {self._changed_window('status changed to Done', previous_start, previous_end)}
        '''.strip()

    def all_defects_created_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for all created defects (inflow) by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND created >= "{self.start_date}"{self._upper_bound('created')}
        '''.strip()

    def all_defects_created_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for DFR denominator (inflow): same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND created >= "{previous_start}"{self._upper_bound('created', previous_end)}
        '''.strip()

    def all_defects_resolved_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for all resolved defects (outflow) by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND {self._changed_window('status changed to Done')}
        '''.strip()

    def all_defects_resolved_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for DFR numerator (outflow): same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Defect
            AND {self._changed_window('status changed to Done', previous_start, previous_end)}
        '''.strip()

    def release_frequency_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for release frequency by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Release
            AND "Prod EMEA Date" >= "{self.start_date}"{self._upper_bound('"Prod EMEA Date"')}
        '''.strip()

    def release_frequency_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for Release Frequency: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Release
            AND "Prod EMEA Date" >= "{previous_start}"{self._upper_bound('"Prod EMEA Date"', previous_end)}
        '''.strip()

    def ontime_delivery_query_by_squad(self, squad_name: str) -> str:
        """Build JQL denominator query for ODR by squad - epics delivered
        (Done) in the (start_date, end_date) window, scoped to the epic
        status-history window. Cancelled epics are excluded since they were
        never delivered. Null Commit Date epics are excluded in Python
        post-fetch, not here."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Epic
            AND status = Done
            AND {self._fixed_window_clause('resolved')}
            AND {self._epic_status_history_clause()}
        '''.strip()

    def ontime_delivery_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for ODR denominator: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Epic
            AND status = Done
            AND {self._fixed_window_clause('resolved', previous_start, previous_end)}
            AND {self._epic_status_history_clause(previous_start, previous_end)}
        '''.strip()

    def ontime_delivery_numerator_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for the ODR numerator candidate pool by squad -
        same scope as the denominator (JQL can't compare resolved <= Commit
        Date since JQL doesn't support comparing one field's value against
        another field). The actual resolved <= Commit Date check, and the
        exclusion of epics with no Commit Date, happen in Python post-fetch
        (see delivery_metrics.py)."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            {squad_filter}
            AND issuetype = Epic
            AND status = Done
            AND {self._fixed_window_clause('resolved')}
            AND {self._epic_status_history_clause()}
        '''.strip()

    def ontime_delivery_numerator_previous_query_by_squad(self, squad_name: str) -> str:
        """Trend baseline for ODR numerator candidate pool: same query, previous comparison window."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            {squad_filter}
            AND issuetype = Epic
            AND status = Done
            AND {self._fixed_window_clause('resolved', previous_start, previous_end)}
            AND {self._epic_status_history_clause(previous_start, previous_end)}
        '''.strip()

    def story_points_delivered_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for story points delivered by squad - non-Epic
        issues resolved in the (start_date, end_date) window. Always scoped
        to the central ENT project - story points are tracked there."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            project = "ENT"
            AND issuetype != Epic
            AND {squad_filter}
            AND {self._fixed_window_clause('resolved')}
        '''.strip()

    def story_points_delivered_previous_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for the comparison window immediately preceding
        (start_date, end_date), same length as that window, used as the
        trend baseline for Pulse Story Points Delivered. Same scope as
        story_points_delivered_query_by_squad otherwise - central ENT
        project, non-Epic issues, squad filter."""
        squad_filter = self._build_squad_filter(squad_name)
        previous_start, previous_end = self._previous_period_bounds()
        return f'''
            project = "ENT"
            AND issuetype != Epic
            AND {squad_filter}
            AND resolved >= "{previous_start}" AND resolved < "{previous_end}"
        '''.strip()

    def backlog_pulse_epics_query_by_squad(self, squad_name: str) -> str:
        """Build JQL query for the epics feeding Backlog Pulse Story Points -
        Epics in Submitted status for the squad. A snapshot (not a rolling
        window). Always scoped to the central ENT project, same as Pulse
        Story Points Delivered - story points are tracked there."""
        squad_filter = self._build_squad_filter(squad_name)
        return f'''
            project = "ENT"
            AND {squad_filter}
            AND issuetype = Epic
            AND status = "Submitted"
        '''.strip()

    def backlog_pulse_story_points_query_by_epics(self, epic_keys: List[str]) -> str:
        """Build JQL query for the child issues of the given epics - the
        Backlog Pulse Story Points pool: issues linked via Epic Link to one
        of the Submitted epics, still in the "To Do" status category, with a
        Story Points - Pulse - Estimated value set (customfield_18045).
        "statusCategory = \"To Do\"" is used rather than "= Open" - this Jira
        instance's status categories are named "To Do" / "In Progress" /
        "Done" (there is no category literally named "Open", so that
        comparison silently matched zero issues). Zero point values are
        excluded in Python post-fetch, not here - the field is a text
        field, so JQL numeric comparison on it isn't reliable."""
        epic_list = ', '.join(epic_keys)
        return f'''
            project = "ENT"
            AND "Epic Link" in ({epic_list})
            AND statusCategory = "To Do"
            AND cf[18045] is not EMPTY
        '''.strip()

    # ===== SUPPORT CASES QUERIES =====

    def support_cases_created_query(self, squad_name: str, issue_type: str = "Support Case", environment: str = "all") -> str:
        """Build JQL query for all created support cases by squad."""
        squad_filter = self._build_squad_filter(squad_name)
        env_filter = ""
        if environment == "production":
            env_filter = 'AND "Found by:" in ("Customer - Production")'
        elif environment == "non_production":
            env_filter = 'AND ("Found by:" not in ("Customer - Production") OR "Found by:" is EMPTY)'
        return f'''
            {squad_filter}
            AND issuetype = "{issue_type}"
            {env_filter}
            AND created >= "{self.start_date}"{self._upper_bound('created')}
        '''.strip()

    def support_cases_resolved_query(self, squad_name: str, issue_type: str = "Support Case", environment: str = "all") -> str:
        """Build JQL query for resolved support cases by squad.

        IMPORTANT: Only counts cases that were CREATED in the timeframe.
        This ensures we're tracking the same cohort (created AND resolved within timeframe).
        """
        squad_filter = self._build_squad_filter(squad_name)
        env_filter = ""
        if environment == "production":
            env_filter = 'AND "Found by:" in ("Customer - Production")'
        elif environment == "non_production":
            env_filter = 'AND ("Found by:" not in ("Customer - Production") OR "Found by:" is EMPTY)'
        return f'''
            {squad_filter}
            AND issuetype = "{issue_type}"
            {env_filter}
            AND created >= "{self.start_date}"{self._upper_bound('created')}
            AND resolved >= "{self.start_date}"{self._upper_bound('resolved')}
            AND status in (Done, Resolved, Closed)
        '''.strip()
