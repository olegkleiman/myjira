"""
Squad-based metrics data fetcher - coordinates all metric fetching by squad
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from atlassian import Jira
from models import Squad
from .metrics_data import MetricsData
from .quality_metrics import QualityMetricsFetcher
from .performance_metrics import PerformanceMetricsFetcher
from .delivery_metrics import DeliveryMetricsFetcher
from .output_metrics import OutputMetricsFetcher

import logging

logger = logging.getLogger(__name__)


class SquadMetricsDataFetcher:
    """Fetches all squad metrics using the different metric components"""

    def __init__(self, 
                 jira_client: Jira, 
                 squad: Squad, 
                 start_date: str, 
                 end_date: str,
                 max_workers: int = 6, 
                 trends_enabled: bool = True):
        # setup the fetcher with jira client and squads
        self.jira_client = jira_client
        self.squad = squad
        self.max_workers = max_workers
        self.trends_enabled = trends_enabled

        # setup the different metric fetchers - every one of them is pinned
        # to the same resolved (start_date, end_date) range
        self.quality_fetcher = QualityMetricsFetcher(
            jira_client, 
            start_date=start_date, 
            end_date=end_date)
        self.performance_fetcher = PerformanceMetricsFetcher(
            jira_client, 
            start_date=start_date, 
            end_date=end_date)
        self.delivery_fetcher = DeliveryMetricsFetcher(
            jira_client, 
            start_date=start_date, 
            end_date=end_date)
        self.output_fetcher = OutputMetricsFetcher(
            jira_client, 
            start_date=start_date, 
            end_date=end_date)

    def fetch_all_metrics(self) ->Dict[str, MetricsData]:
        """
        Fetch all metrics for the squad.
        ...
        """

        metrics_data = MetricsData(f"{self.squad} (Aggregate)")

        logger.info(f"\n\n{'=' * 80}")
        logger.info(f"FETCHING METRICS FOR {self.squad} SQUAD")
        # logger.info(f"Timeframe: {self.quality_fetcher.start_date} to {self.quality_fetcher.end_date}")
        logger.info(f"{'=' * 80}\n")

        tasks = self._build_squad_metric_tasks(self.squad, metrics_data)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fn): attr for _, attr, fn in tasks}   # ← unpack all 3, ignore squad_name
            for future, attr in futures.items():
                setattr(metrics_data, attr, future.result())

        all_metrics = {"__squad_aggregate__": metrics_data}

        logger.info(f"\n  Squad Summary: {self.squad}")
        logger.info(f"     - Customer Found Defects: {metrics_data.customer_found_defects}")
        logger.info(f"     - Hotfix Frequency: {metrics_data.hotfix_frequency}")
        logger.info(f"     - Customer Defect Reopen Rate: {metrics_data.customer_defect_reopen_rate}%")
        logger.info(f"     - Customer Defect Fix Rate: {metrics_data.customer_defect_fix_rate}%")
        logger.info(f"     - Defects Resolution Rate: {metrics_data.defects_resolution_rate}%")
        logger.info(f"     - Release Frequency: {metrics_data.release_frequency}")
        logger.info(f"     - On-time Delivery Rate: {metrics_data.ontime_delivery_rate}% (excluded for no Commit Date: {metrics_data.ontime_delivery_excluded_count})")
        logger.info(f"     - Pulse Story Points Delivered: {metrics_data.story_points_delivered} (previous 30d: {metrics_data.story_points_delivered_previous})")
        logger.info(f"     - Backlog Pulse Story Points: {metrics_data.backlog_pulse_story_points}")

        logger.info(f"\n\n{'=' * 80}")
        logger.info(f"SQUAD METRICS FETCHING COMPLETED!")
        logger.info(f"{'=' * 80}\n")

        return all_metrics

    def _build_squad_metric_tasks(self, squad_name: str, metrics_data: MetricsData) -> List[tuple]:
        """Build the (squad_name, attribute_name, fetch_callable) tuples for
        one squad's aggregate metrics, ready to hand to a shared thread pool.

        When trends are disabled, the "_previous" comparison-window tasks are
        dropped entirely so their JQL queries never fire."""
        tasks = [
            (squad_name, 'customer_found_defects',
             lambda: self.quality_fetcher.fetch_customer_found_defects_by_squad(squad_name, metrics_data)),
            (squad_name, 'customer_found_defects_previous',
             lambda: self.quality_fetcher.fetch_customer_found_defects_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'hotfix_frequency',
             lambda: self.quality_fetcher.fetch_hotfix_frequency_by_squad(squad_name, metrics_data)),
            (squad_name, 'hotfix_frequency_previous',
             lambda: self.quality_fetcher.fetch_hotfix_frequency_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'customer_defect_reopen_rate',
             lambda: self.quality_fetcher.fetch_reopen_rate_by_squad(squad_name, metrics_data)),
            (squad_name, 'customer_defect_reopen_rate_previous',
             lambda: self.quality_fetcher.fetch_reopen_rate_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'customer_defect_fix_rate',
             lambda: self.quality_fetcher.fetch_customer_defect_fix_rate_by_squad(squad_name, metrics_data)),
            (squad_name, 'customer_defect_fix_rate_previous',
             lambda: self.quality_fetcher.fetch_customer_defect_fix_rate_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'defects_resolution_rate',
             lambda: self.performance_fetcher.fetch_defects_resolution_rate_by_squad(squad_name, metrics_data)),
            (squad_name, 'defects_resolution_rate_previous',
             lambda: self.performance_fetcher.fetch_defects_resolution_rate_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'release_frequency',
             lambda: self.delivery_fetcher.fetch_release_frequency_by_squad(squad_name, metrics_data)),
            (squad_name, 'release_frequency_previous',
             lambda: self.delivery_fetcher.fetch_release_frequency_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'ontime_delivery_rate',
             lambda: self.delivery_fetcher.fetch_ontime_delivery_rate_by_squad(squad_name, metrics_data)),
            (squad_name, 'ontime_delivery_rate_previous',
             lambda: self.delivery_fetcher.fetch_ontime_delivery_rate_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'story_points_delivered',
             lambda: self.output_fetcher.fetch_story_points_delivered_by_squad(squad_name, metrics_data)),
            (squad_name, 'story_points_delivered_previous',
             lambda: self.output_fetcher.fetch_story_points_delivered_previous_by_squad(squad_name, metrics_data)),
            (squad_name, 'backlog_pulse_story_points',
             lambda: self.output_fetcher.fetch_backlog_pulse_story_points_by_squad(squad_name, metrics_data)),
        ]

        if not self.trends_enabled:
            tasks = [task for task in tasks if not task[1].endswith('_previous')]

        return tasks
