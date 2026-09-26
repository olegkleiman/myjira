"""
Table generation stuff - makes epic status tables and ticket lists
"""

import html
from typing import Dict, List
from .base_generator import BaseHTMLGenerator, highlight_attrs, status_macro
from models import EpicData


class TableGenerator(BaseHTMLGenerator):
    """Makes epic status tables and ticket displays"""
    
    def __init__(self, table_config: Dict[str, str], jira_base_url: str = "https://jira.verifone.com"):
        # setup with table config and jira URL
        super().__init__(jira_base_url)
        self.table_config = table_config
    
    def create_table_row(self, epic: EpicData, progress_bar: str, indent_px: int = 0,
                       story_points_progress_bar: str = '', is_alt_row: bool = False) -> str:
        # builds one table row for an epic
        # includes progress bar and all the details
        # grab the column widths
        epic_width = self.table_config['epic_name_width']
        status_width = self.table_config['status_width']
        rag_status_width = self.table_config['rag_status_width']
        stories_progress_width = self.table_config['stories_progress_width']
        date_width = self.table_config['delivery_date_width']
        pulse_story_points_width = self.table_config['pulse_story_points_width']

        # build the pieces we need
        epic_link = self._create_epic_link(epic.issue_key, epic.epic_name)
        status_display = self._format_status_display(epic.status_name, status_category_key=epic.status_category_key)
        rag_badge = self._create_rag_status_badge(epic.rag_status)
        is_done = epic.total_count > 0 and epic.done_count >= epic.total_count
        is_overdue = self._is_commit_date_overdue(epic.commit_date, is_done)
        commit_date_str = self._format_commit_date(epic.commit_date, is_overdue)

        # zebra-stripe alternating rows for readability on long tables (native
        # highlight attr - a CSS background here would get stripped by Confluence Cloud)
        row_bg = highlight_attrs("grey") if is_alt_row else ""

        # assemble the actual table row
        # (border/background dropped - Confluence Cloud strips box CSS on render;
        # its default table grid supplies the borders instead)
        return (
            f"<tr>"
            f"<td style='padding: 8px; padding-left: {8 + indent_px}px; width: {epic_width};'{row_bg}>{epic_link}</td>"
            f"<td style='padding: 8px; width: {status_width};'{row_bg}>{status_display}</td>"
            f"<td style='padding: 8px; width: {rag_status_width}; text-align: center;'{row_bg}>{rag_badge}</td>"
            f"<td style='padding: 8px; width: {date_width};'{row_bg}>{commit_date_str}</td>"
            f"<td style='padding: 8px; width: {stories_progress_width};'{row_bg}>{progress_bar}</td>"
            f"<td style='padding: 8px; width: {pulse_story_points_width};'{row_bg}>{story_points_progress_bar}</td>"
            f"</tr>"
        )
    
    def create_project_header_row(self, project_name: str, subpage_url: str = None, indent_px: int = 0) -> str:
        # makes a header row that spans all columns
        # for project names
        escaped_project = html.escape(project_name)
        padding_style = f"padding-left: {10 + indent_px}px;"
        
        if subpage_url:
            project_display = f'<b><a href="{subpage_url}" target="_blank" style="color: #0066cc;">{escaped_project}</a></b> <small style="color: #666;">(click for detailed analysis)</small>'
        else:
            project_display = f'<b>{escaped_project}</b>'
        
        return (
            f'<tr>'
            f'<td colspan="6" style="padding: 8px; {padding_style}"{highlight_attrs("grey")}>'
            f'{project_display}'
            f'</td>'
            f'</tr>'
        )

    def create_squad_header_row(self, squad_name: str, subpage_url: str = None) -> str:
        # top-level squad row
        escaped = html.escape(squad_name)
        if subpage_url:
            squad_display = f'<a href="{subpage_url}" target="_blank" style="color: #0066cc;">{escaped}</a> <small>(click for detailed analysis)</small>'
        else:
            squad_display = escaped
        return (
            f"<tr>"
            f"<td colspan=\"6\" style='padding: 10px; font-weight: bold;'{highlight_attrs('blue')}>"
            f"{squad_display}"
            f"</td>"
            f"</tr>"
        )
    
    def create_tickets_table(self, tickets: List, title: str, include_dates: bool = False,
                           enhanced: bool = False, metric_key: str = "",
                           reopened_ticket_keys: set = None,
                           date_columns: list = None, date_fields: list = None) -> str:
        # builds a table showing ticket details
        # can include dates and highlight reopened ones
        # date_columns/date_fields: custom date column headers and corresponding field names
        if not tickets:
            return f'<p style="color: #95a5a6; font-style: italic;">No {title.lower()} found in the specified timeframe.</p>'

        # setup the column headers
        no_type_metrics = {"hotfix_frequency", "defects_resolution_rate", "release_frequency", "ontime_delivery_rate"}
        headers = ['Key', 'Summary', 'Status'] if metric_key in no_type_metrics else ['Key', 'Summary', 'Type', 'Status']
        if date_columns:
            headers.extend(date_columns)
        elif include_dates:
            headers.extend(['Created', 'Resolved/Closed'])

        header_row = ''.join([f'<th style="padding: 10px; font-weight: bold; text-align: left;"{highlight_attrs("grey")}>{header}</th>' for header in headers])
        
        # make all the data rows
        rows = []
        for ticket in tickets[:20]:  # only show first 20 so the page doesn't get too crazy
            fields = ticket.get('fields', {})
            
            # get the basic ticket info
            key = ticket.get('key', 'N/A')
            summary = fields.get('summary', 'N/A')
            issue_type = fields.get('issuetype', {}).get('name', 'N/A') if fields.get('issuetype') else 'N/A'
            status = fields.get('status', {}).get('name', 'N/A') if fields.get('status') else 'N/A'
            status_category_key = fields.get('status', {}).get('statusCategory', {}).get('key', '') if fields.get('status') else ''
            
            # check if this ticket got reopened - only matters for defect metrics
            defect_metrics = ["customer_defect_reopen_rate", "customer_defect_fix_rate", "customer_found_defects"]
            is_reopened = (reopened_ticket_keys and key in reopened_ticket_keys) if metric_key in defect_metrics else False

            # truncate long summaries so they don't mess up the table layout
            if len(summary) > 80:
                summary = summary[:77] + "..."

            # make the ticket key clickable and add reopened tag if needed
            key_display = f'<a href="{self.jira_base_url}/browse/{key}" target="_blank" style="color: #0066cc; font-weight: bold;">{key}</a>'
            if is_reopened:
                key_display += ' ' + status_macro('REOPENED', 'Red')
            
            if metric_key in no_type_metrics:
                row_data = [
                    key_display,
                    html.escape(summary),
                    self._format_status_display(status, is_reopened, status_category_key)
                ]
            else:
                row_data = [
                    key_display,
                    html.escape(summary),
                    html.escape(issue_type),
                    self._format_status_display(status, is_reopened, status_category_key)
                ]
            
            if date_columns and date_fields:
                for field_name in date_fields:
                    # Handle synthetic fixVersion fields
                    if field_name == '_fixVersion_name':
                        fix_versions = fields.get('fixVersions', [])
                        val = ', '.join(fv.get('name', '') for fv in fix_versions if fv.get('name')) if fix_versions else 'N/A'
                        formatted = html.escape(val) if val != 'N/A' else '<span style="color: #95a5a6;">N/A</span>'
                    elif field_name == '_fixVersion_releaseDate':
                        fix_versions = fields.get('fixVersions', [])
                        dates = [fv.get('releaseDate') for fv in fix_versions if fv.get('releaseDate')]
                        val = ', '.join(dates) if dates else 'N/A'
                        formatted = self._format_date_display(val) if val != 'N/A' and ',' not in val else (html.escape(val) if val != 'N/A' else '<span style="color: #95a5a6;">N/A</span>')
                    else:
                        val = fields.get(field_name, 'N/A')
                        formatted = self._format_date_display(val) if val and val != 'N/A' else '<span style="color: #95a5a6;">N/A</span>'
                    row_data.append(formatted)
            elif include_dates:
                created = fields.get('created', 'N/A')
                resolved = fields.get('resolutiondate', 'N/A')

                # make the dates look nicer
                created_formatted = self._format_date_display(created)
                resolved_formatted = self._format_date_display(resolved) if resolved != 'N/A' else '<span style="color: #95a5a6;">Not closed</span>'

                row_data.extend([created_formatted, resolved_formatted])
            
            row_cells = ''.join([f'<td style="padding: 10px; vertical-align: top;">{data}</td>' for data in row_data])
            rows.append(f'<tr>{row_cells}</tr>')
        
        # show how many tickets we found
        total_count = len(tickets)
        displayed_count = min(20, total_count)
        count_info = f' (showing {displayed_count} of {total_count})' if total_count > 20 else f' ({total_count} total)'
        
        # count up reopened tickets if we're in enhanced mode
        defect_metrics = ["customer_defect_reopen_rate", "customer_defect_fix_rate", "customer_found_defects"]
        reopened_count = 0
        if enhanced and metric_key in defect_metrics and reopened_ticket_keys:
            reopened_count = sum(1 for ticket in tickets if ticket.get('key') in reopened_ticket_keys)
        reopened_info = f' | <span style="color: #e74c3c; font-weight: bold;">{reopened_count} reopened</span>' if reopened_count > 0 else ''
        
        table_html = f'''
        <div style="margin: 15px 0;">
            <p style="font-weight: bold;">{title}{count_info}{reopened_info}</p>
            <table style="width: 100%; font-size: 13px;">
                <thead>
                    <tr>{header_row}</tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        '''
        
        return table_html
