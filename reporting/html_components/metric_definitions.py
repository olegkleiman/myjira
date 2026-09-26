"""
Metric definitions - all the metric info in one place
"""

from typing import Dict


class MetricDefinitions:
    """All the metric definitions in one spot"""

    @staticmethod
    def get_metric_info(metric_key: str) -> Dict[str, str]:
        # gets all the info about a metric
        # returns dict with name, definition, calculation, etc
        definitions = {
            "hotfix_frequency": {
                "name": "Hotfix Frequency",
                "definition": "Number of critical patches and emergency releases deployed in the last 180 days",
                "business_value": "Lower frequency indicates better code quality and testing processes. High frequency suggests systemic quality issues.",
                "calculation": "Count of Release issues labelled 'hotfix' with a 'Prod EMEA Date' within the reporting timeframe",
                "good_range": "0-2 per month (excellent), 3-5 per month (acceptable), &gt;5 per month (needs attention)",
                "category": "Quality",
                "color": "#e74c3c"
            },
            "customer_found_defects": {
                "name": "Customer Found Defects (CFDs)",
                "definition": "Number of defects reported by customers, support, or external users in the last 180 days",
                "business_value": "Lower numbers indicate better internal testing and quality processes before release.",
                "calculation": "Count of Defects where 'Found by:' = 'VFI - Support'",
                "good_range": "0-5 per month (excellent), 6-15 per month (acceptable), &gt;15 per month (needs attention)",
                "category": "Quality",
                "color": "#e74c3c"
            },
            "customer_defect_reopen_rate": {
                "name": "Customer Defect Reopen Rate (CDRR)",
                "definition": "Percentage of resolved customer-reported defects that were subsequently reopened (status changed back from Done)",
                "business_value": "Lower rate indicates more thorough issue resolution and better fix quality.",
                "calculation": "(Defects with status changed from Done / Defects with status changed to Done) × 100",
                "good_range": "0-5% (excellent), 6-15% (acceptable), &gt;15% (needs attention)",
                "category": "Quality",
                "color": "#e74c3c"
            },
            "customer_defect_fix_rate": {
                "name": "Customer Defect Fix Rate (CDFR)",
                "definition": "Percentage of customer-reported defects that had their status changed to Done within the reporting period",
                "business_value": "Higher rate indicates responsive customer support and efficient defect resolution.",
                "calculation": "(Defects with status changed to Done / Total customer defects created) × 100",
                "good_range": "&gt;80% (excellent), 60-80% (acceptable), &lt;60% (needs attention)",
                "category": "Quality",
                "color": "#e74c3c"
            },
            "defects_resolution_rate": {
                "name": "Defects Resolution Rate (DRR)",
                "definition": "Percentage of defects that transitioned to Done within the reporting period, compared to the total number of defects created in the same period.",
                "business_value": "Higher rate indicates effective defect management and team responsiveness to quality issues.",
                "calculation": "(Defects with status changed to Done after start_date / Total defects created after start_date) × 100",
                "good_range": "&gt;75% (excellent), 50-75% (acceptable), &lt;50% (needs attention)",
                "category": "Performance",
                "color": "#3498db"
            },
            "release_frequency": {
                "name": "Release Frequency",
                "definition": "Number of software releases with a release date within the reporting period.",
                "business_value": "Regular releases indicate healthy delivery cadence and continuous value delivery to customers.",
                "calculation": "Count of Release issues where Prod EMEA Date >= start_date",
                "good_range": "4-8 per month (excellent), 2-3 per month (acceptable), &lt;2 per month (needs attention)",
                "category": "Delivery",
                "color": "#2ecc71"
            },
            "ontime_delivery_rate": {
                "name": "On-time Delivery Rate (ODR)",
                "definition": "Percentage of epics delivered in the trailing 30 days that were resolved on or before their locked Commit Date (customfield_14768). Epics without a Commit Date are excluded from this calculation. This is a rolling window, recalculated relative to the time the report is run - not a fixed calendar month.",
                "business_value": "Higher rate indicates reliable delivery commitments and good project planning.",
                "calculation": "(Epics resolved on or before Commit Date) / (Epics delivered in last 30 days with a Commit Date) × 100",
                "good_range": "&gt;90% (excellent), 75-90% (acceptable), &lt;75% (needs attention)",
                "category": "Delivery",
                "color": "#2ecc71"
            },
            "story_points_delivered": {
                "name": "Pulse Story Points Delivered",
                "definition": "Sum of the 'Story Points - Pulse - Estimated' field across all non-Epic issues resolved by the squad in the report's date window, shown against the immediately preceding window of the same length as a trend: current value, direction arrow, percent change, and the previous value. Always scoped to the central ENT project.",
                "business_value": "Tracks the raw volume of estimated work a team actually finishes, independent of ticket count - the built-in trend makes it easy to see whether output is growing or shrinking period over period.",
                "calculation": "Sum of Story Points - Pulse - Estimated (customfield_18045) for issues where project = ENT AND issuetype != Epic AND squad matches AND resolved is in the report's date window, compared against the same sum for the immediately preceding window of the same length",
                "good_range": "Trend-based - compare against the squad's own prior period rather than a fixed target",
                "category": "Output",
                "color": "#9b59b6"
            },
            "backlog_pulse_story_points": {
                "name": "Backlog Pulse Story Points",
                "definition": "A point-in-time snapshot (not a rolling window) of the squad's unstarted backlog: sum of the 'Story Points - Pulse - Estimated' field across the child issues (linked via Epic Link) of the squad's Epics in Submitted status, where the child is still in the \"To Do\" status category and has a non-zero points value. Always scoped to the central ENT project.",
                "business_value": "Shows how much estimated work is queued up but not yet started, independent of throughput - a growing backlog alongside flat delivery signals a widening gap between demand and capacity.",
                "calculation": "1) Find Epics where project = ENT AND squad matches AND status = Submitted. 2) Sum Story Points - Pulse - Estimated (customfield_18045) across issues where \"Epic Link\" in (epics from step 1) AND statusCategory = \"To Do\" AND customfield_18045 is not empty, excluding zero values",
                "good_range": "Trend-based - compare against the squad's own prior snapshots rather than a fixed target",
                "category": "Backlog",
                "color": "#f39c12"
            }
        }

        return definitions.get(metric_key, {
            "name": "Unknown Metric",
            "definition": "Metric definition not available",
            "business_value": "Business value not defined",
            "calculation": "Calculation method not specified",
            "good_range": "Performance ranges not established",
            "category": "Other",
            "color": "#95a5a6"
        })
