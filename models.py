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