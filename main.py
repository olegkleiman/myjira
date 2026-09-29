#!/usr/bin/env python3

from datetime import datetime, timedelta, date
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

def make_clickable_link(url: str, text: str = None) -> str:
    """Wrap a URL in an OSC 8 escape sequence so terminals render it as a clickable link."""
    label = text if text is not None else url
    return f"\033]8;;{url}\033\\{label}\033]8;;\033\\"

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
        end_date = datetime.now()
        start_date = end_date - timedelta(days=timeframe_days)
        with timings.measure("Fetch epics by squad"):
            all_epics = myJira.epics(from_date = start_date)
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
            squad_metrics = myJira.metrics(from_date=start_date)

        # Fetch support cases metrics if enabled
        support_cases_metrics = {}
        # if self.support_cases_enabled:
        with timings.measure("Fetch support cases metrics"):
            support_cases_metrics = myJira.fetch_support_cases_metrics()            

        confluence_base_url = os.getenv("CONFLUENCE_BASE_URL")
        myConfluence = MyConfluence(my_api_token, my_email, confluence_base_url)

        page_hierarchy = myConfluence.page_hierarchy
        grandparent_title = page_hierarchy['grandparent_title'] #Execution Reviews'
        space_key = myConfluence.space_key
        grandparent_page = myConfluence.get_page_by_title(space=space_key, title=grandparent_title)
        if not grandparent_page:
            logger.error(f"Grandparent page '{grandparent_title}' not found.")
            raise ValueError("Grandparent page not found.")
        
        grandparent_page_id = grandparent_page['id']
        logger.info(f"Grandparent page '{grandparent_title}' found with ID: {grandparent_page_id}")                          

        with timings.measure("Generate main HTML report"):
            html_content = myConfluence.generate_html_report(my_squad_name, 
                                                            squad_epics, 
                                                            squad_metrics,
                                                            support_cases_metrics,
                                                            start_date = start_date.strftime("%Y-%m-%d"),
                                                            end_date = end_date.strftime("%Y-%m-%d")) 

        # Create main page
        logger.info("\n" + "=" * 80)
        logger.info("PUBLISHING TO CONFLUENCE")
        logger.info("=" * 80)

        stub_marker = 'delete_me '
        page_title = myConfluence.generate_page_title(
            page_hierarchy['page_title_template'],
            date_range = _report_date_label(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )

        with timings.measure("Create Confluence main page"):
            new_page = myConfluence.create_page(
                                space=myConfluence.space_key, 
                                title=stub_marker + squad_name + page_title,
                                body=html_content,
                                parent_id=grandparent_page_id, 
                                representation='storage'
            )   
            logger.info(f"New page created with ID: {new_page['id']} and title: {new_page['title']}")
            page_url = f"{confluence_base_url}/pages/viewpage.action?pageId={new_page['id']}"
        

        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION REVIEW COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"Report available at: {make_clickable_link(page_url)}")

        timings.print_summary()

    except KeyError as e:
        logger.error(f"Key error occurred: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

def _report_date_label(start_date: datetime, end_date: datetime) -> str:
    """Label identifying the reporting period, used in page/subpage titles."""
    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)
    
    # 2. Changed .date to .day for the start day number
    start = f"{start_dt.strftime('%b')} {start_dt.day}"
    
    # 3. Formatted the end string (using %Y for a 4-digit year)
    end = f"{end_dt.strftime('%b')} {end_dt.day}, {end_dt.strftime('%Y')}"
    
    return f"{start} - {end}"

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    asyncio.run(main())