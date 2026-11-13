"""Tests for Phase 5 Database Integrations and Read-Only Tools."""
import os
import uuid
import pytest
import aiosqlite
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.encryption import encrypt_secret, decrypt_secret, mask_secret
from app.integrations.base import validate_identifier
from app.tools.registry import tool_registry
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.integration import Integration
from app.core.security import hash_password


@pytest.fixture
def sample_sqlite_db(tmp_path):
    """Creates a temporary SQLite database with a sample schema and records."""
    db_file = str(tmp_path / "test_warehouse.db")
    import sqlite3
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE sensitive_salaries (
            id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            salary REAL NOT NULL
        );
    """)
    cursor.executemany(
        "INSERT INTO products (name, price, category) VALUES (?, ?, ?);",
        [
            ("Laptop Pro", 1299.99, "Electronics"),
            ("Wireless Mouse", 29.99, "Electronics"),
            ("Coffee Mug", 12.50, "Kitchen"),
            ("Standing Desk", 450.00, "Furniture"),
        ]
    )
    cursor.execute("INSERT INTO sensitive_salaries VALUES (1, 'Alice CEO', 250000);")
    conn.commit()
    conn.close()
    return db_file


@pytest.mark.asyncio
async def test_encryption_and_masking():
    """Verify credentials encryption, decryption, and masking."""
    secret = "SuperSecretPassword123!"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert isinstance(encrypted, str)

    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret

    masked = mask_secret(secret)
    assert masked == "••••••••"
    assert mask_secret(None) is None


@pytest.mark.asyncio
async def test_sql_identifier_validation():
    """Verify rejection of SQL injection characters in table and column identifiers."""
    # Valid identifiers
    assert validate_identifier("users") == "users"
    assert validate_identifier("order_items_2026") == "order_items_2026"
    assert validate_identifier("_internal") == "_internal"

    # Invalid identifiers / SQL injection payloads
    with pytest.raises(ValueError):
        validate_identifier("users; DROP TABLE users;")
    with pytest.raises(ValueError):
        validate_identifier("users--comment")
    with pytest.raises(ValueError):
        validate_identifier("123users")
    with pytest.raises(ValueError):
        validate_identifier("users WHERE 1=1")
    with pytest.raises(ValueError):
        validate_identifier("")


@pytest.mark.asyncio
async def test_integrations_api_crud_and_testing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_sqlite_db: str
):
    """Test API endpoints for creating, listing, testing, and deleting integrations."""
    # 1. Register and login
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "dbowner@example.com",
        "password": "Password123!",
        "full_name": "Database Owner"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"name": "Analytics WS"}, headers=headers)
    ws_id = ws_res.json()["id"]

    # 3. Test unsaved connection
    test_unsaved = await async_client.post("/api/v1/integrations/test", json={
        "integration_type": "sqlite",
        "database": sample_sqlite_db
    }, headers=headers)
    assert test_unsaved.status_code == 200
    assert test_unsaved.json()["success"] is True
    assert "SQLite" in test_unsaved.json()["version"]

    # 4. Create integration with approved_tables restriction
    create_res = await async_client.post(
        f"/api/v1/integrations?workspace_id={ws_id}",
        json={
            "name": "Warehouse DB",
            "integration_type": "sqlite",
            "database": sample_sqlite_db,
            "approved_tables": ["products"]
        },
        headers=headers
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    integration_id = created_data["id"]
    assert created_data["name"] == "Warehouse DB"
    assert created_data["approved_tables"] == ["products"]

    # 5. List integrations
    list_res = await async_client.get(f"/api/v1/integrations?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == integration_id

    # 6. Test saved connection
    test_saved = await async_client.post(f"/api/v1/integrations/{integration_id}/test", headers=headers)
    assert test_saved.status_code == 200
    assert test_saved.json()["success"] is True

    # 7. Inspect schemas via API (verifying approved_tables filtering)
    schema_res = await async_client.get(f"/api/v1/integrations/{integration_id}/schemas", headers=headers)
    assert schema_res.status_code == 200
    schemas_data = schema_res.json()
    assert len(schemas_data["tables"]) == 1
    assert schemas_data["tables"][0]["table_name"] == "products"
    # sensitive_salaries must NOT be included because of approved_tables
    table_names = [t["table_name"] for t in schemas_data["tables"]]
    assert "sensitive_salaries" not in table_names

    # 8. Delete integration
    del_res = await async_client.delete(f"/api/v1/integrations/{integration_id}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_db_tools_execution_and_security(
    db_session: AsyncSession,
    sample_sqlite_db: str
):
    """Test ToolRegistry execution for db_metadata_inspector and db_query_tool."""
    # 1. Setup user & workspace
    user = User(
        id=uuid.uuid4(),
        email="analyst@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Analyst"
    )
    ws = Workspace(id=uuid.uuid4(), name="Data Lab", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    integration = Integration(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        name="Sales SQLite",
        integration_type="sqlite",
        database=sample_sqlite_db,
        approved_tables=["products"],
        is_active=True
    )
    db_session.add_all([user, ws, ws_member, integration])
    await db_session.commit()

    # 2. Test metadata inspection tool
    meta_result = await tool_registry.execute_tool(
        name="db_metadata_inspector",
        arguments={},
        workspace_id=ws.id,
        db=db_session
    )
    assert meta_result["success"] is True
    res_data = meta_result["result"]
    assert res_data["integration_name"] == "Sales SQLite"
    assert len(res_data["tables"]) == 1
    assert res_data["tables"][0]["table_name"] == "products"

    # 3. Test safe read query on approved table
    query_result = await tool_registry.execute_tool(
        name="db_query_tool",
        arguments={
            "table_name": "products",
            "columns": ["id", "name", "price"],
            "filters": {"category": "Electronics"},
            "order_by": "price",
            "order_desc": True,
            "limit": 10
        },
        workspace_id=ws.id,
        db=db_session
    )
    assert query_result["success"] is True
    rows = query_result["result"]["rows"]
    assert len(rows) == 2
    assert rows[0]["name"] == "Laptop Pro"
    assert rows[1]["name"] == "Wireless Mouse"

    # 4. Security: Rejection of unapproved table
    unapproved_res = await tool_registry.execute_tool(
        name="db_query_tool",
        arguments={"table_name": "sensitive_salaries"},
        workspace_id=ws.id,
        db=db_session
    )
    assert unapproved_res["success"] is True
    assert "error" in unapproved_res["result"]
    assert "not in the approved tables list" in unapproved_res["result"]["error"]

    # 5. Security: SQL Injection attempt in table name rejected
    injection_res = await tool_registry.execute_tool(
        name="db_query_tool",
        arguments={"table_name": "products; DROP TABLE products;"},
        workspace_id=ws.id,
        db=db_session
    )
    assert injection_res["success"] is True
    assert "error" in injection_res["result"]
    assert "Security restriction" in injection_res["result"]["error"]

    # 6. Workspace isolation: Other workspace cannot access integration
    other_ws_id = uuid.uuid4()
    other_res = await tool_registry.execute_tool(
        name="db_query_tool",
        arguments={"table_name": "products"},
        workspace_id=other_ws_id,
        db=db_session
    )
    assert other_res["success"] is True
    assert "No matching active database integration found" in other_res["result"]["error"]
