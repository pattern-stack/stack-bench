"""Stack CLI commands -- thin interface over REST API.

Usage:
    python -m organisms.cli.stack_commands push --stack-id <id> --workspace-id <id>
    python -m organisms.cli.stack_commands submit --stack-id <id>
    python -m organisms.cli.stack_commands ready --stack-id <id>
    python -m organisms.cli.stack_commands status --stack-id <id>
"""

from __future__ import annotations

import json

import httpx
import typer

app = typer.Typer(name="stack", help="Stack workflow commands")

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"


def _get_client(token: str | None = None, base_url: str = DEFAULT_BASE_URL) -> httpx.Client:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


@app.command()
def status(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Show stack status from the backend."""
    client = _get_client(token or None, base_url)
    response = client.get(f"/stacks/{stack_id}/detail")
    response.raise_for_status()
    data = response.json()

    stack = data["stack"]
    typer.echo(f"Stack: {stack['name']} ({stack['state']})")
    typer.echo(f"Trunk: {stack['trunk']}")
    typer.echo()

    for i, bd in enumerate(data["branches"]):
        branch = bd["branch"]
        pr = bd.get("pull_request")
        restack = bd.get("needs_restack", False)

        status_str = branch["state"]
        if pr:
            status_str = f"{pr['state']} (PR #{pr.get('external_id', '?')})"
        if restack:
            status_str += " [needs restack]"

        typer.echo(f"  {i + 1}. {branch['name']} -- {status_str}")


@app.command()
def push(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    workspace_id: str = typer.Argument(..., help="Workspace UUID"),
    branches_json: str = typer.Option(
        ...,
        "--branches",
        "-b",
        help='JSON array: [{"name": "...", "position": 1, "head_sha": "..."}]',
    ),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Push local branch state to the private workspace."""
    client = _get_client(token or None, base_url)
    branches = json.loads(branches_json)
    response = client.post(
        f"/stacks/{stack_id}/push",
        json={"workspace_id": workspace_id, "branches": branches},
    )
    response.raise_for_status()
    data = response.json()

    typer.echo(f"Pushed {data.get('created_count', 0)} new, {data.get('synced_count', 0)} updated branches")


@app.command()
def submit(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Create GitHub draft PRs for pushed branches."""
    client = _get_client(token or None, base_url)
    response = client.post(f"/stacks/{stack_id}/submit")
    response.raise_for_status()
    data = response.json()

    for result in data.get("results", []):
        action = result["action"]
        branch = result["branch"]
        if action == "created":
            typer.echo(f"  Created PR #{result['pr_number']} for {branch}")
            typer.echo(f"    {result['pr_url']}")
        elif action == "skipped":
            reason = result.get("reason", "already has PR")
            typer.echo(f"  Skipped {branch} ({reason})")


@app.command()
def ready(
    stack_id: str = typer.Argument(..., help="Stack UUID"),
    branch_ids: list[str] = typer.Option(  # noqa: B006, B008
        [], "--branch", "-b", help="Specific branch UUIDs (default: all)"
    ),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--url"),
    token: str = typer.Option("", "--token", envvar="SB_TOKEN"),
) -> None:
    """Mark draft PRs as ready for review."""
    client = _get_client(token or None, base_url)
    payload: dict[str, object] = {"branch_ids": branch_ids} if branch_ids else {}
    response = client.post(
        f"/stacks/{stack_id}/ready",
        json=payload if payload else None,
    )
    response.raise_for_status()
    data = response.json()

    for result in data.get("results", []):
        action = result["action"]
        branch = result["branch"]
        if action == "marked_ready":
            typer.echo(f"  Marked PR #{result['pr_number']} ready for {branch}")
        elif action == "skipped":
            typer.echo(f"  Skipped {branch} ({result.get('reason', '')})")


if __name__ == "__main__":
    app()
