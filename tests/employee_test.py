import pytest
from fastapi.testclient import TestClient

from API.leavings import get_db
from core.security import get_current_active_user
from main import app  # Import your FastAPI app
from classes import employee  # Assuming 'employee' module has classes for EmployeeCreate and EmployeeUpdate
from unittest.mock import Mock

client = TestClient(app)

# Mock dependencies
def override_get_db():
    mock_cursor = Mock()
    mock_connection = Mock()
    return mock_cursor, mock_connection

def override_get_current_active_user():
    return Mock(username="test_user", employee_id="12345")

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_active_user] = override_get_current_active_user

@pytest.fixture
def mock_employee_data():
    return employee.EmployeeCreate(
        first_name="John", last_name="Doe", birthday="1990-01-01",
        nic="123456789V", gender="Male", marital_status="Single",
        number_of_dependents=0, address="123 Main St", contact_number="555123456",
        business_email="john.doe@example.com", job_title="Engineer",
        employee_status="Active", department_name="Engineering", branch_name="HQ",
        profile_photo=None, emergency_contact_name="Jane Doe", emergency_contact_nic="987654321V",
        emergency_contact_address="456 Another St", emergency_contact_number="555987654"
    )

### Test Cases

# Test employee creation
def test_create_employee(mock_employee_data):
    response = client.post("/employee/new", json=mock_employee_data.dict())
    assert response.status_code == 201
    assert response.json() == {"message": "Employee created successfully"}

# Test reading employee data
def test_read_employee():
    response = client.get("/employee/test_user")
    assert response.status_code == 200
    assert "first_name" in response.json()

# Test updating employee data
def test_update_employee(mock_employee_data):
    update_data = {"first_name": "Jane", "last_name": "Doe", "job_title": "Senior Engineer"}
    response = client.put("/employee/test_user", json=update_data)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"

# Test deleting an employee
def test_delete_employee():
    response = client.delete("/employee/12345")
    assert response.status_code == 200
    assert response.json() == {"message": "Employee 12345 deleted successfully"}

# Test employee of the month retrieval
def test_employee_of_the_month():
    response = client.get("/employee_of_month")
    assert response.status_code == 200
    assert "message" in response.json()

# Test getting employees on leave
def test_get_on_leave():
    response = client.get("/on_leave")
    assert response.status_code == 200
    assert "message" in response.json()

# Test getting full-time employees for today
def test_get_on_fulltime():
    response = client.get("/today_full_time")
    assert response.status_code == 200
    assert "message" in response.json()

# Test getting part-time employees for today
def test_get_on_halftome():
    response = client.get("/today_half_time")
    assert response.status_code == 200
    assert "message" in response.json()
