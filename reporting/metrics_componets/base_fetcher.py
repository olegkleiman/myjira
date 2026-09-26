"""
Base metrics fetcher - common stuff for all metric fetchers
"""

from datetime import datetime
from typing import List, Optional, Any
from atlassian import Jira

import logging
logger = logging.getLogger(__name__)

class BaseMetricsFetcher:
    """Base class with shared metric fetching utilities"""

    def __init__(self, 
                 jira_client: Jira, 
                 start_date: str, 
                 end_date: str):
        # basic setup for metrics fetching - callers always pass a resolved
        # (start_date, end_date) pair (see Config.metrics_start_date/metrics_end_date)
        self.jira_client = jira_client
        self.start_date = start_date
        self.end_date = end_date

    def _log_query_results(self, metric_name: str, project_key: str, jql: str, issues: List, additional_info: str = "") -> None:
        # log JQL query and results in a nice formatted way
        logger.info(f"\n{'=' * 80}")
        logger.info(f"{metric_name.upper()} - {project_key}")
        logger.info(f"{'=' * 80}")
        logger.info(f"JQL Query:")
        logger.info(f"   {jql.strip()}")
        logger.info(f"Results: {len(issues)} issues found")
        
        if additional_info:
            logger.info(f"Info: {additional_info}")
        
        if issues and len(issues) > 0:
            logger.info(f"Sample Issues (showing first 5):")
            logger.info(f"{'Key':<12} {'Type':<10} {'Status':<15} {'Created':<12} {'Updated':<12}")
            logger.info(f"{'-' * 70}")
            
            for issue in issues.get('issues', [])[:5]: # Show first 5 issues
                fields = issue.get('fields', {})
                key = issue.get('key', 'N/A')
                issue_type = fields.get('issuetype', {}).get('name', 'N/A') if fields.get('issuetype') else 'N/A'
                status = fields.get('status', {}).get('name', 'N/A') if fields.get('status') else 'N/A'
                created = fields.get('created', 'N/A')
                updated = fields.get('updated', 'N/A')
                
                # Format dates to show just the date part
                if created != 'N/A':
                    try:
                        created = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        created = created[:10] if len(created) >= 10 else created
                
                if updated != 'N/A':
                    try:
                        updated = datetime.fromisoformat(updated.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        updated = updated[:10] if len(updated) >= 10 else updated
                
                logger.info(f"{key:<12} {issue_type:<10} {status:<15} {created:<12} {updated:<12}")
        
        logger.info(f"{'=' * 80}\n")
