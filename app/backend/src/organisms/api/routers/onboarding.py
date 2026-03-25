from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from molecules.workflows.onboarding import OnboardingError, OnboardingWorkflow
from organisms.api.dependencies import CurrentUser, DatabaseSession

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# --- Response schemas ---


class OnboardingStatusResponse(BaseModel):
    needs_onboarding: bool
    has_github: bool
    has_project: bool


class GitHubOrgResponse(BaseModel):
    login: str
    avatar_url: str
    description: str | None = None


class GitHubRepoResponse(BaseModel):
    full_name: str
    name: str
    private: bool
    default_branch: str
    description: str | None = None


class OnboardingCompleteRequest(BaseModel):
    repo_full_name: str  # "owner/repo"
    default_branch: str = "main"


class OnboardingCompleteResponse(BaseModel):
    project_id: str
    workspace_id: str
    project_name: str


# --- Endpoints ---


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: CurrentUser, db: DatabaseSession) -> OnboardingStatusResponse:
    workflow = OnboardingWorkflow(db)
    status = await workflow.get_status(user.id)
    return OnboardingStatusResponse(
        needs_onboarding=status.needs_onboarding,
        has_github=status.has_github,
        has_project=status.has_project,
    )


@router.get("/github/orgs", response_model=list[GitHubOrgResponse])
async def list_github_orgs(user: CurrentUser, db: DatabaseSession) -> list[GitHubOrgResponse]:
    workflow = OnboardingWorkflow(db)
    try:
        orgs = await workflow.list_github_orgs(user.id)
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message) from None
    return [GitHubOrgResponse(**vars(o)) for o in orgs]


@router.get("/github/repos", response_model=list[GitHubRepoResponse])
async def list_github_repos(
    user: CurrentUser,
    db: DatabaseSession,
    org: str | None = None,
) -> list[GitHubRepoResponse]:
    workflow = OnboardingWorkflow(db)
    try:
        repos = await workflow.list_github_repos(user.id, org=org)
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message) from None
    return [GitHubRepoResponse(**vars(r)) for r in repos]


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    data: OnboardingCompleteRequest,
    user: CurrentUser,
    db: DatabaseSession,
) -> OnboardingCompleteResponse:
    workflow = OnboardingWorkflow(db)
    try:
        result = await workflow.complete(
            user_id=user.id,
            repo_full_name=data.repo_full_name,
            default_branch=data.default_branch,
        )
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message) from None
    await db.commit()
    return OnboardingCompleteResponse(
        project_id=str(result.project_id),
        workspace_id=str(result.workspace_id),
        project_name=result.project_name,
    )
