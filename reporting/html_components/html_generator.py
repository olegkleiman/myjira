"""
Main HTML generator orchestrator that brings together all components.
"""

import html
import os
import datetime
from typing import Dict, List, Optional
from .base_generator import BaseHTMLGenerator, highlight_attrs
from .table_generator import TableGenerator
from .metrics_table import MetricsTableGenerator
from .detailed_breakdown import DetailedBreakdownGenerator
from .support_cases_table import SupportCasesTableGenerator
from models import EpicData


class HTMLGenerator(BaseHTMLGenerator):
    """Main HTML generator - basically pulls everything together"""
    
    def __init__(
        self,
        table_config: Dict[str, str],
        jira_base_url: str = "https://jira.verifone.com",
        metrics_thresholds: Dict[str, int] = None,
        metrics_start_date: Optional[str] = None,
        metrics_end_date: Optional[str] = None,
        trends_enabled: bool = True,
    ):
        # setup the generator with table config and jira url
        super().__init__(jira_base_url)
        self.table_config = table_config

        # setup the sub-generators we'll need
        self.table_generator = TableGenerator(table_config, jira_base_url)
        self.metrics_table_generator = MetricsTableGenerator(
            jira_base_url, metrics_thresholds=metrics_thresholds,
            start_date=metrics_start_date, end_date=metrics_end_date,
            trends_enabled=trends_enabled
        )
        self.detailed_breakdown_generator = DetailedBreakdownGenerator(jira_base_url)
        self.support_cases_table_generator = SupportCasesTableGenerator()
    
    # just pass things along to the right component
    def create_table_row(self, epic: EpicData, progress_bar: str, indent_px: int = 0,
                       story_points_progress_bar: str = '', is_alt_row: bool = False) -> str:
        # make a table row for an epic
        return self.table_generator.create_table_row(epic, progress_bar, indent_px, story_points_progress_bar, is_alt_row)
    
    def create_project_header_row(self, project_name: str, subpage_url: str = None, indent_px: int = 0) -> str:
        # create the header row that spans across columns
        return self.table_generator.create_project_header_row(project_name, subpage_url, indent_px)

    def create_squad_header_row(self, squad_name: str, subpage_url: str = None) -> str:
        # top-level squad row
        return self.table_generator.create_squad_header_row(squad_name, subpage_url)
    
    def create_metrics_table(self, metrics_data: Dict = None, subpage_urls: Dict[str, str] = None,
                           display_name_mappings: Dict[str, str] = None, project_keys: List[str] = None) -> str:
        # build the main metrics summary table
        return self.metrics_table_generator.create_metrics_table(metrics_data, subpage_urls, display_name_mappings, project_keys)

    def create_metric_definitions_section(self) -> str:
        # build the metric definitions glossary
        return self.metrics_table_generator.create_metric_definitions_section()

    def create_detailed_breakdown_tables(self, metrics_data: Dict, emoji_free: bool = False) -> str:
        # creates the big detailed tables with all the breakdown info
        return self.detailed_breakdown_generator.create_detailed_breakdown_tables(metrics_data, emoji_free)
    
    def generate_html_report(self, grouped_rows: Dict[str, List[str]],
                           metrics_data: Dict = None,
                           subpage_urls: Dict[str, str] = None,
                           display_name_mappings: Dict[str, str] = None,
                           project_keys: List[str] = None,
                           support_cases_metrics: Dict = None) -> str:
        # generates the full HTML report
        # takes all the pieces and puts them together into one page
        # grab the column widths from config

        epic_width = self.table_config['epic_name_width']
        status_width = self.table_config['status_width']
        rag_status_width = self.table_config['rag_status_width']
        stories_progress_width = self.table_config['stories_progress_width']
        date_width = self.table_config['delivery_date_width']
        pulse_story_points_width = self.table_config['pulse_story_points_width']

        # build all the table rows (allow callers to pass fully composed rows)
        if isinstance(grouped_rows, list):
            all_rows = grouped_rows
        else:
            all_rows = []
            for project in sorted(grouped_rows.keys()):
                project_rows = grouped_rows[project]
                subpage_url = subpage_urls.get(project) if subpage_urls else None
                all_rows.append(self.create_project_header_row(project, subpage_url))
                all_rows.extend(project_rows)
        
        # make the metrics table with links to subpages
        metrics_table = self.create_metrics_table(metrics_data, subpage_urls, display_name_mappings, project_keys)
        metric_definitions = self.create_metric_definitions_section()

        # detailed breakdowns are on separate pages now (keeps main page cleaner)
        detailed_breakdown = ""

        # Support cases section (optional)
        support_cases_section = ""
        if support_cases_metrics:
            support_cases_section = (
                "<hr/>"
                "<h1 style=\"color: #2c3e50;\">"
                "Support Cases Metrics"
                "</h1>"
                f"{self.support_cases_table_generator.generate_table(support_cases_metrics)}"
            )

        # assemble the complete HTML - Confluence storage format is a body-only
        # fragment, so no <html>/<head>/<style>/<body> wrapper (Cloud strips those,
        # unlike Server/DC which passed them through). Colored dividers and box
        # backgrounds/borders are dropped too - Cloud's renderer strips arbitrary
        # background/border CSS, so we lean on the Info macro and native table
        # highlight attrs instead, and just accept Confluence's default table grid
        # and plain <hr/> where no native alternative exists.
        html_content = f"""
    <!-- Main metrics section -->
    <h1 style="color: #2c3e50;">Metrics Summary</h1>
    {metrics_table}

    {support_cases_section}

    <hr/>

    <!-- Epic status table -->
    <h1 style="color: #2c3e50;">Epic Status Table</h1>
    <table style="width: 100%;">
        <colgroup>
            <col style="width: {epic_width};" />
            <col style="width: {status_width};" />
            <col style="width: {rag_status_width};" />
            <col style="width: {date_width};" />
            <col style="width: {stories_progress_width};" />
            <col style="width: {pulse_story_points_width};" />
        </colgroup>
        <tr>
            <th style="padding: 8px; text-align: left; font-weight: bold; width: {epic_width};"{highlight_attrs("grey")}>Epic Name</th>
            <th style="padding: 8px; text-align: left; font-weight: bold; width: {status_width};"{highlight_attrs("grey")}>Status</th>
            <th style="padding: 8px; text-align: center; font-weight: bold; width: {rag_status_width};"{highlight_attrs("grey")}>RAG Status</th>
            <th style="padding: 8px; text-align: left; font-weight: bold; width: {date_width};"{highlight_attrs("grey")}>Commit Date</th>
            <th style="padding: 8px; text-align: left; font-weight: bold; width: {stories_progress_width};"{highlight_attrs("grey")}>Progress by Stories Number</th>
            <th style="padding: 8px; text-align: left; font-weight: bold; width: {pulse_story_points_width};"{highlight_attrs("grey")}>Progress by Pulse Story Points (On Stories)</th>
        </tr>
        {''.join(all_rows)}
    </table>

    <hr/>

    {metric_definitions}
"""
        return html_content
