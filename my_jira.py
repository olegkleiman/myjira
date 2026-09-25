
from datetime import datetime, timedelta
import os
import asyncio

from atlassian import Jira

from models import EpicProgressInfo, JiraIssue, JiraStatus, JiraProject, JiraVersion

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

        # raises KeyError if the environment variable is not set
        self.story_points_field = os.environ['story_points_pulse_estimated']
        self.rag_status = os.environ['rag_status']
        self.max_result=os.environ.get('max_result', 1000)  # Default to 1000 if not set
        self.max_workers = int(os.environ.get('max_workers', '6'))  # Default to 6 if not set
        self.epic_statuses_excluded = os.environ.get('epic_statuses_excluded', 'Submitted,Cancelled').split(',')

    async def epics(self, fromDate=None, toDate=None):
        # Show the epics that are either still active, or were completed after 'fromDate'
        if fromDate is None:
            _fromDate = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            _fromDate = fromDate.strftime("%Y-%m-%d")
    
        jql = (
            f'cf[14829] = "{self.squad_name}" '
            'AND issuetype = Epic '
            f'AND status not in ({",".join(self.epic_statuses_excluded)}) '
            f'AND (statusCategory != Done OR resolved > "{_fromDate}") '
            'order by "Commit Date" ASC'
        )
        epics = self.jira.jql(jql, limit=self.max_result)

        tasks = [asyncio.to_thread(self.get_epic_progress,epic) for epic in epics['issues']]
        results = await asyncio.gather(*tasks)

        issues_data = epics['issues'] if 'issues' in epics else []

        for issue_data in issues_data:

            self._parse_issue(issue_data)

        return  epics

    def _parse_issue(self, issue):

            fields = issue.get('fields', {})
            issue_key = issue.get('key', '')
            issue_summary = fields.get('summary', '')
            issue_status = fields.get('status', {}).get('name', '')

            issue_status_category_key = fields.get('status', {}).get('statusCategory', {}).get('key', '')
            jira_status = JiraStatus(name=issue_status, status_category_key=issue_status_category_key)

            project = fields.get('project', {})
            jira_project = JiraProject(key=project.get('key', ''), 
                                       name=project.get('name', ''))

            jira_issue = JiraIssue(
                key=issue_key,
                summary=issue_summary,
                status=jira_status,
                project=jira_project
            )

            assignee = fields.get('assignee') or {}
            issue_assignee = assignee.get('displayName', 'Unassigned')
            issue_created = fields.get('created', '')
            issue_updated = fields.get('updated', '')

            story_points_field = self.story_points_field
            raw_story_points = fields.get(story_points_field, 0) if story_points_field else 0

            if raw_story_points:
                try:
                    story_points = float(raw_story_points)
                except (ValueError, TypeError):
                    story_points = 0.0

            JiraEpicProgressInfo = EpicProgressInfo(done_count=0, total_count=0)

            print(f"Issue Key: {issue_key}")
            print(f"Summary: {issue_summary}")
            print(f"Status: {issue_status}")
            print(f"Assignee: {issue_assignee}")
            print(f"Created: {issue_created}")
            print(f"Updated: {issue_updated}")
            print("-" * 40)

            return EpicProgressInfo()

    def get_epic_progress(self, epic) -> EpicProgressInfo:

            issue_key = epic.get('key', '')
            
            jql = f'"Epic Link" = {issue_key}'
            try:
                data = self.jira.jql(jql, limit=self.max_result)
                child_issues = data.get('issues', [])
                total_count = len(child_issues)
                done_count = sum(
                    1 for issue in child_issues
                    if issue['fields'].get('status', {}).get('statusCategory', {}).get('key') == 'done'
                )                

                story_points_done = 0.0
                story_points_total = 0.0

                if self.story_points_field:
                    for child_issue in child_issues:
                        child_fields = child_issue.get('fields', {})
                        child_status = child_fields.get('status', {}).get('name', '')
                        raw_story_points = child_fields.get(self.story_points_field, 0)

                        try:
                            story_points = float(raw_story_points) if raw_story_points else 0.0
                        except (ValueError, TypeError):
                            story_points = 0.0

                        story_points_total += story_points

                        if child_status.lower() == 'done':
                            story_points_done += story_points

                return EpicProgressInfo(
                    done_count=done_count,
                    total_count=total_count,
                    story_points_done=round(story_points_done, 1),
                    story_points_total=round(story_points_total, 1)
                )                            

            except Exception as e:  
                print(f"Error fetching child issues for epic {issue_key}: {e}")
                return EpicProgressInfo(done_count=0, total_count=0)