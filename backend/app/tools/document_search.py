"""Semantic document search tool for RAG."""
import uuid
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool
from app.knowledge.retrieval import SemanticRetriever
from app.db.session import AsyncSessionLocal


class DocumentSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The semantic search query to look up in workspace documents."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Workspace ID to search documents within."
    )


class DocumentSearchTool(BaseTool):
    name = "document_search"
    description = (
        "Search uploaded documents, specifications, and knowledge bases within the workspace. "
        "Returns relevant excerpts with document names and page numbers for source citations."
    )
    args_schema = DocumentSearchInput
    timeout_seconds = 10.0

    async def execute(
        self,
        query: str,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Perform semantic search and return relevant document chunks."""
        if not workspace_id:
            return {
                "results": [],
                "message": "No workspace context provided for document search."
            }

        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            return {
                "results": [],
                "error": "Invalid workspace UUID."
            }

        if db is not None:
            chunks = await SemanticRetriever.search(
                db=db,
                workspace_id=ws_uuid,
                query=query,
                top_k=4
            )
        else:
            async with AsyncSessionLocal() as session:
                chunks = await SemanticRetriever.search(
                    db=session,
                    workspace_id=ws_uuid,
                    query=query,
                    top_k=4
                )

        if not chunks:
            return {
                "query": query,
                "results": [],
                "message": "No relevant documents or matches found in this workspace."
            }

        return {
            "query": query,
            "results": chunks,
            "citation_instructions": (
                "When answering the user, ground your explanation in these retrieved excerpts. "
                "Explicitly cite the source document filename and page number where available."
            )
        }
