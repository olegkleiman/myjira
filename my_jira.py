
from datetime import datetime, timedelta

from atlassian import Jira

class MyJira:
    def __init__(self, api_token, email, base_url, squad_name):
        self.api_token = api_token
        self.email = email
        self.base_url = base_url
        self.squad_name = squad_name

        self.jira = Jira(
            url=self.base_url,
            username=self.email,
            password=self.api_token,
            cloud=True
        )
        self.me = self.jira.myself()

    def epics(self, limit=50,fromDate=None, toDate=None):
        # Show the epics that are either still active, or were completed after 'fromDate'
        if fromDate is None:
            _fromDate = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            _fromDate = fromDate.strftime("%Y-%m-%d")
    
        jql = (
            'cf[14829] = "EMEA [IL] GPP" '
            'AND issuetype = Epic '
            'AND status not in (Submitted, Cancelled) '
            f'AND (statusCategory != Done OR resolved > "{_fromDate}") '
            'order by "Commit Date" ASC'
        )
        epics = self.jira.jql(jql, limit=limit) #, fields="summary, status, assignee, created, updated")
        issues_data = epics['issues'] if 'issues' in epics else []

        for issue_data in issues_data:
            self._parse_issue(issue_data)

        return  epics

    def _parse_issue(self, issue):

            fields = issue.get('fields', {})
            issue_key = issue.get('key', '')
            issue_summary = fields.get('summary', '')
            issue_status = fields.get('status', {}).get('name', '')
            assignee = fields.get('assignee') or {}
            issue_assignee = assignee.get('displayName', 'Unassigned')
            issue_created = fields.get('created', '')
            issue_updated = fields.get('updated', '')

            print(f"Issue Key: {issue_key}")
            print(f"Summary: {issue_summary}")
            print(f"Status: {issue_status}")
            print(f"Assignee: {issue_assignee}")
            print(f"Created: {issue_created}")
            print(f"Updated: {issue_updated}")
            print("-" * 40)