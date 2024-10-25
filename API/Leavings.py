import os

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List
from classes import Leavings
from core.security import get_current_active_user  # Assuming this function is implemented in core.security
router = APIRouter()
from dotenv import load_dotenv

# Dependency for OAuth2 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
load_dotenv()


# Database connection dependency
def get_db():
    connection = mysql.connector.connect(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME'))
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()


# Pydantic models for the Leave_Request entity


# Endpoint to create a new leave request (accessible by employees)
@router.post("/leave/request", status_code=status.HTTP_201_CREATED)
def create_leave_request(leave_request: Leavings.LeaveRequestCreate, db=Depends(get_db),
        current_user=Depends(get_current_active_user)  # Enforces JWT token authentication
):
    cursor, connection = db
    try:
        cursor.callproc("create_leave_request", [leave_request.employee_id,leave_request.leave_start_date,leave_request.period_of_absence,leave_request.reason_for_absence,leave_request.type_of_leave,])
        connection.commit()

        return "Leave requested successfully"

    except mysql.connector.Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating leave request: {str(e)}")


# Endpoint to read leave request details (accessible to employees and supervisors)
@router.get("/leave/request/{leave_request_id}", response_model=Leavings.LeaveRequestResponse)
def read_leave_request(leave_request_id: int, db=Depends(get_db), current_user=Depends(get_current_active_user)
        # Enforces JWT token authentication
):
    cursor, _ = db
    cursor.execute("SELECT * FROM leave_request WHERE leave_request_id = %s", (leave_request_id,))
    leave_request_record = cursor.fetchone()
    if not leave_request_record:
        raise HTTPException(status_code=404, detail="Leave request not found")

    return leave_request_record

#
# Endpoint to update leave request details (accessible by supervisors)
@router.put("/leave/request/{leave_request_id}", response_model=Leavings.LeaveRequestResponse)
def update_leave_request(leave_request_id: int, leave_request: Leavings.LeaveRequestUpdate, db=Depends(get_db),
        current_user=Depends(get_current_active_user)  # Enforces JWT token authentication
):
    if not current_user.is_supervisor:  # Check if the user is a supervisor
        raise HTTPException(status_code=403, detail="Not authorized to update leave requests")

    cursor, connection = db
    try:
        cursor.execute(
            "UPDATE Leave_Request SET Period_of_Absence=%s, Reason_for_Absence=%s, Type_of_Leave=%s, Request_Status=%s "
            "WHERE Leave_Request_ID=%s", (
            leave_request.Period_of_Absence, leave_request.Reason_for_Absence, leave_request.Type_of_Leave,
            leave_request.Request_Status, leave_request_id))
        connection.commit()
        cursor.execute("SELECT * FROM Leave_Request WHERE Leave_Request_ID = %s", (leave_request_id,))
        updated_leave_request = cursor.fetchone()

        if not updated_leave_request:
            raise HTTPException(status_code=404, detail="Leave request not found")
        return updated_leave_request

    except mysql.connector.Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating leave request: {str(e)}")


# Endpoint to delete a leave request (admin or supervisor only)
@router.delete("/leave/request/{leave_request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_leave_request(leave_request_id: int, db=Depends(get_db), current_user=Depends(get_current_active_user)
        # Enforces JWT token authentication
):
    cursor, connection = db
    cursor.execute("SELECT is_supervisor FROM user_access WHERE username = %s", (current_user.username,))
    user_role = cursor.fetchone()
    if not user_role:  # Check if the user is an admin or supervisor
        raise HTTPException(status_code=403, detail="Not authorized to delete leave requests")

    try:
        cursor.callproc("delete_request", [leave_request_id,])
        connection.commit()
        return "Request deleted successfully"

    except mysql.connector.Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting leave request: {str(e)}")


@router.get("/supervisor/leave_requests", response_model=List[Leavings.LeaveRequestResponse])
def get_team_leave_requests(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, _ = db

    # Verify that the current user is a supervisor
    cursor.execute("SELECT is_supervisor FROM user_access WHERE username = %s", (current_user.username,))
    user_role = cursor.fetchone()

    if not user_role or not user_role['is_supervisor']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have permission to view this information")

    # Fetch the supervisor ID - passing only the username as a string
    cursor.callproc('get_employee_id_by_username', (current_user.username,))
    supervisor_result = next(cursor.stored_results()).fetchone()

    if not supervisor_result:
        raise HTTPException(status_code=404, detail="Supervisor ID not found.")

    # Extract supervisor ID from the result
    supervisor_id = supervisor_result['employee_id']  # Assuming the stored procedure returns a single value, e.g., an employee ID

    # Fetch all leave requests for employees reporting to this supervisor
    cursor.callproc('leave_request_Pending_list', (supervisor_id,))
    leave_requests = next(cursor.stored_results()).fetchall()

    if not leave_requests:
        raise HTTPException(status_code=404, detail="No leave requests found for your team")

    # Map SQL query results to the LeaveRequestResponse model
    leave_requests_response = [
        Leavings.LeaveRequestResponse(
            first_name =row['first_name'],
            last_name = row['last_name'],
            gender = row['gender'],
            leave_request_id=row['leave_request_id'],
            employee_id=row['employee_id'],
            request_date=row['request_date'],
            leave_start_date=row['leave_start_date'],
            period_of_absence=row['period_of_absence'],
            reason_for_absence=row['reason_for_absence'],
            type_of_leave=row['type_of_leave'],
            request_status=row['request_status']
        ) for row in leave_requests
    ]

    return leave_requests_response

