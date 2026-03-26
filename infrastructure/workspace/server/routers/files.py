"""File CRUD endpoints for workspace server."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

WORKSPACE_ROOT = Path("/workspace")


class FileEntry(BaseModel):
    name: str
    path: str
    type: str  # "file" | "dir"
    size: int | None = None


class FileContent(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"  # "utf-8" or "base64"
    size: int


class FileWrite(BaseModel):
    content: str
    encoding: str = "utf-8"


def _validate_path(path: str) -> Path:
    """Ensure path is within /workspace/."""
    resolved = Path(path).resolve()
    if not str(resolved).startswith(str(WORKSPACE_ROOT)):
        raise HTTPException(status_code=403, detail="Path must be within /workspace/")
    return resolved


@router.get("")
async def list_files(path: str = "/workspace/main/") -> list[FileEntry]:
    """List directory contents."""
    target = _validate_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    entries = []
    for item in sorted(target.iterdir()):
        entry_type = "dir" if item.is_dir() else "file"
        size = item.stat().st_size if item.is_file() else None
        entries.append(FileEntry(
            name=item.name,
            path=str(item),
            type=entry_type,
            size=size,
        ))
    return entries


@router.get("/{path:path}")
async def read_file(path: str) -> FileContent:
    """Read file contents. Returns text or base64 encoded."""
    target = _validate_path(f"/{path}")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    size = target.stat().st_size
    try:
        content = target.read_text(encoding="utf-8")
        return FileContent(path=str(target), content=content, encoding="utf-8", size=size)
    except UnicodeDecodeError:
        content_b64 = base64.b64encode(target.read_bytes()).decode("ascii")
        return FileContent(path=str(target), content=content_b64, encoding="base64", size=size)


@router.put("/{path:path}")
async def write_file(path: str, body: FileWrite) -> FileContent:
    """Write file contents."""
    target = _validate_path(f"/{path}")
    target.parent.mkdir(parents=True, exist_ok=True)

    if body.encoding == "base64":
        data = base64.b64decode(body.content)
        target.write_bytes(data)
        size = len(data)
    else:
        target.write_text(body.content, encoding="utf-8")
        size = len(body.content.encode("utf-8"))

    return FileContent(path=str(target), content=body.content, encoding=body.encoding, size=size)


@router.delete("/{path:path}")
async def delete_file(path: str) -> dict:
    """Delete a file."""
    target = _validate_path(f"/{path}")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    target.unlink()
    return {"deleted": str(target)}
