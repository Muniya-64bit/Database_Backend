import uuid
import mysql.connector
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from classes import employee
from core.middleware import logger
from core.security import get_current_active_user
from db.db import get_db

# Initialize the router
router = APIRouter()

# Polling helper function
async def poll_endpoint(func, check_condition, delay=5, max_retries=5, *args, **kwargs):
    retries = 0
    while retries < max_retries:
        response = await func(*args, **kwargs)
        if check_condition(response):
            return response
        await asyncio.sleep(delay)
        retries += 1
    raise HTTPException(status_code=408, detail="Request timed out")

# Endpoint for creating a new employee
@router.post("/employee/new", status_code=status.HTTP_201_CREATED)
async def create_employee(employee: employee.EmployeeCreate, db=Depends(get_db),
                          current_user=Depends(get_current_active_user)):
    cursor, connection = db
    logger.info(f"Attempting to create employee: {employee.employee_id}")

    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        employee_id = user_record["employee_id"]
        employee.employee_id = str(uuid.uuid4())

        # Check authorization using a user-defined function
        if current_user.employee_id != employee_id and not cursor.callproc("is_admin", [current_user.username]):
            raise HTTPException(status_code=403, detail="Not authorized to add an employee")

        # Call the 'add_employee' stored procedure
        cursor.callproc("add_employee", [employee.employee_id, employee.first_name, employee.last_name,
                                         employee.birthday, employee.nic, employee.gender, employee.marital_status,
                                         employee.number_of_dependents, employee.address, employee.contact_number,
                                         employee.business_email, employee.job_title, employee.employee_status,
                                         employee.department_name, employee.branch_name, employee.profile_photo,
                                         employee.emergency_contact_name, employee.emergency_contact_nic,
                                         employee.emergency_contact_address, employee.emergency_contact_number])
        connection.commit()

        # Fetch the newly created employee record using a stored procedure
        cursor.callproc("select_employee_details", [employee.employee_id])
        new_employee = next(cursor.stored_results()).fetchone()
        if not new_employee:
            raise HTTPException(status_code=404, detail="Employee creation failed")

        return {"message": "Employee created successfully"}

    except mysql.connector.Error as e:
        logger.error(f"Database error while creating employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get("/employee_of_month")
async def get_employee_of_the_month_polling(background_tasks: BackgroundTasks, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    async def fetch_employee_of_month():
        cursor, connection = db
        cursor.callproc("employee_of_the_month")
        employee_of_month = next(cursor.stored_results()).fetchone()
        if employee_of_month:
            logger.info(f"Employee of the month: {employee_of_month}")
            return employee_of_month
        return None

    # Define a condition function to stop polling when an employee of the month is found
    check_condition = lambda result: result is not None

    # Schedule polling with a delay and a maximum number of retries
    try:
        employee_of_month = await poll_endpoint(fetch_employee_of_month, check_condition, delay=5, max_retries=10)
        return {"employee_of_the_month": employee_of_month}
    except HTTPException as e:
        logger.error("Error during polling for employee of the month")
        raise e

# Additional endpoints (read_employee, delete_employee, update_employee, etc.) remain unchanged.

@router.delete("/employee/{employee_id}", status_code=status.HTTP_200_OK)
async def delete_employee(employee_id: str, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db

    try:
        logger.info(f"Attempting to delete employee with ID: {employee_id} by user: {current_user.username}")

        cursor.callproc("get_usernme_by_employee_id", [employee_id])
        username = next(cursor.stored_results()).fetchone()

        if not username:
            logger.warning(f"Username for employee_id {employee_id} not found")
            raise HTTPException(status_code=404, detail="Employee username not found")

        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            logger.error(f"Current user {current_user.username} not found")
            raise HTTPException(status_code=404, detail="Current user not found")

        current_user_employee_id = user_record['employee_id']
        employee_id_to_delete = employee_id

        logger.info(f"User {current_user.username} is attempting to delete employee with ID: {employee_id_to_delete}")

        cursor.callproc("is_admin", [current_user.username])
        is_admin = next(cursor.stored_results()).fetchone()

        if not is_admin:
            logger.warning(f"User {current_user.username} is not authorized to delete employee {employee_id_to_delete}")
            raise HTTPException(status_code=403, detail="Not authorized to delete this employee")

        cursor.callproc("delete_employee", [current_user_employee_id, employee_id_to_delete])
        connection.commit()

        logger.info(f"Employee {employee_id_to_delete} deleted successfully by user {current_user.username}")

        return {"message": f"Employee {employee_id_to_delete} deleted successfully"}

    except mysql.connector.Error as e:
        logger.error(f"Database error while deleting employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")
