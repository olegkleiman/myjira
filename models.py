from dataclasses import dataclass
from typing import List, Optional


@dataclass
class JiraVersion:
    """Jira version/release info"""
    name: str


@dataclass
class JiraStatus:
    """Jira issue status"""
    name: str
    status_category_key: str


@dataclass
class JiraProject:
    """Jira project info"""
    key: str
    name: str


@dataclass
class EpicProgressInfo:
    """Represents progress information for an epic (child issues completion)."""
    done_count: int
    total_count: int
    story_points_done: float = 0.0
    story_points_total: float = 0.0


@dataclass
class JiraIssue:
    """Represents a Jira issue with essential fields."""
    key: str
    summary: str
    status: JiraStatus
    project: JiraProject
    epic_name: Optional[str] = None
    rag_status: Optional[str] = None
    commit_date: Optional[str] = None
    due_date: Optional[str] = None
    comments: Optional[str] = None
    fixed_versions: List[JiraVersion] = None

    def __post_init__(self):
        if self.fixed_versions is None:
            self.fixed_versions = []

    @property
    def project_name(self) -> str:
        """Get the project name, fallback to project key if name not available."""
        return self.project.name if self.project.name else self.key.split('-')[0]

    @property
    def fixed_version_names(self) -> List[str]:
        """Get list of fixed version names."""
        return [version.name for version in self.fixed_versions]


@dataclass
class SupportCasesMetrics:
    """Metrics for support cases by squad."""
    squad_name: str
    project_name: Optional[str]  # None for squad-level aggregates
    environment: str  # "production", "non_production", or "all"
    ingress: int  # Cases created (incoming workload)
    egress: int  # Cases resolved (outgoing workload)
    cases: List['SupportCase'] = None

    @property
    def net_change(self) -> int:
        """Net change in support cases (ingress - egress). Positive = backlog growing."""
        return self.ingress - self.egress

    def __post_init__(self):
        if self.cases is None:
            self.cases = []


@dataclass
class Squad:
    """Represents a squad/team."""
    name: str

@dataclass
class SupportCase:
    """Represents a Support Case issue."""
    key: str
    summary: str
    priority: str
    created: str
    resolved: Optional[str]
    status: JiraStatus
    project: JiraProject
    squad: Optional[str] = None


@dataclass
class EpicData:
    """Epic data with status info"""
    
    def __init__(self, issue_key: str, epic_name: str, rag_status: str,
                 commit_date: str, fixed_versions: List[str], comments: str,
                 done_count: int, total_count: int, project_name: str,
                 due_date: str = '', story_points_done: float = 0.0,
                 story_points_total: float = 0.0, status_name: str = '',
                 status_category_key: str = ''):
        self.issue_key = issue_key
        self.epic_name = epic_name
        self.rag_status = rag_status
        self.commit_date = commit_date
        self.due_date = due_date
        self.fixed_versions = fixed_versions
        self.comments = comments
        self.done_count = done_count
        self.total_count = total_count
        self.project_name = project_name
        self.story_points_done = story_points_done
        self.story_points_total = story_points_total
        self.status_name = status_name
        self.status_category_key = status_category_key    
