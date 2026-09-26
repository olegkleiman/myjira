"""
Metrics table generation - builds the summary table for all projects
"""

import html
import re
from typing import Dict, List, Optional
from .base_generator import BaseHTMLGenerator, highlight_attrs


class MetricsTableGenerator(BaseHTMLGenerator):
    """Makes the metrics summary table for all projects"""

    def __init__(self, jira_base_url: str = "https://jira.verifone.com", metrics_thresholds: Optional[Dict[str, int]] = None,
                 start_date: str = None, end_date: str = None, trends_enabled: bool = True):
        # basic setup for metrics table generator
        super().__init__(jira_base_url)
        self.metrics_thresholds = metrics_thresholds or {
            'green': 90, 'amber': 75}
        self.start_date = start_date
        self.end_date = end_date
        self.trends_enabled = trends_enabled

    def _period_label(self) -> str:
        """Human-readable label for the reporting period, used in the
        metrics table heading and definitions blurb."""
        return f"{self.start_date} to {self.end_date}"

    @staticmethod
    def _format_number(value) -> str:
        # drop trailing .0 for whole-number counts (e.g. story points sums)
        return f"{value:g}" if isinstance(value, float) else str(value)

    def _format_trend_value(self, current, previous, suffix: str = "") -> str:
        """Render a value with a trend indicator against the prior period,
        e.g. "30" on one line, then a smaller muted "▼ (-50%) (60)" on the
        next: current value, direction arrow, percent change, then the
        previous-period value in parens. `suffix` (e.g. "%") is appended to
        both the current and previous displayed values, but percent-change
        is always computed on the raw numeric values. An unchanged value
        (current == previous) collapses the trend line to a bare muted
        dash instead, so a flat period doesn't visually compete with actual
        moves."""
        current_str = f"<strong>{self._format_number(current)}{suffix}</strong>"

        if previous is None:
            return current_str

        if current == previous:
            return f'{current_str}<br><span style="color: #95a5a6; font-size: 10px;">–</span>'

        arrow = "▲" if current > previous else "▼"

        if previous == 0:
            pct_str = "new" if current > 0 else "0%"
        else:
            pct = ((current - previous) / previous) * 100
            pct_str = f"{pct:+.0f}%" if round(pct) != 0 else "0%"

        previous_str = f"{self._format_number(previous)}{suffix}"
        trend_str = f'<span style="color: #95a5a6; font-size: 10px;">{arrow} ({pct_str}) ({previous_str})</span>'
        return f"{current_str}<br>{trend_str}"

    def _get_metric_value(self, metrics_data: Dict, project_key: str, metric: str) -> str:
        # gets the metric value for a project
        # returns placeholder if no data exists
        if not metrics_data or project_key not in metrics_data:
            return "-" if "Rate" in metric else "—"

        project_metrics = metrics_data[project_key]

        # map the display names to actual data attributes
        metric_mapping = {
            "Hotfix Frequency": project_metrics.hotfix_frequency,
            "Customer Found Defects (CFDs)": project_metrics.customer_found_defects,
            "Customer Defect Reopen Rate (CDRR)": project_metrics.customer_defect_reopen_rate,
            "Customer Defect Fix Rate (CDFR)": project_metrics.customer_defect_fix_rate,
            "Defects Resolution Rate (DFR)": project_metrics.defects_resolution_rate,
            "Release Frequency": project_metrics.release_frequency,
            "On-time Delivery Rate (ODR)": project_metrics.ontime_delivery_rate,
            "Pulse Story Points Delivered": project_metrics.story_points_delivered,
            "Backlog Pulse Story Points": project_metrics.backlog_pulse_story_points,
        }

        # comparison-window value for every metric except Backlog Pulse
        # Story Points, which is a point-in-time snapshot with no trend
        previous_mapping = {
            "Hotfix Frequency": project_metrics.hotfix_frequency_previous,
            "Customer Found Defects (CFDs)": project_metrics.customer_found_defects_previous,
            "Customer Defect Reopen Rate (CDRR)": project_metrics.customer_defect_reopen_rate_previous,
            "Customer Defect Fix Rate (CDFR)": project_metrics.customer_defect_fix_rate_previous,
            "Defects Resolution Rate (DFR)": project_metrics.defects_resolution_rate_previous,
            "Release Frequency": project_metrics.release_frequency_previous,
            "On-time Delivery Rate (ODR)": project_metrics.ontime_delivery_rate_previous,
            "Pulse Story Points Delivered": project_metrics.story_points_delivered_previous,
        }

        value = metric_mapping.get(metric)

        if value is None:
            return "-" if "Rate" in metric else "—"

        if metric == "Backlog Pulse Story Points":
            return f"<strong>{self._format_number(value)}</strong>"

        suffix = "%" if "Rate" in metric else ""
        previous = previous_mapping.get(metric) if self.trends_enabled else None
        return self._format_trend_value(value, previous, suffix=suffix)

    @staticmethod
    def _leading_number(value: str) -> Optional[float]:
        """Extract the leading numeric token from a (possibly HTML-wrapped,
        trend-annotated) cell value like '<strong>85%</strong><br>...', for
        threshold-based coloring. Strips HTML tags first since the value/trend
        markup would otherwise land inside the "leading token"."""
        stripped = re.sub(r'<[^>]+>', '', value)
        match = re.match(r'-?\d+(?:\.\d+)?', stripped)
        return float(match.group()) if match else None

    def _get_metric_cell_attrs(self, value: str, metric: str = "") -> str:
        """Return style + native highlight attrs for metric cells based on thresholds.

        Confluence Cloud strips arbitrary `background` CSS on render, so status
        coloring has to go through the native highlight attribute instead (fixed
        palette: grey/red/yellow/green - not our exact hex shades).

        Thresholds are evaluated against the metric's own SLA rule, not the
        trend direction, for every metric except Pulse Story Points Delivered
        (which has no SLA and is colored by trend direction instead)."""
        style = ' style="padding: 10px 12px; text-align: center; vertical-align: middle;"'
        if value in ["-", "—"]:
            return style + highlight_attrs("grey")

        numeric = self._leading_number(value)

        if metric == "Release Frequency":
            if numeric is None:
                return style
            if numeric == 0:
                return style + highlight_attrs("red")
            return style
        if metric == "Customer Found Defects (CFDs)":
            if numeric is None:
                return style
            if numeric == 0:
                return style + highlight_attrs("green")
            return style
        if metric == "Customer Defect Reopen Rate (CDRR)":
            if numeric is None:
                return style
            green = self.metrics_thresholds.get('green', 90)
            amber = self.metrics_thresholds.get('amber', 75)
            inverted = 100 - numeric
            if inverted >= green:
                return style + highlight_attrs("green")
            if inverted >= amber:
                return style + highlight_attrs("yellow")
            return style + highlight_attrs("red")
        if metric == "Hotfix Frequency":
            if numeric is None:
                return style
            if numeric == 0:
                return style + highlight_attrs("green")
            return style + highlight_attrs("red")
        if metric == "Pulse Story Points Delivered":
            if "▲" in value:
                return style + highlight_attrs("green")
            if "▼" in value:
                return style + highlight_attrs("red")
            return style + highlight_attrs("grey")
        if "Rate" in metric:
            if numeric is None:
                return style
            green = self.metrics_thresholds.get('green', 90)
            amber = self.metrics_thresholds.get('amber', 75)
            if numeric >= green:
                return style + highlight_attrs("green")
            if numeric >= amber:
                return style + highlight_attrs("yellow")
            return style + highlight_attrs("red")
        return style

    def create_metrics_table(self, metrics_data: Dict = None, subpage_urls: Dict[str, str] = None,
                             display_name_mappings: Dict[str, str] = None, project_keys: List[str] = None) -> str:
        # creates the main execution-review metrics table
        # shows all projects and their metrics in a nice grid

        # if no project keys provided, extract from metrics_data
        if not project_keys:
            if metrics_data:
                project_keys = list(metrics_data.keys())
            else:
                # no projects to display
                project_keys = []

        # use display names as headers if provided
        project_headers = display_name_mappings if display_name_mappings else {
            key: key for key in project_keys}

        # group metrics into quality and throughput categories
        quality_metrics = [
            "Hotfix Frequency",
            "Customer Found Defects (CFDs)",
            "Customer Defect Reopen Rate (CDRR)",
            "Customer Defect Fix Rate (CDFR)"
        ]

        throughput_metrics = [
            "Defects Resolution Rate (DFR)",
            "Release Frequency",
            "On-time Delivery Rate (ODR)"
        ]

        output_metrics = [
            "Pulse Story Points Delivered"
        ]

        def squad_cell_html(project_key: str) -> str:
            # renders the row-label cell for a squad, linking to its subpage if available
            header_name = project_headers.get(project_key, project_key)
            display_name = display_name_mappings.get(
                project_key, project_key) if display_name_mappings else project_key

            if subpage_urls and display_name in subpage_urls:
                squad_display = f'<a href="{subpage_urls[display_name]}" target="_blank" style="color: #0066cc; text-decoration: none;">{html.escape(header_name)}</a>'
            else:
                squad_display = html.escape(header_name)

            return f'<td style="padding: 10px 12px; text-align: left; vertical-align: middle; color: #0066cc; font-weight: bold;"{highlight_attrs("grey")}>{squad_display}</td>'

        # each category gets its own highlight color so the header forms a
        # colored band that visually groups its columns down both header rows
        categories = [
            ("Quality", quality_metrics, "blue"),
            ("Throughput", throughput_metrics, "grey"),
            ("Output", output_metrics, "blue"),
        ]

        # build the table header - squads as rows, metrics as columns grouped by category
        category_header_cells = [
            f'<th rowspan="2" style="padding: 10px 12px; text-align: left; vertical-align: middle; font-weight: bold; font-size: 13px;"{highlight_attrs("grey")}>Squad</th>']
        metric_header_cells = []
        for category_name, category_metrics, category_color in categories:
            category_header_cells.append(
                f'<th colspan="{len(category_metrics)}" style="padding: 10px 12px; text-align: center; vertical-align: middle; font-weight: bold; font-size: 13px;"{highlight_attrs(category_color)}>{category_name}</th>')
            for metric in category_metrics:
                metric_header_cells.append(
                    f'<th style="padding: 8px 10px; text-align: center; vertical-align: middle; font-weight: bold; font-size: 12px;"{highlight_attrs(category_color)}>{html.escape(metric)}</th>')

        header_row = (
            f"<tr>{''.join(category_header_cells)}</tr>"
            f"<tr>{''.join(metric_header_cells)}</tr>"
        )

        # build all the data rows - one per squad
        data_rows = []
        for project_key in project_keys:
            cells = [squad_cell_html(project_key)]
            for _, category_metrics, _ in categories:
                for metric in category_metrics:
                    value = self._get_metric_value(
                        metrics_data, project_key, metric)
                    cell_attrs = self._get_metric_cell_attrs(value, metric)
                    cells.append(f'<td{cell_attrs}>{value}</td>')
            data_rows.append(f"<tr>{''.join(cells)}</tr>")

        # put together the main table
        metrics_table = f"""
    <h2>Execution-Review Projects – Metrics (Avg per {self._period_label()})</h2>
    <table style="width: 100%; margin-top: 20px; font-size: 14px;">
        {header_row}
        {''.join(data_rows)}
    </table>
"""

        # Backlog Pulse Story Points is a point-in-time snapshot, not an
        # average over the reporting period, so it gets its own table
        # instead of a column in the averaged metrics table above.
        backlog_header_row = (
            f'<tr><th style="padding: 10px 12px; text-align: left; vertical-align: middle; font-weight: bold; font-size: 13px;"{highlight_attrs("grey")}>Squad</th>'
            f'<th style="padding: 10px 12px; text-align: center; vertical-align: middle; font-weight: bold; font-size: 13px;"{highlight_attrs("grey")}>Backlog Pulse Story Points</th></tr>'
        )

        backlog_rows = []
        for project_key in project_keys:
            value = self._get_metric_value(
                metrics_data, project_key, "Backlog Pulse Story Points")
            cell_attrs = self._get_metric_cell_attrs(
                value, "Backlog Pulse Story Points")
            backlog_rows.append(
                f"<tr>{squad_cell_html(project_key)}<td{cell_attrs}>{value}</td></tr>")

        backlog_table = f"""
    <h2>Backlog Pulse Story Points (Snapshot)</h2>
    <table style="width: auto; margin-top: 20px; font-size: 14px;">
        {backlog_header_row}
        {''.join(backlog_rows)}
    </table>
"""

        return metrics_table + backlog_table

    def create_metric_definitions_section(self) -> str:
        # definitions for every metric shown in the summary table
        trend_blurb = (
            '<p><em>Trend: every metric except Backlog Pulse Story Points shows its '
            'current-period value against the prior period of equal length, e.g. '
            '"30 &#9650; (+20%) (25)" - value, direction arrow, percent change, then '
            'the prior-period value in parens.</em></p>'
        ) if self.trends_enabled else ""
        return f"""
    <h3>Metric Definitions</h3>
    <p><em>All the metrics below are cumulative average per month over {self._period_label()}.</em></p>
    {trend_blurb}
    <ul>
        <li><strong>Hotfix Frequency:</strong> Number of 'hotfix'-labelled Release issues released in the period.</li>
        <li><strong>Customer Found Defects (CFDs):</strong> Number of customer-reported issues assigned to engineering.</li>
        <li><strong>Customer Defect Reopen Rate (CDRR):</strong> Percentage of resolved customer defects that were later reopened.</li>
        <li><strong>Customer Defect Fix Rate (CDFR):</strong> Percentage of customer defects resolved.</li>
        <li><strong>Defects Resolution Rate (DFR):</strong> Percentage of defects created in the period that were also resolved in it.</li>
        <li><strong>Release Frequency:</strong> Number of Release issues with a Prod EMEA Date in the period.</li>
        <li><strong>On-time Delivery Rate (ODR):</strong> Percentage of epics delivered in the trailing 30 days that were resolved by their Commit Date. Excludes epics without a Commit Date.</li>
        <li><strong>Pulse Story Points Delivered:</strong> Story points delivered by the squad in the trailing 30 days vs. the prior 30 days.</li>
        <li><strong>Backlog Pulse Story Points:</strong> Snapshot of story points in Submitted story-level issues in the squad's Submitted epics.</li>
    </ul>
"""
