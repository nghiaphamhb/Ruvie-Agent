from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ruvie.dependencies import get_authenticated_user_id, get_session
from ruvie.services.projects import ProjectListingService


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(user_id: str = Depends(get_authenticated_user_id), session: Session = Depends(get_session)) -> dict[str, list[dict[str, str]]]:
    projects = ProjectListingService(session).list_for_user(user_id)
    return {"items": [{"id": project.id, "code": project.code, "name": project.name} for project in projects]}
