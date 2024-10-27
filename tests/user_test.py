import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from main import app
from classes.User import User, UserLogin, UpdatePassword
client = TestClient(app)


class TestCreateUser(unittest.TestCase):
    @patch("your_module.get_db")
    @patch("your_module.pwd_context")
    def test_create_user(self, mock_pwd_context, mock_get_db):
        # Mocking DB and hashing
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_get_db.return_value = (mock_cursor, mock_connection)
        mock_pwd_context.hash.return_value = "hashed_password"

        user_data = {
            "username": "testuser",
            "password": "testpassword",
            "employee_id": 1,
            "access_level": 2
        }

        response = client.post("/user/reg", json=user_data)

        # Simulate stored procedure and DB responses
        mock_cursor.callproc.assert_called_once_with("create_user_account", ["testuser", "hashed_password", 1, 2])
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE username = %s", ("testuser",))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "User registered successfully")


class TestLoginUser(unittest.TestCase):
    @patch("db.db.get_db")
    @patch("core.security.verify_password")
    @patch("core.security.create_access_token")
    def test_login_user(self, mock_create_access_token, mock_verify_password, mock_get_db):
        # Mocking DB and security functions
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_get_db.return_value = (mock_cursor, mock_connection)
        mock_verify_password.return_value = True

        user_data = {
            "username": "Umesha",
            "password": "Umesha"
        }

        # Mock DB responses
        mock_cursor.fetchone.return_value = {"username": "Umesha", "password": "Umesha"}
        mock_cursor.stored_results.return_value = iter([Mock(fetchone=lambda: {"user_role": "admin"})])

        response = client.post("/login", json=user_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "Umesha")
        self.assertEqual(response.json()["role"], "admin")


class TestUpdateUserPassword(unittest.TestCase):
    @patch("db.db.get_db")
    @patch("core.security.verify_password")
    def test_update_user_password(self, mock_get_current_active_user, mock_get_db):
        # Mock DB and current user
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_get_db.return_value = (mock_cursor, mock_connection)
        mock_get_current_active_user.return_value = {"username": "admin"}

        new_password_data = {"password": "newpassword"}

        response = client.put("/user/testuser", json=new_password_data)

        mock_cursor.execute.assert_called_once_with(
            "UPDATE users SET password = %s WHERE username = %s",
            ("newpassword", "testuser")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "User access updated successfully")


if __name__ == '__main__':
    unittest.main()
