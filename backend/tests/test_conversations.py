"""Tests for conversations, messages, and strict workspace boundary isolation."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_lifecycle_and_workspace_isolation(async_client: AsyncClient):
    """Verify conversation CRUD, message persistence, and cross-workspace access rejection."""
    # 1. Register User A
    user_a_res = await async_client.post("/api/v1/auth/register", json={
        "email": "user_a@example.com",
        "password": "PasswordUserA123!",
        "full_name": "User Alpha"
    })
    token_a = user_a_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Fetch User A's workspace
    ws_a_res = await async_client.get("/api/v1/workspaces", headers=headers_a)
    assert ws_a_res.status_code == 200
    workspaces_a = ws_a_res.json()
    assert len(workspaces_a) >= 1
    workspace_a_id = workspaces_a[0]["id"]

    # 2. Register User B
    user_b_res = await async_client.post("/api/v1/auth/register", json={
        "email": "user_b@example.com",
        "password": "PasswordUserB123!",
        "full_name": "User Beta"
    })
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Fetch User B's workspace
    ws_b_res = await async_client.get("/api/v1/workspaces", headers=headers_b)
    assert ws_b_res.status_code == 200
    workspace_b_id = ws_b_res.json()[0]["id"]

    # 3. User A creates a conversation in Workspace A
    conv_create_res = await async_client.post(
        "/api/v1/conversations",
        headers=headers_a,
        json={
            "workspace_id": workspace_a_id,
            "title": "Architecture Discussion",
            "model_provider": "openai",
            "model_name": "gpt-4o"
        }
    )
    assert conv_create_res.status_code == 201
    conversation_a_id = conv_create_res.json()["id"]

    # 4. User A posts messages into Conversation A
    msg1_res = await async_client.post(
        f"/api/v1/conversations/{conversation_a_id}/messages",
        headers=headers_a,
        json={"role": "user", "content": "How do we structure the modular monolith?"}
    )
    assert msg1_res.status_code == 201

    msg2_res = await async_client.post(
        f"/api/v1/conversations/{conversation_a_id}/messages",
        headers=headers_a,
        json={"role": "assistant", "content": "Keep core logic decoupled from web endpoints."}
    )
    assert msg2_res.status_code == 201

    # 5. User A retrieves conversation with message history
    get_conv_res = await async_client.get(
        f"/api/v1/conversations/{conversation_a_id}",
        headers=headers_a
    )
    assert get_conv_res.status_code == 200
    conv_data = get_conv_res.json()
    assert len(conv_data["messages"]) == 2
    assert conv_data["messages"][0]["role"] == "user"
    assert conv_data["messages"][1]["role"] == "assistant"

    # =========================================================================
    # 6. SECURITY CHECK: User B attempts to access Workspace A's conversation
    # =========================================================================
    unauthorized_get = await async_client.get(
        f"/api/v1/conversations/{conversation_a_id}",
        headers=headers_b
    )
    assert unauthorized_get.status_code == 403
    assert "access to this workspace" in unauthorized_get.json()["detail"]

    # User B attempts to post message to User A's conversation
    unauthorized_post = await async_client.post(
        f"/api/v1/conversations/{conversation_a_id}/messages",
        headers=headers_b,
        json={"role": "user", "content": "Can I infiltrate this conversation?"}
    )
    assert unauthorized_post.status_code == 403

    # User B attempts to list conversations from Workspace A
    unauthorized_list = await async_client.get(
        f"/api/v1/conversations?workspace_id={workspace_a_id}",
        headers=headers_b
    )
    assert unauthorized_list.status_code == 403

    # User B attempts to create conversation inside Workspace A
    unauthorized_create = await async_client.post(
        "/api/v1/conversations",
        headers=headers_b,
        json={
            "workspace_id": workspace_a_id,
            "title": "Malicious Conversation"
        }
    )
    assert unauthorized_create.status_code == 403

    # 7. User A updates conversation title
    update_res = await async_client.patch(
        f"/api/v1/conversations/{conversation_a_id}",
        headers=headers_a,
        json={"title": "Updated Architecture Discussion"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Architecture Discussion"

    # 8. User A deletes conversation
    delete_res = await async_client.delete(
        f"/api/v1/conversations/{conversation_a_id}",
        headers=headers_a
    )
    assert delete_res.status_code == 204

    # 9. Verify conversation is deleted
    not_found_res = await async_client.get(
        f"/api/v1/conversations/{conversation_a_id}",
        headers=headers_a
    )
    assert not_found_res.status_code == 404
