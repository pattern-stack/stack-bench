# mypy: disable-error-code="attr-defined"
"""Mock implementation of DocumentProtocol."""

from __future__ import annotations

from datetime import UTC, datetime

from agentic_patterns.core.atoms.exceptions import NotFoundError
from agentic_patterns.core.atoms.protocols import (
    CreateDocumentInput,
    Document,
    DocumentFilter,
    UpdateDocumentInput,
)


class MockDocumentMixin:
    """In-memory DocumentProtocol implementation."""

    async def create_document(self, input: CreateDocumentInput) -> Document:
        now = datetime.now(UTC)
        doc_id = self._next_id("doc")
        slug = input.title.lower().replace(" ", "-")
        data = {
            "id": doc_id,
            "title": input.title,
            "content": input.content,
            "slug": slug,
            "icon": input.icon,
            "doc_type": input.doc_type,
            "project_id": input.project_id,
            "created_by": self._current_user_id,
            "created_at": now,
            "updated_at": now,
        }
        self._documents[doc_id] = data
        return Document(**data)

    async def get_document(self, id: str) -> Document:
        if id not in self._documents:
            raise NotFoundError("Document", id)
        return Document(**self._documents[id])

    async def list_documents(self, filter: DocumentFilter | None = None) -> list[Document]:
        results = list(self._documents.values())
        if filter is not None:
            if filter.doc_type is not None:
                dt_val = filter.doc_type.value if hasattr(filter.doc_type, "value") else filter.doc_type
                results = [
                    d
                    for d in results
                    if (d["doc_type"].value if hasattr(d["doc_type"], "value") else d["doc_type"]) == dt_val
                ]
            if filter.project_id is not None:
                results = [d for d in results if d["project_id"] == filter.project_id]
            if filter.created_by is not None:
                results = [d for d in results if d["created_by"] == filter.created_by]
        return [Document(**d) for d in results]

    async def update_document(self, input: UpdateDocumentInput) -> Document:
        if input.id not in self._documents:
            raise NotFoundError("Document", input.id)
        data = self._documents[input.id]
        for field in ("title", "content", "doc_type", "icon"):
            value = getattr(input, field)
            if value is not None:
                data[field] = value
        if input.title is not None:
            data["slug"] = input.title.lower().replace(" ", "-")
        data["updated_at"] = datetime.now(UTC)
        return Document(**data)

    async def delete_document(self, id: str) -> None:
        if id not in self._documents:
            raise NotFoundError("Document", id)
        del self._documents[id]

    async def search_documents(self, query: str) -> list[Document]:
        query_lower = query.lower()
        results = []
        for d in self._documents.values():
            title = d.get("title", "").lower()
            content = d.get("content", "").lower()
            if query_lower in title or query_lower in content:
                results.append(Document(**d))
        return results
