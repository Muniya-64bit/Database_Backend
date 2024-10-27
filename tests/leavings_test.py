import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app  # Replace with the actual location of your FastAPI app instance

client = TestClient(app)


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_create_leave_request(mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)

    # Set up mock data
    leave_request_data = {
        "employee_id": 123,
        "leave_start_date": "2024-10-20",
        "period_of_absence": 5,
        "reason_for_absence": "Vacation",
        "type_of_leave": "Paid"
    }

    # Mock stored procedure call
    mock_cursor.callproc.return_value = None

    # Run the test
    response = client.post("/leave/request", json=leave_request_data)
    assert response.status_code == 201
    assert response.json() == "Leave requested successfully"

    # Test database transaction commit
    mock_connection.commit.assert_called_once()


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_read_leave_request(mock_get_db):
    mock_cursor = MagicMock()
    mock_get_db.return_value = (mock_cursor, None)

    # Mock response from the database
    mock_cursor.fetchone.return_value = {
        "leave_request_id": 1,
        "employee_id": 123,
        "leave_start_date": "2024-10-20",
        "period_of_absence": 5,
        "reason_for_absence": "Vacation",
        "type_of_leave": "Paid",
        "request_status": "Pending"
    }

    response = client.get("/leave/request/1")
    assert response.status_code == 200
    assert response.json()["leave_request_id"] == 1
    assert response.json()["employee_id"] == 123


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_update_leave_request(mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)

    # Test data
    update_data = {
        "period_of_absence": 7,
        "reason_for_absence": "Medical leave",
        "type_of_leave": "Paid",
        "request_status": "Approved"
    }

    # Mock database responses
    mock_cursor.execute.side_effect = [
        None,  # for update
        {"leave_request_id": 1, "period_of_absence": 7, "reason_for_absence": "Medical leave", "type_of_leave": "Paid"}
    ]

    response = client.put("/leave/request/1", json=update_data)
    assert response.status_code == 200
    assert response.json()["period_of_absence"] == 7
    assert response.json()["request_status"] == "Approved"


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_delete_leave_request(mock_get_db):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_get_db.return_value = (mock_cursor, mock_connection)

    # Mock stored procedure for deleting request
    mock_cursor.callproc.return_value = None

    response = client.delete("/leave/request/1")
    assert response.status_code == 204
    mock_connection.commit.assert_called_once()


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_get_team_leave_requests(mock_get_db):
    mock_cursor = MagicMock()
    mock_get_db.return_value = (mock_cursor, None)

    # Mock responses
    mock_cursor.execute.side_effect = [None, None]  # User access check and employee ID fetch
    mock_cursor.callproc.return_value = None
    mock_cursor.stored_results.return_value = [
        MagicMock(fetchall=lambda: [
            {
                "leave_request_id": 1,
                "employee_id": 123,
                "first_name": "John",
                "last_name": "Doe",
                "request_date": "2024-10-20",
                "leave_start_date": "2024-10-25",
                "period_of_absence": 5,
                "reason_for_absence": "Vacation",
                "type_of_leave": "Paid",
                "request_status": "Pending"
            }
        ])
    ]

    response = client.get("/supervisor/leave_requests")
    assert response.status_code == 200
    assert response.json()[0]["first_name"] == "John"
    assert len(response.json()) == 1


@pytest.mark.asyncio
@patch("your_module.get_db")
async def test_all_leaves(mock_get_db):
    mock_cursor = MagicMock()
    mock_get_db.return_value = (mock_cursor, None)

    # Mock responses for user access check and leave request retrieval
    mock_cursor.execute.side_effect = [None]  # Admin access check
    mock_cursor.callproc.return_value = None
    mock_cursor.stored_results.return_value = [
        MagicMock(fetchall=lambda: [
            {
                "leave_request_id": 1,
                "employee_id": 123,
                "first_name": "Alice",
                "last_name": "Smith",
                "request_date": "2024-10-20",
                "leave_start_date": "2024-10-25",
                "period_of_absence": 7,
                "reason_for_absence": "Conference",
                "type_of_leave": "Paid",
                "request_status": "Approved"
            }
        ])
    ]

    response = client.get("/admin_leaves")
    assert response.status_code == 200
    assert response.json()[0]["first_name"] == "Alice"
    assert len(response.json()) == 1
