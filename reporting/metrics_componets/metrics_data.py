"""
MetricsData model - holds all the metrics values and ticket data
"""

from typing import List, Optional


class MetricsData:
    """Holds metrics values for one project"""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        
        # the actual metric values
        self.hotfix_frequency: Optional[int] = None
        self.customer_found_defects: Optional[int] = None
        self.customer_defect_reopen_rate: Optional[float] = None
        self.customer_defect_fix_rate: Optional[float] = None
        self.defects_resolution_rate: Optional[float] = None
        self.release_frequency: Optional[int] = None
        self.ontime_delivery_rate: Optional[float] = None
        # count of epics excluded from the ODR denominator/numerator because
        # they had no locked Commit Date (customfield_14768) - surfaced so a
        # large exclusion count doesn't silently undermine the metric
        self.ontime_delivery_excluded_count: Optional[int] = None
        self.story_points_delivered: Optional[float] = None

        # comparison-window values (immediately preceding the current
        # window, same length as it) used as the trend baseline for each
        # metric shown in the summary table
        self.hotfix_frequency_previous: Optional[int] = None
        self.customer_found_defects_previous: Optional[int] = None
        self.customer_defect_reopen_rate_previous: Optional[float] = None
        self.customer_defect_fix_rate_previous: Optional[float] = None
        self.defects_resolution_rate_previous: Optional[float] = None
        self.release_frequency_previous: Optional[int] = None
        self.ontime_delivery_rate_previous: Optional[float] = None
        self.story_points_delivered_previous: Optional[float] = None

        # point-in-time backlog snapshot, not a rolling window
        self.backlog_pulse_story_points: Optional[float] = None

        # ticket lists for each metric (for detailed analysis)
        self.hotfix_tickets: List = []
        self.customer_found_defect_tickets: List = []
        self.customer_defect_reopen_resolved_tickets: List = []
        self.customer_defect_reopen_reopened_tickets: List = []
        self.customer_defect_fix_total_tickets: List = []
        self.customer_defect_fix_resolved_tickets: List = []
        self.defects_resolution_created_tickets: List = []
        self.defects_resolution_resolved_tickets: List = []
        self.release_frequency_tickets: List = []
        self.ontime_delivery_tickets: List = []
        self.ontime_delivery_numerator_tickets: List = []
        self.story_points_delivered_tickets: List = []
        self.story_points_delivered_previous_tickets: List = []
        self.backlog_pulse_epics_tickets: List = []
        self.backlog_pulse_story_points_tickets: List = []

        # JQL queries used (so people can see how we calculated stuff)
        self.hotfix_jql: str = ""
        self.customer_found_defects_jql: str = ""
        self.customer_defect_reopen_resolved_jql: str = ""
        self.customer_defect_reopen_reopened_jql: str = ""
        self.customer_defect_fix_total_jql: str = ""
        self.customer_defect_fix_resolved_jql: str = ""
        self.defects_resolution_created_jql: str = ""
        self.defects_resolution_resolved_jql: str = ""
        self.release_frequency_jql: str = ""
        self.ontime_delivery_jql: str = ""
        self.ontime_delivery_numerator_jql: str = ""
        self.story_points_delivered_jql: str = ""
        self.story_points_delivered_previous_jql: str = ""
        self.backlog_pulse_epics_jql: str = ""
        self.backlog_pulse_story_points_jql: str = ""