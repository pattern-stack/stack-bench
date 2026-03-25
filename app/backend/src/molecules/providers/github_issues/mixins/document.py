"""GitHub Issues implementation of DocumentProtocol (stub).

GitHub has no native document concept. All methods raise NotFoundError
or return empty results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agentic_patterns.core.atoms.exceptions import NotFoundError

if TYPE_CHECKING:
    from agentic_patterns.core.atoms.protocols import (
        CreateDocumentInput,
        Document,
        DocumentFilter,
        UpdateDocumentInput,
    )


class GitHubDocumentMixin:
    """Stub DocumentProtocol — GitHub has no document concept."""

    async def create_document(self, input: CreateDocumentInput) -> Document:
        raise NotFoundError(
            "Document",
            "unsupported",
        )

    async def get_document(self, id: str) -> Document:
        raise NotFoundError("Document", id)

    async def list_documents(self, filter: DocumentFilter | None = None) -> list[Document]:
        return []

    async def update_document(self, input: UpdateDocumentInput) -> Document:
        raise NotFoundError("Document", input.id)

    async def delete_document(self, id: str) -> None:
        raise NotFoundError("Document", id)

    async def search_documents(self, query: str) -> list[Document]:
        return []
