"""
Configuration loader - loads and validates YAML config
"""

import yaml
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from models import Squad

class ConfigurationError(Exception):
    """Exception for config errors"""
    pass


class Config:
    """Config class for loading YAML configuration"""

    def __init__(self, config_file: str = 'config.yaml'):
        # load config from YAML file
        self.config_file = config_file
        self._config = self._load_config()
        self._merge_credentials()
        # self._validate_config()
        # resolve the report's date range once: an explicit report.start_date
        # /report.end_date pair is used as-is; otherwise it's derived from
        # timeframe_days as (today - timeframe_days, today). Every consumer
        # downstream (JQL builders, HTML generator) works with this concrete
        # range only - timeframe_days never leaves this class.
        # self._resolved_start_date, self._resolved_end_date = self._resolve_date_range(
        #     self.report.get('start_date'), self.report.get('end_date'), self.metrics_timeframe_days)

    @staticmethod
    def _resolve_date_range(start_date: Optional[str], end_date: Optional[str],
                             timeframe_days: int) -> Tuple[str, str]:
        if start_date and end_date:
            return start_date, end_date
        end = datetime.now()
        start = end - timedelta(days=timeframe_days)
        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    def _load_config(self) -> Dict[str, Any]:
        # load config from YAML file
        try:
            with open(self.config_file, 'r', encoding="utf-8") as f:
                config = yaml.safe_load(f)
            print(f"Loaded configuration from {self.config_file}")
            return config
        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file {self.config_file} not found!")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")

    def _merge_credentials(self) -> None:
        # merge credentials (base_url, email, api_token) from each section's
        # credentials_file into the corresponding config section
        for section in ('jira', 'confluence'):
            section_config = self._config.get(section)
            if not section_config:
                continue
            credentials_file = section_config.pop('credentials_file', None)
            if not credentials_file:
                continue
            try:
                with open(credentials_file, 'r') as f:
                    credentials = yaml.safe_load(f) or {}
            except FileNotFoundError:
                raise ConfigurationError(
                    f"Credentials file {credentials_file} not found! "
                    f"Copy {credentials_file}.example to {credentials_file} and fill in your values.")
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Error parsing YAML credentials file {credentials_file}: {e}")
            section_config.update(credentials.get(section, {}))

    def _validate_config(self) -> None:
        # validate required config sections exist
        required_sections = ['jira', 'confluence', 'report']

        for section in required_sections:
            if section not in self._config:
                raise ConfigurationError(
                    f"Missing required configuration section: {section}")

        # Validate Jira configuration
        jira_config = self._config['jira']
        required_jira_fields = ['base_url', 'email', 'api_token', 'squads', 'fields']
        for field in required_jira_fields:
            if field not in jira_config:
                raise ConfigurationError(
                    f"Missing required Jira configuration field: {field}")

        # Validate squads configuration
        if not isinstance(jira_config['squads'], list) or len(jira_config['squads']) == 0:
            raise ConfigurationError("Jira squads must be a non-empty list")

        # Validate Confluence configuration
        confluence_config = self._config['confluence']
        required_confluence_fields = [
            'base_url', 'email', 'api_token', 'space_key', 'page_hierarchy']
        for field in required_confluence_fields:
            if field not in confluence_config:
                raise ConfigurationError(
                    f"Missing required Confluence configuration field: {field}")

        self._validate_date_range(
            self.report.get('start_date'), self.report.get('end_date'))

    @staticmethod
    def _validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> None:
        # optional explicit date range for report.start_date/end_date - either both set or neither
        if start_date is None and end_date is None:
            return
        if start_date is None or end_date is None:
            raise ConfigurationError(
                "report.start_date and report.end_date must both be set together, or both omitted")

        for label, value in (('start_date', start_date), ('end_date', end_date)):
            try:
                datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise ConfigurationError(
                    f"report.{label} must be in YYYY-MM-DD format, got: {value!r}")

        if start_date > end_date:
            raise ConfigurationError(
                f"report.start_date ({start_date}) must not be after report.end_date ({end_date})")

    @property
    def jira(self) -> Dict[str, Any]:
        # get jira config
        return self._config['jira']

    @property
    def confluence(self) -> Dict[str, Any]:
        # get confluence config
        return self._config['confluence']

    @property
    def report(self) -> Dict[str, Any]:
        # get report config
        return self._config['report']

    # Jira-specific getters
    @property
    def jira_base_url(self) -> str:
        # get jira base URL
        return self.jira['base_url']

    @property
    def jira_email(self) -> str:
        # get jira account email
        return self.jira['email']

    @property
    def jira_api_token(self) -> str:
        # get jira cloud API token
        return self.jira['api_token']

    @property
    def jira_squads(self) -> List[Squad]:
        # get list of Squad objects from config
        squads_config = self.jira['squads']
        squads = []
        for squad_data in squads_config:
            squad = Squad(name=squad_data['name'])
            squads.append(squad)
        return squads

    @property
    def jira_fields(self) -> Dict[str, str]:
        # get jira field mappings
        return self.jira['fields']

    @property
    def jira_excluded_statuses(self) -> List[str]:
        # get excluded epic statuses
        return self.jira['epic_statuses_excluded']

    @property
    def jira_max_results(self) -> int:
        # get max results per API call
        return self.jira.get('max_results', 1000)

    @property
    def jira_max_workers(self) -> int:
        # get thread pool size for parallel JQL queries
        return self.jira.get('max_workers', 6)

    # Confluence-specific getters
    @property
    def confluence_base_url(self) -> str:
        # get confluence base URL
        return self.confluence['base_url']

    @property
    def confluence_email(self) -> str:
        # get confluence account email
        return self.confluence['email']

    @property
    def confluence_api_token(self) -> str:
        # get confluence cloud api token
        return self.confluence['api_token']

    @property
    def confluence_space_key(self) -> str:
        # get confluence space key
        return self.confluence['space_key']

    @property
    def confluence_page_hierarchy(self) -> Dict[str, str]:
        # get confluence page hierarchy config
        return self.confluence['page_hierarchy']

    # Report-specific getters
    @property
    def table_config(self) -> Dict[str, str]:
        # get table config
        return self.report['table']

    @property
    def progress_bar_config(self) -> Dict[str, Any]:
        # get progress bar config
        return self.report['progress_bar']

    @property
    def metrics_timeframe_days(self) -> int:
        # timeframe (days) used to derive the date range when report.start_date
        # /report.end_date aren't explicitly set
        return self.report.get('timeframe_days', 90)

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

    @property
    def metrics_thresholds(self) -> Dict[str, int]:
        # thresholds for coloring metrics percentages
        return self.report.get('thresholds', {}).get('metrics', {'green': 90, 'amber': 75})

    @property
    def html_output_file(self) -> str:
        # get HTML output file path
        return self.report['html_output_file']

    # Support Cases configuration getters
    @property
    def support_cases(self) -> Dict[str, Any]:
        # get support cases config (optional section)
        return self._config.get('support_cases', {})

    @property
    def support_cases_enabled(self) -> bool:
        # check if support cases tracking is enabled
        return self.support_cases.get('enabled', False)

    @property
    def support_cases_issue_type(self) -> str:
        # get support case issue type
        return self.support_cases.get('issue_type', 'Support Case')

    @property
    def support_cases_squad_overrides(self) -> Dict[str, str]:
        # mapping of squad name -> alternate squad name used only for support cases (DEPRECATED)
        return self.support_cases.get('squad_name_overrides', {})

    @property
    def support_cases_jql_overrides(self) -> Dict[str, Dict[str, str]]:
        # mapping of squad name -> dict of JQL queries for created/resolved overrides
        # Format: {
        #   "squad_name": {
        #     "created_query": "custom JQL query for created cases",
        #     "resolved_query": "custom JQL query for resolved cases"
        #   }
        # }
        return self.support_cases.get('jql_overrides', {})

    # Trends configuration getters
    @property
    def trends(self) -> Dict[str, Any]:
        # get trends config (optional section)
        return self._config.get('trends', {})

    @property
    def trends_enabled(self) -> bool:
        # check if trend comparisons against the prior period are enabled (default: on)
        return self.trends.get('enabled', True)


def load_config(config_file: str = 'config.yaml') -> Config:
    # load config from YAML file
    # returns Config object
    try:
        return Config(config_file)
    except ConfigurationError:
        sys.exit(1)
