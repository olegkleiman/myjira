"""
Base HTML generator - common stuff that other generators use
"""

import html
from datetime import datetime
from typing import Optional


def highlight_attrs(color: Optional[str]) -> str:
    """Confluence Cloud strips arbitrary background/border CSS on render - cell
    backgrounds only survive via this native highlight attribute (fixed palette:
    grey, red, yellow, green, blue, purple)."""
    if not color:
        return ""
    return f' class="highlight-{color}" data-highlight-colour="{color}"'


def status_macro(title: str, colour: str) -> str:
    """Confluence's native colored lozenge - renders reliably where a CSS
    background on a span/div would get stripped."""
    return (
        '<ac:structured-macro ac:name="status" ac:schema-version="1">'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f'<ac:parameter ac:name="title">{html.escape(str(title))}</ac:parameter>'
        '</ac:structured-macro>'
    )


def code_macro(text: str) -> str:
    """Confluence's native code block - also gives us a real monospace box
    without relying on CSS that Cloud would strip."""
    safe = text.replace(']]>', ']]]]><![CDATA[>')
    return (
        '<ac:structured-macro ac:name="code" ac:schema-version="1">'
        '<ac:parameter ac:name="language">text</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[{safe}]]></ac:plain-text-body>'
        '</ac:structured-macro>'
    )


class BaseHTMLGenerator:
    """Base class with shared HTML helpers"""
    
    def __init__(self, jira_base_url: str = "https://jira.verifone.com"):
        # basic setup - just store the jira URL for now
        self.jira_base_url = jira_base_url
    
    def _create_rag_status_badge(self, rag_status: str) -> str:
        # renders RAG status as a native Confluence status lozenge
        rag_status_lower = (rag_status or '').lower()

        if rag_status_lower == 'green':
            return status_macro('ON TRACK', 'Green')
        elif rag_status_lower == 'amber':
            return status_macro('AT RISK', 'Yellow')
        elif rag_status_lower == 'red':
            return status_macro('OFF TRACK', 'Red')
        else:
            return status_macro(rag_status or 'UNKNOWN', 'Grey')

    def _is_commit_date_overdue(self, commit_date: str, is_done: bool) -> bool:
        # flags a commit date that's in the past for an epic that isn't fully done
        if is_done or not commit_date:
            return False
        try:
            return datetime.strptime(commit_date, '%Y-%m-%d').date() < datetime.now().date()
        except Exception:
            return False

    def _format_commit_date(self, commit_date: str, is_overdue: bool = False) -> str:
        # cleans up the date format for display
        # handles the ISO date parsing
        if not commit_date:
            return ''

        try:
            formatted = datetime.strptime(commit_date, '%Y-%m-%d').strftime('%d %b %Y')
        except Exception:
            formatted = commit_date

        if is_overdue:
            return f'<span style="color: #e74c3c; font-weight: bold;">{formatted}</span>'
        return formatted
    
    def _create_epic_link(self, issue_key: str, epic_name: str) -> str:
        # builds a clickable link to the epic in jira
        escaped_name = html.escape(epic_name)
        return f'<a href="{self.jira_base_url}/browse/{issue_key}" target="_blank">{issue_key}</a> - {escaped_name}'
    
    def _format_jql_display(self, jql_query: str) -> str:
        # formats JQL queries as a native Confluence code block
        # (a manual <div><pre> box would lose its background/border on Cloud)
        if not jql_query:
            return ""

        return f'''
        <p><strong>JQL Query:</strong></p>
        {code_macro(jql_query)}
        '''
    
    def _format_date_display(self, date_str: str) -> str:
        # makes dates look nicer with relative time info
        if date_str == 'N/A' or not date_str:
            return '<span style="color: #95a5a6;">N/A</span>'
        
        try:
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            formatted = parsed_date.strftime('%Y-%m-%d')
            
            # add "X days ago" for recent dates - makes it easier to read
            days_ago = (datetime.now() - parsed_date.replace(tzinfo=None)).days
            if days_ago == 0:
                relative = "Today"
            elif days_ago == 1:
                relative = "Yesterday" 
            elif days_ago < 7:
                relative = f"{days_ago} days ago"
            elif days_ago < 30:
                relative = f"{days_ago // 7} weeks ago"
            else:
                relative = f"{days_ago // 30} months ago"
            
            return f'{formatted} <small style="color: #666;">({relative})</small>'
        except:
            # if date parsing fails, just show whatever we can
            return date_str[:10] if len(date_str) >= 10 else date_str
    
    def _format_status_display(self, status: str, is_reopened: bool = False, status_category_key: str = '') -> str:
        # colors the status text by Jira's own status category (To Do/In
        # Progress/Done) rather than guessing from the status name, so custom
        # statuses (e.g. "Blocked", "Ready for QA") still get the right color
        if is_reopened:
            return f'<span style="color: #e74c3c; font-weight: bold;">{html.escape(status)}</span>'
        elif status_category_key == 'done':
            return f'<span style="color: #27ae60; font-weight: bold;">{html.escape(status)}</span>'
        elif status_category_key == 'indeterminate':
            return f'<span style="color: #3498db; font-weight: bold;">{html.escape(status)}</span>'
        elif status_category_key == 'new':
            return f'<span style="color: #7f8c8d; font-weight: bold;">{html.escape(status)}</span>'
        else:
            return html.escape(status)
    
    def _get_metric_emoji(self, metric_key: str, emoji_free: bool = False) -> str:
        # picks the right emoji for each metric type
        if emoji_free:
            return ""
        
        emoji_map = {
            "hotfix_frequency": "🚨",
            "customer_found_defects": "🐛", 
            "customer_defect_reopen_rate": "🔄",
            "customer_defect_fix_rate": "🔧",
            "defects_resolution_rate": "🎯",
            "release_frequency": "🚀",
            "ontime_delivery_rate": "📅",
            "story_points_delivered": "📈"
        }
        return emoji_map.get(metric_key, "📊")