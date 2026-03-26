from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import get_settings
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
    installed: bool = False
    installation_id: int | None = None
    account_type: str = "Organization"


class GitHubRepoResponse(BaseModel):
    full_name: str
    name: str
    private: bool
    default_branch: str
    description: str | None = None


class GitHubAppInstallResponse(BaseModel):
    install_url: str


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


@router.get("/github/install", response_model=GitHubAppInstallResponse)
async def get_github_app_install_url(user: CurrentUser) -> GitHubAppInstallResponse:
    """Return the URL to install the Stack Bench GitHub App on an org.

    Uses /installations/select_target which shows the org picker even if
    the app is already installed on the user's personal account.
    """
    settings = get_settings()
    install_url = f"https://github.com/apps/{settings.GITHUB_APP_SLUG}/installations/new"
    return GitHubAppInstallResponse(install_url=install_url)


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


class OnboardingCompleteSimpleResponse(BaseModel):
    completed: bool


@router.post("/complete", response_model=OnboardingCompleteSimpleResponse)
async def complete_onboarding(
    user: CurrentUser,
    db: DatabaseSession,
) -> OnboardingCompleteSimpleResponse:
    """Mark onboarding as complete. GitHub App is installed, user is ready.

    Project creation is a separate workflow — not part of onboarding.
    """
    workflow = OnboardingWorkflow(db)
    await workflow.mark_complete(user.id)
    await db.commit()
    return OnboardingCompleteSimpleResponse(completed=True)
