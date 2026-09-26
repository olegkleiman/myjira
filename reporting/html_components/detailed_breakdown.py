"""
Detailed breakdown component - does the heavy lifting for metric analysis
"""

import html
from typing import Dict, List
from .base_generator import BaseHTMLGenerator, status_macro, highlight_attrs
from .metric_definitions import MetricDefinitions
from .table_generator import TableGenerator


class DetailedBreakdownGenerator(BaseHTMLGenerator):
    """Makes detailed breakdown analysis for all the project metrics"""
    
    def __init__(self, jira_base_url: str = "https://jira.verifone.com"):
        # setup for detailed breakdown generation
        super().__init__(jira_base_url)
        self.table_generator = TableGenerator({}, jira_base_url)
    
    def _format_multi_query_display(self, metric_key: str, project_metrics) -> str:
        # formats JQL query display - some metrics have multiple queries
        # so we need to handle both cases
        try:
            # these metrics need multiple queries to calculate properly
            multi_query_metrics = {
                "defects_resolution_rate": {
                    "queries": [
                        ("defects_resolution_created_jql", "INFLOW: Customer Defects Created", "defects_resolution_created_tickets"),
                        ("defects_resolution_resolved_jql", "OUTFLOW: Customer Defects Resolved", "defects_resolution_resolved_tickets")
                    ],
                    "calculation": "Resolved / Created * 100 = (OUTFLOW / INFLOW) * 100"
                },
                "customer_defect_reopen_rate": {
                    "queries": [
                        ("customer_defect_reopen_resolved_jql", "Total Customer Defects Resolved", "customer_defect_reopen_resolved_tickets"),
                        ("customer_defect_reopen_reopened_jql", "Customer Defects Reopened", "customer_defect_reopen_reopened_tickets")
                    ],
                    "calculation": "Reopened / Total Resolved * 100"
                },
                "customer_defect_fix_rate": {
                    "queries": [
                        ("customer_defect_fix_total_jql", "Total Customer Defects Created", "customer_defect_fix_total_tickets"),
                        ("customer_defect_fix_resolved_jql", "Customer Defects Resolved", "customer_defect_fix_resolved_tickets")
                    ],
                    "calculation": "Resolved / Total Created * 100"
                },
                "ontime_delivery_rate": {
                    "queries": [
                        ("ontime_delivery_jql", "Denominator: Epics delivered in last 30 days (status-history scoped)", "ontime_delivery_tickets"),
                        ("ontime_delivery_numerator_jql", "Numerator: Of those, resolved on or before Commit Date", "ontime_delivery_numerator_tickets")
                    ],
                    "calculation": "Epics resolved on or before Commit Date / Epics delivered in last 30 days with a Commit Date * 100"
                },
                "story_points_delivered": {
                    "queries": [
                        ("story_points_delivered_jql", "Current Period: Resolved in the report's date window", "story_points_delivered_tickets"),
                        ("story_points_delivered_previous_jql", "Previous Period: Resolved in the immediately preceding window of the same length", "story_points_delivered_previous_tickets")
                    ],
                    "calculation": "Sum of Story Points - Pulse - Estimated (customfield_18045) for Current Period vs Previous Period"
                },
                "backlog_pulse_story_points": {
                    "queries": [
                        ("backlog_pulse_epics_jql", "Query 1: Epics in Submitted status", "backlog_pulse_epics_tickets"),
                        ("backlog_pulse_story_points_jql", 'Query 2: Child issues (Epic Link) still in the "To Do" status category with a non-zero points value', "backlog_pulse_story_points_tickets")
                    ],
                    "calculation": "Sum of Story Points - Pulse - Estimated (customfield_18045) across non-zero-valued child issues (Epic Link) of the Submitted epics from Query 1"
                }
            }
            
            if metric_key in multi_query_metrics:
                # this one uses multiple queries
                config = multi_query_metrics[metric_key]
                html_parts = []
                
                # show the math formula first so people understand
                # (native info macro - a manual colored div loses its background/border on Cloud)
                html_parts.append(f'''
                <ac:structured-macro ac:name="info" ac:schema-version="1">
                    <ac:rich-text-body>
                        <p><strong>📊 Calculation Formula:</strong> {config['calculation']}</p>
                    </ac:rich-text-body>
                </ac:structured-macro>
                ''')
                
                # now show each individual query
                for i, (jql_attr, query_desc, tickets_attr) in enumerate(config['queries'], 1):
                    jql_query = getattr(project_metrics, jql_attr, "")
                    tickets = getattr(project_metrics, tickets_attr, [])
                    ticket_count = len(tickets) if tickets else 0
                    
                    if jql_query:
                        # Add red note for queries with Python-side filtering
                        note_html = ''
                        if metric_key == 'ontime_delivery_rate' and tickets_attr == 'ontime_delivery_tickets':
                            excluded_count = getattr(project_metrics, 'ontime_delivery_excluded_count', None)
                            if excluded_count:
                                note_html = f'<p style="color: #e74c3c; font-weight: bold; font-size: 13px;">Note: {excluded_count} epic(s) excluded above - no Commit Date (customfield_14768) set</p>'
                        elif metric_key == 'ontime_delivery_rate' and tickets_attr == 'ontime_delivery_numerator_tickets':
                            note_html = '<p style="color: #e74c3c; font-weight: bold; font-size: 13px;">Note: resolved &le; Commit Date (customfield_14768) checked in script; epics with no Commit Date excluded</p>'

                        # (plain text + code macro - the old bordered/shaded box loses its styling on Cloud)
                        html_parts.append(f'''
                        <p><strong>Query {i}: {query_desc}</strong> <span style="color: #666;">({ticket_count} issues found)</span></p>
                        {self._format_jql_display(jql_query)}
                        {note_html}
                        ''')
                    else:
                        html_parts.append(f'''
                        <p style="color: #666;"><strong>Query {i}: {query_desc}</strong> - No query executed</p>
                        ''')
                
                return ''.join(html_parts)
            else:
                # regular single-query metric - simpler case
                # some attributes have weird names, need mapping
                jql_attr_mappings = {
                    "hotfix_frequency": "hotfix_jql",
                    "ontime_delivery_rate": "ontime_delivery_jql"
                }
                
                jql_attr = jql_attr_mappings.get(metric_key, f"{metric_key}_jql")
                jql_query = getattr(project_metrics, jql_attr, "")
                
                if jql_query:
                    return self._format_jql_display(jql_query)
                else:
                    return '<p style="color: #95a5a6; font-style: italic;">No query executed (calculated metric or no data)</p>'
        except Exception as e:
            # if something goes wrong, just fall back to the old way
            jql_attr_mappings = {
                "hotfix_frequency": "hotfix_jql",
                "ontime_delivery_rate": "ontime_delivery_jql"
            }
            
            jql_attr = jql_attr_mappings.get(metric_key, f"{metric_key}_jql")
            jql_query = getattr(project_metrics, jql_attr, "")
            
            if jql_query:
                return self._format_jql_display(jql_query)
            else:
                return f'<p style="color: #e74c3c; font-style: italic;">Error displaying queries: {str(e)}</p>'
    
    def _get_calculation_details(self, metric_key: str, project_metrics, metric_value) -> str:
        # shows the calculation breakdown for complex metrics
        # helps people understand how we got the numbers
        try:
            # these metrics need special calculation display
            multi_query_calculations = {
                "defects_resolution_rate": {
                    "tickets": [
                        ("defects_resolution_created_tickets", "Created (Inflow)"),
                        ("defects_resolution_resolved_tickets", "Resolved (Outflow)")
                    ],
                    "formula": "Resolved ÷ Created × 100"
                },
                "customer_defect_reopen_rate": {
                    "tickets": [
                        ("customer_defect_reopen_resolved_tickets", "Total Resolved"),
                        ("customer_defect_reopen_reopened_tickets", "Reopened")
                    ],
                    "formula": "Reopened ÷ Total Resolved × 100"
                },
                "customer_defect_fix_rate": {
                    "tickets": [
                        ("customer_defect_fix_total_tickets", "Total Created"),
                        ("customer_defect_fix_resolved_tickets", "Resolved")
                    ],
                    "formula": "Resolved ÷ Total Created × 100"
                },
            }
            
            if metric_key in multi_query_calculations and metric_value is not None:
                config = multi_query_calculations[metric_key]
                counts = []
                
                # count up the tickets for each part
                for tickets_attr, label in config["tickets"]:
                    tickets = getattr(project_metrics, tickets_attr, [])
                    count = len(tickets) if tickets else 0
                    counts.append((count, label))
                
                if len(counts) >= 2:
                    denom_count, denom_label = counts[0]
                    num_count, num_label = counts[1]
                    result_badge = status_macro(f"{metric_value}%", "Blue")
                    return f'''
                    <ac:structured-macro ac:name="tip" ac:schema-version="1">
                        <ac:parameter ac:name="title">📊 Calculation Breakdown</ac:parameter>
                        <ac:rich-text-body>
                            <table>
                                <tr>
                                    <th style="text-align: left;"{highlight_attrs("grey")}>Component</th>
                                    <th style="text-align: center;"{highlight_attrs("grey")}>Count</th>
                                </tr>
                                <tr><td>{html.escape(denom_label)}</td><td style="text-align: center;">{denom_count}</td></tr>
                                <tr><td>{html.escape(num_label)}</td><td style="text-align: center;">{num_count}</td></tr>
                            </table>
                            <p><strong>Formula:</strong> {config['formula']}</p>
                            <p><strong>Result:</strong> {num_count} ÷ {denom_count} × 100 = {result_badge}</p>
                        </ac:rich-text-body>
                    </ac:structured-macro>
                    '''
            
            return ""
        except Exception as e:
            return f'<p style="color: #e74c3c; font-style: italic;">Error calculating details: {str(e)}</p>'
    
    def _get_performance_assessment(self, metric_key: str, metric_value, metric_info: Dict) -> str:
        # gives a quick assessment of how the metric looks
        if metric_value is None:
            return '<p style="color: #95a5a6; margin-top: 10px; font-style: italic;">No data available for assessment</p>'
        
        # basic assessment logic - could probably be smarter about thresholds
        if isinstance(metric_value, (int, float)) and metric_value == 0:
            assessment = "No issues found in this period"
            color = "#2ecc71"
        elif isinstance(metric_value, (int, float)) and metric_value > 0:
            assessment = "Activity detected - review individual issues for details"
            color = "#f39c12"
        else:
            assessment = "Data available - see individual issues below"
            color = "#3498db"
        
        return f'<p style="color: {color}; margin-top: 10px; font-style: italic;">Assessment: {assessment}</p>'
    
    def _get_metric_tickets(self, metric_key: str, project_metrics) -> List:
        # grabs the ticket list for a given metric
        ticket_attr_map = {
            "hotfix_frequency": "hotfix_tickets",
            "customer_found_defects": "customer_found_defect_tickets",
            "customer_defect_reopen_rate": "customer_defect_reopen_resolved_tickets",
            "customer_defect_fix_rate": "customer_defect_fix_total_tickets",
            "defects_resolution_rate": "defects_resolution_created_tickets",
            "release_frequency": "release_frequency_tickets",
            "ontime_delivery_rate": "ontime_delivery_tickets",
            "story_points_delivered": "story_points_delivered_tickets",
            "backlog_pulse_story_points": "backlog_pulse_story_points_tickets"
        }
        
        ticket_attr = ticket_attr_map.get(metric_key, "")
        if ticket_attr:
            return getattr(project_metrics, ticket_attr, [])
        return []
    
    def _create_enhanced_tickets_display(self, metric_key: str, tickets: List, project_metrics=None) -> str:
        # makes a nice ticket display with special handling for different types
        if not tickets:
            return '<p style="color: #95a5a6; font-style: italic;">No tickets found for this metric in the reporting period.</p>'

        # ODR gets two tables: denominator and numerator
        if metric_key == "ontime_delivery_rate" and project_metrics:
            denominator_tickets = getattr(project_metrics, "ontime_delivery_tickets", [])
            numerator_tickets = getattr(project_metrics, "ontime_delivery_numerator_tickets", [])
            html = self.table_generator.create_tickets_table(
                numerator_tickets,
                "Numerator: Epics resolved on or before Commit Date",
                enhanced=True,
                metric_key=metric_key,
                date_columns=['Created', 'Resolved', 'Commit Date'],
                date_fields=['created', 'resolutiondate', 'customfield_14768']
            )
            html += self.table_generator.create_tickets_table(
                denominator_tickets,
                "Denominator: Epics delivered in last 30 days (with a Commit Date)",
                enhanced=True,
                metric_key=metric_key,
                date_columns=['Created', 'Resolved', 'Commit Date'],
                date_fields=['created', 'resolutiondate', 'customfield_14768']
            )
            return html

        # Pulse Story Points Delivered gets two tables: current period, previous period
        if metric_key == "story_points_delivered" and project_metrics:
            current_tickets = getattr(project_metrics, "story_points_delivered_tickets", [])
            previous_tickets = getattr(project_metrics, "story_points_delivered_previous_tickets", [])
            html = self.table_generator.create_tickets_table(
                current_tickets,
                "Query 1: Current Period - Resolved in the report's date window",
                enhanced=True,
                metric_key=metric_key
            )
            html += self.table_generator.create_tickets_table(
                previous_tickets,
                "Query 2: Previous Period - Resolved in the immediately preceding window of the same length",
                enhanced=True,
                metric_key=metric_key
            )
            return html

        # Backlog Pulse Story Points gets two tables: the Submitted epics, and
        # their qualifying (still "To Do", non-zero points) child issues
        if metric_key == "backlog_pulse_story_points" and project_metrics:
            epic_tickets = getattr(project_metrics, "backlog_pulse_epics_tickets", [])
            child_tickets = getattr(project_metrics, "backlog_pulse_story_points_tickets", [])
            html = self.table_generator.create_tickets_table(
                epic_tickets,
                "Query 1: Epics in Submitted status",
                enhanced=True,
                metric_key=metric_key
            )
            html += self.table_generator.create_tickets_table(
                child_tickets,
                'Query 2: Child issues (Epic Link) still in the "To Do" status category with a non-zero points value',
                enhanced=True,
                metric_key=metric_key
            )
            return html

        # figure out if we should show date columns
        include_dates = metric_key in ["customer_found_defects",
                                     "customer_defect_fix_rate", "customer_defect_reopen_rate"]

        # for reopen rate, we need to highlight the actual reopened tickets
        reopened_ticket_keys = set()
        if metric_key == "customer_defect_reopen_rate" and project_metrics:
            reopened_tickets = getattr(project_metrics, "customer_defect_reopen_reopened_tickets", [])
            reopened_ticket_keys = {ticket.get('key') for ticket in reopened_tickets if ticket.get('key')}

        return self.table_generator.create_tickets_table(
            tickets,
            f"Tickets for {metric_key.replace('_', ' ').title()}",
            include_dates=include_dates,
            enhanced=True,
            metric_key=metric_key,
            reopened_ticket_keys=reopened_ticket_keys
        )
    
    def _create_comprehensive_metric_section(self, metric_key: str, metric_info: Dict, project_metrics, emoji_free: bool = False) -> str:
        # creates a comprehensive metric section with 4 parts
        # definition, queries, results, and individual tickets
        # get the metric value and see if we actually have data
        metric_value = getattr(project_metrics, metric_key.replace("_", "_"), None)
        has_data = metric_value is not None and (
            (isinstance(metric_value, (int, float)) and metric_value > 0) or
            (isinstance(metric_value, float) and metric_value >= 0)
        )
        
        # grab the JQL query used
        jql_attr = f"{metric_key}_jql"
        jql_query = getattr(project_metrics, jql_attr, "")
        
        # get the actual tickets for this metric
        tickets = self._get_metric_tickets(metric_key, project_metrics)
        
        # format the value nicely for display
        if metric_value is None:
            value_display = "No data available"
            value_colour = "Grey"
        elif isinstance(metric_value, float):
            if "rate" in metric_key.lower():
                value_display = f"{metric_value}%"
            elif metric_key == "story_points_delivered":
                previous = getattr(project_metrics, "story_points_delivered_previous", None)
                if previous is None:
                    value_display = f"{metric_value:g}"
                else:
                    value_display = f"{metric_value:g} (previous 30d: {previous:g})"
            elif metric_key == "backlog_pulse_story_points":
                value_display = f"{metric_value:g}"
            else:
                value_display = f"{metric_value} days"
            value_colour = "Green" if metric_value > 0 else "Red"
        else:
            value_display = f"{metric_value}"
            value_colour = "Green" if metric_value > 0 else "Red"

        panel_title = f"{self._get_metric_emoji(metric_key, emoji_free)} {metric_info['name']} - {metric_info['category']}".strip()

        # Panel macro replaces the old bordered <div> + colored header bar - Cloud
        # strips arbitrary background/border CSS on render, but macro parameters
        # like titleBGColor are honored since they aren't sanitized CSS.
        return f'''
        <ac:structured-macro ac:name="panel" ac:schema-version="1">
            <ac:parameter ac:name="title">{html.escape(panel_title)}</ac:parameter>
            <ac:parameter ac:name="titleBGColor">{metric_info['color']}</ac:parameter>
            <ac:parameter ac:name="titleColor">#FFFFFF</ac:parameter>
            <ac:parameter ac:name="borderColor">{metric_info['color']}</ac:parameter>
            <ac:rich-text-body>
                <!-- Part 1: JQL Queries Used -->
                <h4>{"" if emoji_free else "🔍 "}JQL Queries Used</h4>
                <p><strong>Calculation Method:</strong> {metric_info['calculation']}</p>
                {self._format_multi_query_display(metric_key, project_metrics)}

                <!-- Part 2: Results Summary -->
                <h4>{"" if emoji_free else "📈 "}Results Summary</h4>
                <p><strong>Current Value:</strong> {status_macro(value_display, value_colour)}</p>
                {self._get_calculation_details(metric_key, project_metrics, metric_value)}
                {self._get_performance_assessment(metric_key, metric_value, metric_info)}

                <!-- Part 3: Individual Issues -->
                <h4>{"" if emoji_free else "📋 "}Individual Issues</h4>
                {self._create_enhanced_tickets_display(metric_key, tickets, project_metrics)}
            </ac:rich-text-body>
        </ac:structured-macro>
        '''
    
    def create_detailed_breakdown_tables(self, metrics_data: Dict, emoji_free: bool = False) -> str:
        # creates detailed breakdown tables for all projects
        # uses 4-part structure: definition -> jql -> results -> issues
        if not metrics_data:
            return ""
        
        breakdown_html = []
        
        # add a nice section header
        section_emoji = "" if emoji_free else "📊 "
        breakdown_html.append(f'''
        <hr/>
        <h1 style="color: #2c3e50; text-align: center;">
            {section_emoji}Detailed Breakdown by Project
        </h1>
        <p style="text-align: center; color: #666; font-style: italic;">
            Complete metric analysis with definitions, JQL queries, and individual ticket details
        </p>
        ''')

        # always show all metrics for every project (even empty ones)
        metric_keys = [
            "hotfix_frequency", "customer_found_defects", "customer_defect_reopen_rate",
            "customer_defect_fix_rate",
            "defects_resolution_rate", "release_frequency", "ontime_delivery_rate",
            "story_points_delivered", "backlog_pulse_story_points"
        ]

        for project_name, project_metrics in metrics_data.items():
            if not project_metrics:
                continue

            # make a nice visual section for each project
            # (no outer colored box here - each metric below is already a Panel
            # macro, and Confluence Cloud doesn't support nesting panels)
            project_emoji = "" if emoji_free else "🏢 "
            breakdown_html.append(f'''
            <hr/>
            <h2 style="color: #2c3e50; text-align: center;">
                {project_emoji}{html.escape(project_name)} - Complete Metrics Analysis
            </h2>
            ''')

            # show all metrics even when there's no data - better than hiding stuff
            for metric_key in metric_keys:
                metric_info = MetricDefinitions.get_metric_info(metric_key)
                metric_section = self._create_comprehensive_metric_section(
                    metric_key, metric_info, project_metrics, emoji_free
                )
                breakdown_html.append(metric_section)

        return ''.join(breakdown_html)