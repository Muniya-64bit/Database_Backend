import pytest
from httpx import AsyncClient
from main import app  # Import your FastAPI app here
from unittest.mock import AsyncMock, patch

# Mock database dependency
@pytest.fixture
def mock_db():
    mock_cursor = AsyncMock()
    mock_connection = AsyncMock()
    return (mock_cursor, mock_connection)

# Client to test async routes
@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

# Test user registration
@pytest.mark.asyncio
async def test_create_user(client, mock_db):
    with patch("db/db.py", return_value=mock_db):
        mock_db[0].fetchone.return_value = {"username": "Umesha", "password": "Umesha"}

        response = await client.post(
            "/user/reg",
            json={
                "username": "testuser",
                "password": "testpassword",
                "employee_id": '86ceb943-cbb1-4caa-b259-15e2ed687ae2',
                "access_level": "employee"
            },
        )
        assert response.status_code == 201
        assert response.json() == {
            "message": "User registered successfully",
            "user": {"username": "testuser", "password": "testpassword"}
        }

# Test login
@pytest.mark.asyncio
async def test_login_user(client, mock_db):
    with patch("path.to.get_db", return_value=mock_db):
        mock_db[0].fetchone.return_value = {"username": "testuser", "password": "hashed_pwd"}
        mock_db[0].stored_results.return_value = [{"user_role": "admin"}]

        response = await client.post(
            "/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["role"] == "admin"

# Test update user access
@pytest.mark.asyncio
async def test_update_user_access(client, mock_db):
    with patch("path.to.get_db", return_value=mock_db):
        # Mock admin check and existing user
        mock_db[0].fetchone.side_effect = [
            {"username": "testuser"},  # Target user fetch
            {"is_admin": True}         # Admin check fetch
        ]

        response = await client.put(
            "/user/testuser",
            json={"password": "newpassword"}
        )
        assert response.status_code == 200
        assert response.json() == {"message": "User access updated successfully"}
