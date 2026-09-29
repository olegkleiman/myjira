
from typing import Dict, Optional, Any

from datetime import datetime
import os
import requests
from atlassian import ConfluenceV2
from config.config_loader import load_config
from reporting.html_components.html_generator import HTMLGenerator
from reporting.html_components.progress_bar import ProgressBarGenerator

import logging
logger = logging.getLogger(__name__)

class ConfluenceAPIError(Exception):
    """Exception for Confluence API errors"""
    pass

class MyConfluence:
    def __init__(self, 
                 api_token, 
                 email, 
                 base_url, 
                 config_file: str = 'config.yaml'):
        base_url = base_url.rstrip('/')
        if base_url.endswith('/wiki'):
            base_url = base_url[:-5]

        self.confluence = ConfluenceV2(
            url=base_url,
            username=email,
            password=api_token,
            cloud=True
        )
        self._page_hierarchy: Dict[str, str] = {}

        self.config = load_config(config_file)

        self.progress_bar_generator = ProgressBarGenerator(
            self.config.progress_bar_config
        )

    @property
    def page_hierarchy(self) -> Dict[str, str]:
        return self.config.confluence['page_hierarchy']

    @property
    def space_key(self):
        return self.config.confluence['space_key']

    def generate_page_title(self, template: str, date_range: str) -> str:
        # generate page title from template - {date_range} is the report's
        # (start_date, end_date) span, {generated_date} is always today, the
        # day the report is actually being published
        generated_date = datetime.now().strftime('%Y-%m-%d')
        return template.format(date_range=date_range, generated_date=generated_date)        

    def get_page_by_title(self, space, title) -> Optional[Dict]:
        response = self.confluence.get_page_by_title(space, title, expand='ancestors')
        results = response.get("results", [])
        return results[0] if results else None

    def create_page(self, space, title, body, parent_id=None, representation=None):
        space_data = self.confluence.get_space_by_key(space)
        space_id = space_data['id'] if isinstance(space_data, dict) else space_data

        try:
            return self.confluence.create_page(
                space_id=space_id,
                title=title,
                body=body,
                parent_id=parent_id,
                representation=representation,
            )
        except requests.exceptions.HTTPError as error:
            response = error.response
            status_code = response.status_code if response is not None else 'unknown'
            response_text = response.text.strip() if response is not None else str(error)
            raise RuntimeError(
                f'Confluence page creation failed ({status_code}): {response_text}'
            ) from error

    def update_page(self, page_id, title, body):
        return self.confluence.update_page(page_id, title=title, body=body)

    def find_page_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        # find page by title in the space
        endpoint = "/rest/api/content"
        params = {
            'title': title,
            'spaceKey': self.space_key,
            'expand': 'ancestors'
        }
        
        response = self._make_request('GET', endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            return results[0] if results else None
        else:
            return None

    def setup_page_hierarchy(self, page_hierarchy: Dict[str, str]) -> tuple[str, str]:
        # setup and validate page hierarchy
        # returns tuple of (grandparent_id, parent_id)
        grandparent_title = page_hierarchy['grandparent_title']
        parent_title = page_hierarchy.get('parent_title')  # Optional - may be None or missing
        
        # Get grandparent page
        grandparent_page = self.find_page_by_title(grandparent_title)
        if not grandparent_page:
            raise ConfluenceAPIError(f"Grandparent page '{grandparent_title}' not found")
        
        grandparent_id = grandparent_page['id']
        
        # If parent_title is not provided, create pages directly under grandparent
        if not parent_title:
            print(f"No parent_title specified - pages will be created directly under '{grandparent_title}'")
            return grandparent_id, grandparent_id
        
        # Get parent page under grandparent
        parent_page = self.find_page_under_parent(parent_title, grandparent_id)
        if not parent_page:
            raise ConfluenceAPIError(f"Parent page '{parent_title}' not found under '{grandparent_title}'")
        
        parent_id = parent_page['id']
        
        return grandparent_id, parent_id


    def generate_html_report(self, squad_name: str,
                             squad_epics: Dict, 
                             squad_metrics: Dict,
                             support_cases_metrics: Dict, 
                             start_date: datetime,
                             end_date: datetime,
                             with_trends : bool = False, #=trends_enabled,
                             subpage_urls: Dict = None,) -> str:
        """Generate complete HTML report with squad-based organization"""

        self.html_generator = HTMLGenerator(
            self.config.table_config,
            "https://jira.verifone.com",
            metrics_thresholds=self.config.metrics_thresholds,
            metrics_start_date=start_date,
            metrics_end_date=end_date,
            trends_enabled=with_trends
        )        

        logger.info("\nGenerating HTML report...")

        # Transform squad epics to project groups for HTML generator
        # Structure: squad_name → project_key → List[html_rows]
        squad_project_groups = {}
        epic_row_index = 0  # continuous counter so zebra striping stays consistent across squads/projects

        for squad_name, project_epics in squad_epics.items():
            squad_project_groups[squad_name] = {}

            for project_key, epics in project_epics.items():
                rows = []
                for epic in epics:
                    progress_bar = self.progress_bar_generator.create_progress_bar(
                        epic.done_count,
                        epic.total_count
                    )

                    story_points_progress_bar = self.progress_bar_generator.create_progress_bar(
                        epic.story_points_done,
                        epic.story_points_total
                    )

                    table_row = self.html_generator.create_table_row(
                        epic, progress_bar, indent_px=24,
                        story_points_progress_bar=story_points_progress_bar,
                        is_alt_row=(epic_row_index % 2 == 1))
                    epic_row_index += 1
                    rows.append(table_row)

                squad_project_groups[squad_name][project_key] = rows

            # Build hierarchical rows: Squad header -> Epics
            hierarchical_rows = []
            for squad_name, projects in squad_project_groups.items():
                # Only include squads that have epics
                projects_with_epics = {k: v for k, v in projects.items() if v}
                if not projects_with_epics:
                    continue

                squad_subpage_url = subpage_urls.get(squad_name) if subpage_urls else None
                hierarchical_rows.append(
                    self.html_generator.create_squad_header_row(squad_name, squad_subpage_url))

                for project_key, rows in projects_with_epics.items():
                    hierarchical_rows.extend(rows)

        # Flatten squad metrics to match expected structure: Dict[combined_key, MetricsData]
        # The metrics table expects metrics_data[project_key] to be a MetricsData object
        flattened_metrics = {}
        for squad_name, squad_data in squad_metrics.items():
            for project_key, metrics_data in squad_data.items():
                # Skip the special aggregate key for now (will handle separately)
                if project_key == "__squad_aggregate__":
                    # Use squad name as key for aggregate
                    flattened_metrics[squad_name] = metrics_data
                else:
                    # Create combined key for per-project metrics
                    combined_key = f"{squad_name} - {project_key}"
                    flattened_metrics[combined_key] = metrics_data                    

        html_content = self.html_generator.generate_html_report(
            hierarchical_rows,
            flattened_metrics,
            subpage_urls,
            {},  # display_name_mappings - will be handled differently for squads
            # Use flattened keys as "project" keys
            list(flattened_metrics.keys()),
            support_cases_metrics
        ) 


        return html_content                          