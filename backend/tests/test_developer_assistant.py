"""Tests for Phase 6 Developer Assistant, GitHub Integration, and Code Indexing."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.code_repository import CodeRepository, RepositoryFile
from app.knowledge.code_indexer import chunk_code_file, is_indexable_path, CodeIndexer, CodeSearchEngine
from app.tools.registry import tool_registry
from app.agents.developer_assistant import DeveloperAssistantAgent
from app.core.security import hash_password

SAMPLE_PYTHON_CODE = """# Personal AI Core - Fast health endpoint
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    \"\"\"Return 200 OK for uptime monitoring.\"\"\"
    return {"status": "healthy", "service": "personal_ai_core"}

def calculate_uptime():
    return 99.99
"""

SAMPLE_TYPESCRIPT_CODE = """// Navigation item component
export interface NavItem {
  title: string;
  href: string;
  disabled?: boolean;
}

export function renderNav(items: NavItem[]) {
  return items.map(item => item.title);
}
"""


def test_path_filter_and_code_chunker():
    """Verify file path filtering and line-numbered chunking."""
    assert is_indexable_path("backend/app/main.py") is True
    assert is_indexable_path("frontend/src/app/chat/page.tsx") is True
    assert is_indexable_path("Dockerfile") is True
    assert is_indexable_path("backend/.venv/lib/site-packages/fastapi/main.py") is False
    assert is_indexable_path("frontend/node_modules/react/index.js") is False
    assert is_indexable_path(".git/HEAD") is False

    chunks = chunk_code_file("backend/app/main.py", SAMPLE_PYTHON_CODE, chunk_lines=5, overlap_lines=2)
    assert len(chunks) > 0
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 5
    assert "Personal AI Core" in chunks[0]["content"]
    assert chunks[1]["start_line"] == 4  # (5 - 2 = 3 step -> line 4)


@pytest.mark.asyncio
async def test_repository_api_crud(async_client: AsyncClient, db_session: AsyncSession):
    """Test repository registration, listing, retrieval, and deletion with workspace isolation."""
    # 1. Register & login
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "devlead@example.com",
        "password": "Password123!",
        "full_name": "Dev Lead"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"name": "DevLab"}, headers=headers)
    ws_id = ws_res.json()["id"]

    # 3. Connect repository
    create_res = await async_client.post(
        f"/api/v1/repositories?workspace_id={ws_id}",
        json={
            "name": "Personal AI Core",
            "owner": "abhay",
            "repo_name": "personal-ai-core",
            "default_branch": "master",
            "token": "ghp_test_mock_token_12345"
        },
        headers=headers
    )
    assert create_res.status_code == 201
    repo_data = create_res.json()
    repo_id = repo_data["id"]
    assert repo_data["has_token"] is True
    assert repo_data["owner"] == "abhay"

    # 4. List repositories
    list_res = await async_client.get(f"/api/v1/repositories?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == repo_id

    # 5. Delete repository
    del_res = await async_client.delete(f"/api/v1/repositories/{repo_id}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_code_indexing_and_search(db_session: AsyncSession):
    """Test CodeIndexer and CodeSearchEngine with real FastEmbed embeddings."""
    user = User(
        id=uuid.uuid4(),
        email="coder@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Coder"
    )
    ws = Workspace(id=uuid.uuid4(), name="Engineering WS", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    repo = CodeRepository(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        name="AI Core Repo",
        owner="google",
        repo_name="ai-core",
        default_branch="main"
    )
    db_session.add_all([user, ws, ws_member, repo])
    await db_session.commit()

    # Index files
    files = [
        {"path": "backend/app/health.py", "content": SAMPLE_PYTHON_CODE},
        {"path": "frontend/src/nav.ts", "content": SAMPLE_TYPESCRIPT_CODE}
    ]
    indexed_count = await CodeIndexer.index_repository_files(db=db_session, repository=repo, files=files)
    assert indexed_count == 2
    assert repo.is_indexed is True
    assert repo.file_count == 2

    # Semantic code search
    search_results = await CodeSearchEngine.search(
        db=db_session,
        workspace_id=ws.id,
        query="uptime monitoring endpoint and health check",
        top_k=2
    )
    assert len(search_results) > 0
    top = search_results[0]
    assert top["file_path"] == "backend/app/health.py"
    assert "health_check" in top["content"]
    assert top["similarity_score"] > 0.3


@pytest.mark.asyncio
async def test_developer_tools_execution(db_session: AsyncSession):
    """Test repo_file_tree, repo_read_file, and repo_code_search tools via ToolRegistry."""
    user = User(
        id=uuid.uuid4(),
        email="architect@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Architect"
    )
    ws = Workspace(id=uuid.uuid4(), name="Arch WS", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    repo = CodeRepository(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        name="Personal Core",
        owner="owner",
        repo_name="core",
        default_branch="main"
    )
    db_session.add_all([user, ws, ws_member, repo])
    await db_session.commit()

    # Index sample files
    files = [
        {"path": "backend/app/health.py", "content": SAMPLE_PYTHON_CODE},
        {"path": "frontend/src/nav.ts", "content": SAMPLE_TYPESCRIPT_CODE}
    ]
    await CodeIndexer.index_repository_files(db=db_session, repository=repo, files=files)

    # 1. Test repo_file_tree
    tree_res = await tool_registry.execute_tool(
        name="repo_file_tree",
        arguments={},
        workspace_id=ws.id,
        db=db_session
    )
    assert tree_res["success"] is True
    file_list = tree_res["result"]["files"]
    assert "backend/app/health.py" in file_list
    assert "frontend/src/nav.ts" in file_list

    # 2. Test repo_read_file
    read_res = await tool_registry.execute_tool(
        name="repo_read_file",
        arguments={
            "file_path": "backend/app/health.py",
            "start_line": 6,
            "end_line": 12
        },
        workspace_id=ws.id,
        db=db_session
    )
    assert read_res["success"] is True
    result_data = read_res["result"]
    assert result_data["file_path"] == "backend/app/health.py"
    assert "health_check" in result_data["content"]
    assert "6 | " in result_data["content"]

    # 3. Test repo_code_search
    search_res = await tool_registry.execute_tool(
        name="repo_code_search",
        arguments={"query": "navigation item render"},
        workspace_id=ws.id,
        db=db_session
    )
    assert search_res["success"] is True
    matches = search_res["result"]["results"]
    assert len(matches) > 0
    assert matches[0]["file_path"] == "frontend/src/nav.ts"


def test_developer_assistant_agent_spec():
    """Verify Developer Assistant agent definition and tool permissions."""
    agent = DeveloperAssistantAgent()
    assert agent.name == "developer_assistant"
    assert "repo_read_file" in agent.allowed_tools
    assert "repo_code_search" in agent.allowed_tools
    assert "repo_file_tree" in agent.allowed_tools
    assert "cite specific file paths" in agent.get_system_prompt().lower()
