"""Unit and integration tests for authentication workflows."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    """Verify user registration returns token pair and creates user."""
    payload = {
        "email": "developer@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Test Developer"
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """Verify duplicate email registration returns 409 Conflict."""
    payload = {
        "email": "developer@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Initial Developer"
    }
    # First registration
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with identical email
    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Verify login with correct credentials returns token pair."""
    # Register first
    await async_client.post("/api/v1/auth/register", json={
        "email": "login_test@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Login Tester"
    })

    # Login
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "login_test@example.com",
        "password": "SuperSecretPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """Verify login with wrong password returns 401 Unauthorized."""
    # Register first
    await async_client.post("/api/v1/auth/register", json={
        "email": "wrong_pwd@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Password Tester"
    })

    response = await async_client.post("/api/v1/auth/login", json={
        "email": "wrong_pwd@example.com",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_profile(async_client: AsyncClient):
    """Verify /me profile endpoint returns user profile."""
    # Register
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "profile_test@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Profile Tester"
    })
    token = reg_res.json()["access_token"]

    # Call /me with token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "profile_test@example.com"
    assert me_data["full_name"] == "Profile Tester"
    assert me_data["is_active"] is True


@pytest.mark.asyncio
async def test_token_rotation_and_revocation(async_client: AsyncClient):
    """Verify refresh token rotation and subsequent rejection of used tokens."""
    # 1. Register
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "rotation_test@example.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Rotation Tester"
    })
    first_refresh = reg_res.json()["refresh_token"]

    # 2. Rotate token
    refresh_res = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": first_refresh
    })
    assert refresh_res.status_code == 200
    second_refresh = refresh_res.json()["refresh_token"]
    assert second_refresh != first_refresh

    # 3. Attempting to reuse first_refresh must fail (401)
    reuse_res = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": first_refresh
    })
    assert reuse_res.status_code == 401

    # 4. Logout using second_refresh
    logout_res = await async_client.post("/api/v1/auth/logout", json={
        "refresh_token": second_refresh
    })
    assert logout_res.status_code == 204

    # 5. Attempting to use second_refresh after logout must fail
    after_logout_res = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": second_refresh
    })
    assert after_logout_res.status_code == 401
