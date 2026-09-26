#!/usr/bin/env python3

import datetime
import os
import asyncio
import sys
from collections import defaultdict
from atlassian import Jira
from typing import Dict, List
import logging

from timing import Timings
from concurrent.futures import ThreadPoolExecutor

from my_jira import MyJira
from my_confluence import MyConfluence
from models import EpicData
from reporting.html_components.html_generator import HTMLGenerator

def setup_logging():
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    # formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    # handler.setFormatter(formatter)

    root_logger = logging.getLogger()  # root logger, no name = affects everything
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(handler)

async def main():

    """Main execution flow"""
    logger.info("Starting Squad-Based Execution Review Generation")
    logger.info("=" * 80)

    try:
        my_api_token = os.getenv("JIRA_API_TOKEN")
        my_email = os.getenv("E_MAIL")
        jira_base_url = os.getenv("JIRA_BASE_URL")
        my_squad_name = os.getenv("SQUAD_NAME")
        trends_enabled = os.getenv('trends_enabled')
        timeframe_days = int(os.getenv('timeframe_days'))

        timings = Timings()

        myJira = MyJira(my_api_token, my_email, jira_base_url, my_squad_name, trends_enabled)
        fromDate = datetime.datetime.now() - datetime.timedelta(days=timeframe_days)
        with timings.measure("Fetch epics by squad"):
            all_epics = myJira.epics(from_date=fromDate)
            logger.info(f"  Found {len(all_epics)} epics for squad: {my_squad_name}")

        with ThreadPoolExecutor(max_workers=6) as executor:
                progress_by_epic = list(executor.map(
                    lambda epic: myJira.get_epic_progress(epic.key, 
                                                          myJira.field_mappings['story_points_field']),
                    all_epics
                ))
        logger.info(f"  Fetched progress for {len(progress_by_epic)} epics")

        project_epics_by_squad: Dict[str, Dict[str, List[EpicData]]] = defaultdict(lambda: defaultdict(list))
        for epic, progress_info in zip(all_epics, progress_by_epic):
            epic_data = EpicData(
                issue_key=epic.key,
                epic_name=epic.epic_name or epic.summary,
                rag_status=epic.rag_status or '',
                commit_date=epic.commit_date or '',
                due_date=epic.due_date or '',
                fixed_versions=epic.fixed_version_names,
                comments=epic.comments or '',
                done_count=progress_info.done_count,
                total_count=progress_info.total_count,
                project_name=epic.project_name,
                story_points_done=progress_info.story_points_done,
                story_points_total=progress_info.story_points_total,
                status_name=epic.status.name,
                status_category_key=epic.status.status_category_key
            )
            project_epics_by_squad[my_squad_name][epic.project_name].append(epic_data)

        squad_epics: Dict[str, Dict] = {}
        for squad_name, project_epics in project_epics_by_squad.items():
            squad_epics[squad_name] = dict(project_epics)

        # Fetch metrics by squad
        logger.info("\n" + "=" * 80)
        logger.info("FETCHING SQUAD METRICS")
        logger.info("=" * 80)
        with timings.measure("Fetch squad metrics"):
            squad_metrics = myJira.metrics(from_date=fromDate)

        # Fetch support cases metrics if enabled
        support_cases_metrics = {}
        # if self.support_cases_enabled:
        with timings.measure("Fetch support cases metrics"):
            support_cases_metrics = myJira.support_metrics()            

        html_content = generate_html_report(my_squad_name, squad_epics, squad_metrics)

        confluence_base_url = os.getenv("CONFLUENCE_BASE_URL")
        myConfluence = MyConfluence(my_api_token, my_email, confluence_base_url)
        
        # page_hierarchy = myConfluence.page_hierarchy
        grandparent_title = 'Execution Reviews'
        grandparent_page = myConfluence.get_page_by_title(space='EEE', title=grandparent_title)
        if not grandparent_page:
            logger.error(f"Grandparent page '{grandparent_title}' not found.")
            raise ValueError("Grandparent page not found.")     
        
        grandparent_page_id = grandparent_page['id']
        logger.info(f"Grandparent page '{grandparent_title}' found with ID: {grandparent_page_id}")

        new_page = myConfluence.create_page(space='EEE', 
                                title='delete_me', 
                                # body='<p>Content is storage format</p>', 
                                body=html_content,
                                parent_id=grandparent_page_id, 
                                representation='storage')
        logger.info(f"New page created with ID: {new_page['id']} and title: {new_page['title']}")

    except KeyError as e:
        logger.error(f"Key error occurred: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


def generate_html_report(squad_name: str, 
                         squad_epics: Dict, 
                         squad_metrics: Dict):
    """Generate complete HTML report with squad-based organization"""
    logger.info("Generating HTML report...")

    table_config = {    
        'epic_name_width': os.environ.get('epic_name_width', '8%'),
        'status_width': os.environ.get('status_width', '8%'),
        'rag_status_width': os.environ.get('rag_status_width', '8%'),
        'stories_progress_width': os.environ.get('stories_progress_width', '16%'),
        'delivery_date_width': os.environ.get('delivery_date_width', '10%'),
        'due_date_width': os.environ.get('due_date_width', '10%'),
        'comments_width': os.environ.get('comments_width', '30%'),
        'pulse_story_points_width': os.environ.get('pulse_story_points_width', '30%')
    }

    html_generator = HTMLGenerator(table_config,
                                    jira_base_url="https://jira.verifone.com")

    # Transform squad epics to project groups for HTML generator
    # Structure: squad_name → project_key → List[html_rows]
    squad_project_groups = {}

    for project_epics in squad_epics:
        squad_project_groups[squad_name] = {}

        for project_key, epics in project_epics.items():
            rows = []
            pass

    html_content = html_generator.generate_html_report(grouped_rows=squad_epics)
    return html_content

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    asyncio.run(main())