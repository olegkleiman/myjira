from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any, Optional, Tuple

from atlassian import Jira

from models import EpicProgressInfo, EpicData, JiraIssue, JiraStatus, JiraProject, JiraVersion
from reporting.metrics_componets.squad_metrics_data_fetcher import SquadMetricsDataFetcher
from reporting.metrics_componets.support_cases_metrics import SupportCasesMetricsFetcher

from config.config_loader import load_config, Config, ConfigurationError

import logging
logger = logging.getLogger(__name__)

class MyJira:
    def __init__(self, 
                 api_token, 
                 email, 
                 base_url, 
                 squad_name,
                 trends_enabled,
                 config_file: str = 'config.yaml'):
        self.api_token = api_token
        self.email = email
        self.base_url = base_url
        self.squad_name = squad_name
        self.trends_enabled = trends_enabled

        self.config = load_config(config_file)

        self.jira = Jira(
            url=self.base_url,
            username=self.email,
            password=self.api_token,
            cloud=True
        )
        self.me = self.jira.myself()

        # os.environ() raises KeyError if the environment variable is not set
        self.field_mappings: Dict[str, str] = {
            'epic_name' : os.environ['epic_name'],
            'story_points_field' : os.environ['story_points_pulse_estimated'],
            'commit_date' : os.environ['commit_date'],
            'comments' : os.environ['comments'],
            'fixed_version' : os.environ['fixed_version'],
            'epic_statuses_excluded' : os.environ.get('epic_statuses_excluded', 'Submitted,Cancelled').split(','),
            'rag_status' : os.environ['rag_status']
        }

        self.max_result=os.environ.get('max_result', 1000)  # Default to 1000 if not set
        self.max_workers = int(os.environ.get('max_workers', '6'))  # Default to 6 if not set

        self.metrics_timeframe_days = int(os.environ['timeframe_days'])
        self._resolved_start_date, self._resolved_end_date = self._resolve_date_range(
            None, None, self.metrics_timeframe_days)

        # Squad-based metrics fetcher
        self.squad_metrics_fetcher = SquadMetricsDataFetcher(
            self.jira,
            self.squad_name,
            max_workers=self.max_workers,
            start_date=self._resolved_start_date,
            end_date=self._resolved_end_date,
            trends_enabled=self.trends_enabled
        )

        self.support_cases_fetcher = SupportCasesMetricsFetcher(
            self.jira,
            self.config.support_cases_issue_type,
            start_date=self._resolved_start_date,
            end_date=self._resolved_end_date
        )

    def epics(self, from_date=None, to_date=None) -> List[JiraIssue]:
        """Fetch epics for the squad. Returns a list of JiraIssue objects."""
        if from_date is None:
            _fromDate = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            _fromDate = from_date.strftime("%Y-%m-%d")
    
        jql = (
            f'cf[14829] = "{self.squad_name}" '
            'AND issuetype = Epic '
            f'AND status not in ({",".join(self.field_mappings["epic_statuses_excluded"])}) '
            f'AND (statusCategory != Done OR resolved > "{_fromDate}") '
            'order by "Commit Date" ASC'
        )
        logger.info("Fetching epics by squad from Jira...")
        epics_data = self.jira.jql(jql, limit=self.max_result)
        issues_data = epics_data.get('issues', [])
        
        return [self._parse_issue(issue_data, self.field_mappings) for issue_data in issues_data]

    def metrics(self, from_date=None):
        return self.squad_metrics_fetcher.fetch_all_metrics()

    def support_metrics(self, from_date=None):
        return self.support_cases_fetcher.fetch_support_cases_metrics_by_squad(self.squad_name)

    def _parse_issue(self, issue_data: Dict[str, Any], field_mappings: Dict[str, str]) -> JiraIssue:
        # parse issue data from API response into JiraIssue model
        fields = issue_data.get('fields', {})
        
        # Parse basic fields
        issue_key = issue_data.get('key', '')
        summary = fields.get(field_mappings.get('epic_name', 'summary'), '')
        
        # Parse status
        status_data = fields.get('status', {})
        status = self._parse_status(status_data)
        
        # Parse project
        project_data = fields.get('project', {})
        project = self._parse_project(project_data)
        
        # Parse custom fields
        rag_status_field = fields.get(field_mappings.get('rag_status'))
        rag_status = rag_status_field.get('value', '') if rag_status_field else ''
        
        commit_date = fields.get(field_mappings.get('commit_date'))
        due_date = fields.get('duedate')
        comments_raw = fields.get(field_mappings.get('comments'), '')
        # Jira Cloud v3 returns rich text fields as ADF (dict) - extract plain text
        comments = self._extract_adf_text(comments_raw) if isinstance(comments_raw, dict) else (comments_raw or '')
        
        # Parse fixed versions
        fixed_versions_data = fields.get(field_mappings.get('fixed_version', 'fixVersions'), [])
        fixed_versions = [self._parse_version(v) for v in fixed_versions_data if v]
        
        return JiraIssue(
            key=issue_key,
            summary=summary,
            status=status,
            project=project,
            epic_name=summary,  # For epics, summary is the epic name
            rag_status=rag_status,
            commit_date=commit_date,
            due_date=due_date,
            comments=comments,
            fixed_versions=fixed_versions
        )

    def _parse_status(self, status_data: Dict[str, Any]) -> JiraStatus:
        # parse status data from API response
        status_category = status_data.get('statusCategory', {})
        return JiraStatus(
            name=status_data.get('name', ''),
            status_category_key=status_category.get('key', '')
        )

    def _parse_project(self, project_data: Dict[str, Any]) -> JiraProject:
        # parse project data from API response
        return JiraProject(
            key=project_data.get('key', ''),
            name=project_data.get('name', '')
        )       

    def get_epic_progress(self, 
                          epic_key: str, 
                          story_points_field: Optional[str] = None) -> EpicProgressInfo:


            jql = f'"Epic Link" = {epic_key}'
            fields = ['status'] + ([story_points_field] if story_points_field else [])
   
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

                if story_points_field:
                    for child_issue in child_issues:
                        child_fields = child_issue.get('fields', {})
                        child_status = child_fields.get('status', {}).get('name', '')
                        raw_story_points = child_fields.get(story_points_field, 0)

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
                logger.error(f"Error fetching child issues for epic {epic_key}: {e}")
                return EpicProgressInfo(done_count=0, total_count=0)

    def _extract_adf_text(self, adf_data: Any) -> str:
        """Extract plain text from Jira's ADF (Atlassian Document Format) structure."""
        if not isinstance(adf_data, dict):
            return str(adf_data) if adf_data else ''
        
        text_parts = []
        
        # ADF documents have a 'content' array with blocks
        if 'content' in adf_data:
            for block in adf_data['content']:
                if block.get('type') == 'paragraph':
                    content = block.get('content', [])
                    for item in content:
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
        
        return ''.join(text_parts)

    def _parse_version(self, version_data: Dict[str, Any]) -> JiraVersion:
        """Parse a version object from Jira API response."""
        return JiraVersion(name=version_data.get('name', ''))

    @staticmethod
    def _resolve_date_range(start_date: Optional[str], 
                            end_date: Optional[str],
                            timeframe_days: int) -> Tuple[str, str]:
        if start_date and end_date:
            return start_date, end_date
        end = datetime.now()
        start = end - timedelta(days=timeframe_days)
        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')    

    @property
    def metrics_start_date(self) -> str:
        # resolved start date (YYYY-MM-DD) for all queries - either the
        # explicit report.start_date, or today - timeframe_days
        return self._resolved_start_date

    @property
    def metrics_end_date(self) -> str:
        # resolved end date (YYYY-MM-DD) for all queries - either the
        # explicit report.end_date, or today
        return self._resolved_end_date    