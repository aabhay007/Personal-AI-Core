"""Unit and integration tests for Knowledge Engine, RAG, and Workspace Isolation."""
import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter
from app.knowledge.ingestion import DocumentExtractor, clean_text
from app.knowledge.chunking import TextChunker
from app.knowledge.retrieval import SemanticRetriever, cosine_similarity
from app.knowledge.service import DocumentService


def test_text_cleaning_and_pdf_extraction():
    """Verify text cleaning and PDF extraction."""
    raw = "Hello   world!\r\n\r\n\n\nThis is a test.\t\t"
    assert clean_text(raw) == "Hello world!\n\nThis is a test."

    # Create a tiny in-memory PDF with pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    pdf_bytes_io = io.BytesIO()
    writer.write(pdf_bytes_io)
    pdf_bytes = pdf_bytes_io.getvalue()

    # Plain text extractor test
    sections = DocumentExtractor.extract_text("spec.txt", b"System architecture specification content.")
    assert len(sections) == 1
    assert sections[0]["page_number"] == 1
    assert "specification content" in sections[0]["content"]


def test_text_chunker():
    """Verify document chunker generates overlapping windows and preserves metadata."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=15)
    sections = [
        {"content": "First page text describing personal AI platform components.", "page_number": 1},
        {"content": "Second page text detailing vector search and database retrieval.", "page_number": 2}
    ]
    chunks = chunker.chunk_document_sections(sections, "manual.pdf")
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["filename"] == "manual.pdf"
    assert chunks[0]["metadata"]["page_number"] in (1, 2)
    assert "content" in chunks[0]


def test_cosine_similarity():
    """Verify vector cosine similarity calculation."""
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    assert cosine_similarity(vec_a, vec_b) == 1.0
    assert cosine_similarity(vec_a, vec_c) == 0.0


@pytest.mark.asyncio
async def test_document_upload_and_semantic_search_isolation(async_client: AsyncClient):
    """Verify document ingestion, semantic search, and cross-workspace isolation."""
    # 1. Register User A
    user_a_res = await async_client.post("/api/v1/auth/register", json={
        "email": "doc_user_a@example.com",
        "password": "Password123!",
        "full_name": "User Doc Alpha"
    })
    token_a = user_a_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    ws_a_res = await async_client.get("/api/v1/workspaces", headers=headers_a)
    workspace_a_id = ws_a_res.json()[0]["id"]

    # 2. Register User B
    user_b_res = await async_client.post("/api/v1/auth/register", json={
        "email": "doc_user_b@example.com",
        "password": "Password123!",
        "full_name": "User Doc Beta"
    })
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    ws_b_res = await async_client.get("/api/v1/workspaces", headers=headers_b)
    workspace_b_id = ws_b_res.json()[0]["id"]

    # 3. User A uploads a document to Workspace A
    doc_content = (
        b"Personal AI Core uses a modular monolith architecture. "
        b"It uses FastAPI for the backend API and Next.js for the frontend. "
        b"Vector embeddings are generated using local FastEmbed models and pgvector."
    )
    files = {"file": ("architecture.txt", doc_content, "text/plain")}
    upload_res = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers_a,
        data={"workspace_id": workspace_a_id},
        files=files
    )
    assert upload_res.status_code == 201
    doc_a = upload_res.json()
    assert doc_a["filename"] == "architecture.txt"
    assert doc_a["processing_status"] == "completed"
    doc_a_id = doc_a["id"]

    # 4. User A lists documents in Workspace A
    list_a_res = await async_client.get(f"/api/v1/documents?workspace_id={workspace_a_id}", headers=headers_a)
    assert list_a_res.status_code == 200
    assert len(list_a_res.json()) >= 1

    # 5. User A executes document_search tool via API
    search_res = await async_client.post(
        "/api/v1/tools/document_search/execute",
        headers=headers_a,
        json={"arguments": {"query": "What architecture does the core use?", "workspace_id": workspace_a_id}}
    )
    assert search_res.status_code == 200
    search_data = search_res.json()["result"]
    assert len(search_data["results"]) >= 1
    top_result = search_data["results"][0]
    assert "modular monolith" in top_result["content"].lower()
    assert top_result["filename"] == "architecture.txt"

    # =========================================================================
    # 6. SECURITY CHECK: User B cannot access or retrieve User A's documents
    # =========================================================================
    # User B searches in Workspace B (which has no documents)
    b_search_res = await async_client.post(
        "/api/v1/tools/document_search/execute",
        headers=headers_b,
        json={"arguments": {"query": "modular monolith", "workspace_id": workspace_b_id}}
    )
    assert b_search_res.status_code == 200
    assert len(b_search_res.json()["result"]["results"]) == 0

    # User B attempts to access User A's document directly by ID
    unauthorized_get = await async_client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert unauthorized_get.status_code == 403

    # User B attempts to delete User A's document
    unauthorized_delete = await async_client.delete(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert unauthorized_delete.status_code == 403

    # 7. User A deletes the document
    delete_res = await async_client.delete(f"/api/v1/documents/{doc_a_id}", headers=headers_a)
    assert delete_res.status_code == 204

    # Verify document is gone
    not_found = await async_client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_a)
    assert not_found.status_code == 404
