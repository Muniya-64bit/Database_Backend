# test_endpoints.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import router  # Assuming your routes are in a file named main.py

client = TestClient(router)


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_admin_list(mock_current_user, mock_get_db):
    # Mock database cursor and connection
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)

    # Mock current user as admin
    mock_current_user.return_value = MagicMock(username="adminuser")

    # Mock stored procedure outputs
    mock_cursor.stored_results.return_value = iter([MagicMock(fetchone=lambda: {"is_admin": True}),
                                                    MagicMock(fetchall=lambda: [
                                                        {"first_name": "Admin", "last_name": "User", "employee_id": 1}
                                                    ])])

    response = client.get("/all_admins")
    assert response.status_code == 200
    assert response.json() == [{"first_name": "Admin", "last_name": "User", "employee_id": 1}]


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_all_supervisors(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="adminuser")

    mock_cursor.fetchone.return_value = {"is_admin": True}
    mock_cursor.stored_results.return_value = iter([MagicMock(fetchall=lambda: [
        {"supervisor_id": 1, "first_name": "Alice", "last_name": "Johnson"}
    ])])

    response = client.get("/supervisors")
    assert response.status_code == 200
    assert response.json() == [{"supervisor_id": 1, "first_name": "Alice", "last_name": "Johnson"}]


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_supervisor_team(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="supervisoruser")

    mock_cursor.fetchone.side_effect = [{"is_supervisor": True}]
    mock_cursor.stored_results.side_effect = [
        iter([MagicMock(fetchone=lambda: {"employee_id": 1})]),
        iter([MagicMock(fetchall=lambda: [
            {"employee_id": 2, "first_name": "John", "last_name": "Doe"},
            {"employee_id": 3, "first_name": "Jane", "last_name": "Smith"}
        ])])
    ]

    response = client.get("/supervisor/team/")
    assert response.status_code == 200
    assert response.json() == [
        {"employee_id": 2, "first_name": "John", "last_name": "Doe"},
        {"employee_id": 3, "first_name": "Jane", "last_name": "Smith"}
    ]


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_all_leaves(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="supervisoruser")

    mock_cursor.fetchone.return_value = {"is_supervisor": True}
    mock_cursor.stored_results.return_value = iter([MagicMock(fetchone=lambda: {"employee_id": 1})])
    mock_cursor.fetchall.return_value = [
        {
            "leave_request_id": 1, "employee_id": 2, "request_date": "2023-10-01",
            "leave_start_date": "2023-10-02", "period_of_absence": 3, "reason_for_absence": "Sick Leave",
            "type_of_leave": "Sick", "request_status": "Approved"
        }
    ]

    response = client.get("/team_leaves")
    assert response.status_code == 200
    assert response.json() == [
        {
            "leave_request_id": 1, "employee_id": 2, "request_date": "2023-10-01",
            "leave_start_date": "2023-10-02", "period_of_absence": 3, "reason_for_absence": "Sick Leave",
            "type_of_leave": "Sick", "request_status": "Approved"
        }
    ]


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_get_on_leave(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="adminuser")

    mock_cursor.stored_results.side_effect = [
        iter([MagicMock(fetchone=lambda: {"employee_id": 1})]),
        iter([MagicMock(fetchone=lambda: {"on_leave": 5})])
    ]

    response = client.get("/on_leave")
    assert response.status_code == 200
    assert response.json() == {"message": {"on_leave": 5}}


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_today_full_time(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="adminuser")

    mock_cursor.stored_results.side_effect = [
        iter([MagicMock(fetchone=lambda: {"employee_id": 1})]),
        iter([MagicMock(fetchone=lambda: {"full_time": 10})])
    ]

    response = client.get("/today_full_time")
    assert response.status_code == 200
    assert response.json() == {"message": {"full_time": 10}}


@pytest.mark.asyncio
@patch("main.get_db")
@patch("main.get_current_active_user")
async def test_today_half_time(mock_current_user, mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)
    mock_current_user.return_value = MagicMock(username="adminuser")

    mock_cursor.stored_results.side_effect = [
        iter([MagicMock(fetchone=lambda: {"employee_id": 1})]),
        iter([MagicMock(fetchone=lambda: {"part_time": 3})])
    ]

    response = client.get("/today_half_time")
    assert response.status_code == 200
    assert response.json() == {"message": {"part_time": 3}}
