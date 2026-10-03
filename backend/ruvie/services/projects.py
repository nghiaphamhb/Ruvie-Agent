from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ruvie.models import Membership, Project


@dataclass(frozen=True)
class ProjectSummary:
    id: str
    code: str
    name: str


class ProjectListingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: str) -> list[ProjectSummary]:
        projects = self.session.scalars(
            select(Project)
            .join(Membership, Membership.project_id == Project.id)
            .where(Membership.user_id == user_id)
            .distinct()
            .order_by(Project.name, Project.id)
        )
        return [ProjectSummary(project.id, project.code, project.name) for project in projects]
