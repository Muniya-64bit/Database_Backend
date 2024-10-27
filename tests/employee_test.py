import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app  # Adjust the import according to your application structure
from classes import employee

client = TestClient(app)


class TestEmployeeAPI(unittest.TestCase):

    def setUp(self):
        # Set up a test client and any necessary data
        self.client = TestClient(app)
        self.test_user = employee.User(username="testuser", employee_id="1234", is_admin=False)
        self.admin_user = employee.User(username="adminuser", employee_id="admin123", is_admin=True)

    @patch("core.security.get_current_active_user")
    def test_create_employee(self, mock_get_current_user):
        mock_get_current_user.return_value = self.test_user

        employee_data = {
            "employee_id":"",
            "first_name": "John",
            "last_name": "Doe",
            "birthday": "1990-01-01",
            "nic": "123456789V",
            "gender": "Male",
            "marital_status": "Single",
            "number_of_dependents": 0,
            "address": "123 Main St",
            "contact_number": "1234567890",
            "business_email": "john.doe@example.com",
            "job_title": "Developer",
            "employee_status": "Active",
            "department_name": "Engineering",
            "branch_name": "Head Office",
            "profile_photo": "path/to/photo.jpg",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_nic": "987654321V",
            "emergency_contact_address": "456 Side St",
            "emergency_contact_number": "0987654321"
        }

        response = self.client.post("/employee/new", json=employee_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "Employee created successfully"})

    @patch("core.security.get_current_active_user")
    def test_read_employee(self, mock_get_current_user):
        mock_get_current_user.return_value = self.test_user

        # Mock employee details response
        with patch("your_module.select_employee_details", return_value={"first_name": "John", "last_name": "Doe"}):
            response = self.client.get("/employee/testuser")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"first_name": "John", "last_name": "Doe"})

    @patch("your_module.get_current_active_user")
    def test_update_employee(self, mock_get_current_user):
        mock_get_current_user.return_value = self.admin_user

        employee_update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "birthday": "1991-02-02",
            "nic": "987654321V",
            "gender": "Female",
            "marital_status": "Married",
            "number_of_dependents": 1,
            "address": "789 New St",
            "contact_number": "1231231230",
            "business_email": "jane.smith@example.com",
            "job_title": "Senior Developer",
            "department_id": 1,
            "branch_id": 2
        }

        response = self.client.put("/employee/testuser", json=employee_update_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("first_name", response.json())

    @patch("your_module.get_current_active_user")
    def test_delete_employee(self, mock_get_current_user):
        mock_get_current_user.return_value = self.admin_user

        response = self.client.delete("/employee/1234")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Employee 1234 deleted successfully"})


if __name__ == "__main__":
    unittest.main()
