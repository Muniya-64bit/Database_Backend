import logging
import os
from datetime import datetime

import asyncmy
import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from mysql.connector import pooling

from classes import employee
from classes.employee import EmployeeResponse
from core.security import get_current_active_user

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Query for counting absent employees
router = APIRouter()

# Dependency for OAuth2 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database connection
load_dotenv()

async def get_db():
    connection = mysql.connector.connect(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME'))
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()


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
        # Check authorization using a user-defined function
        if current_user.employee_id != employee_id and not cursor.callproc("is_admin", [current_user.username]):
            raise HTTPException(status_code=403, detail="Not authorized to add an employee")

        # Call the 'add_employee' stored procedure
        cursor.callproc("add_employee", [
            employee.employee_id, employee.first_name, employee.last_name, employee.birthday, employee.nic,
            employee.gender, employee.marital_status, employee.number_of_dependents, employee.address,
            employee.contact_number, employee.business_email, employee.job_title, employee.employee_status,
            employee.department_name, employee.branch_name, employee.profile_photo, employee.emergency_contact_name,
            employee.emergency_contact_nic, employee.emergency_contact_address, employee.emergency_contact_number
        ])
        connection.commit()

        # Fetch the newly created employee record using a stored procedure
        cursor.callproc("select_employee_details", [employee.employee_id])
        new_employee = next(cursor.stored_results()).fetchone()
        if not new_employee:
            raise HTTPException(status_code=404, detail="Employee creation failed")

        return {"message": "Employee created successfully", "employee": new_employee}

    except mysql.connector.Error as e:
        logger.error(f"Database error while creating employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get("/employee/{username}", response_model=employee.EmployeeResponse)
async def read_employee(username: str, db=Depends(get_db),
                        current_user=Depends(get_current_active_user)):
    cursor, _ = db

    try:
        # Fetch the employee_id of the current user (currently logged-in user)
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="Current user not found")

        employee_id = user_record["employee_id"]

        # Check if current user is admin using a separate stored procedure
        cursor.callproc("is_admin", [current_user.username])
        admin_record = next(cursor.stored_results()).fetchone()
        is_admin = admin_record["is_admin"] if admin_record else False

        # Fetch the target employee's employee_id by their username
        cursor.callproc("get_employee_id_by_username", [username])
        target_employee_record = next(cursor.stored_results()).fetchone()

        if not target_employee_record:
            raise HTTPException(status_code=404, detail="Employee not found")

        target_employee_id = target_employee_record["employee_id"]

        # If the current user is not an admin and tries to access another user's data, deny access
        if not is_admin and current_user.employee_id != target_employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this employee's details")

        # Fetch employee details via stored procedure
        cursor.callproc("select_employee_details", [target_employee_id])
        employee_record = next(cursor.stored_results()).fetchone()

        if not employee_record:
            raise HTTPException(status_code=404, detail="Employee details not found")

        logger.info(f"Fetched employee details for {username}")
        return employee_record

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching employee details: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

#
#
@router.delete("/employee/{username}", status_code=status.HTTP_200_OK)
async def delete_employee(username: str, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db

    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        # Fetch the employee_id of the employee to be deleted
        cursor.callproc("get_employee_id_by_username", [username])
        employee_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        if not employee_record:
            raise HTTPException(status_code=404, detail="Employee not found")

        current_user_employee_id = user_record["employee_id"]
        employee_id_to_delete = employee_record["employee_id"]
        cursor.callproc("is_admin",[current_user.username])
        is_admin = next(cursor.stored_results()).fetchone()
        # Check visibility access
        if current_user_employee_id == employee_id_to_delete or not is_admin['is_admin']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this employee")

        # Delete the employee
        cursor.callproc("delete_employee", [current_user_employee_id,employee_id_to_delete])
        connection.commit()

        logger.info(f"Employee {employee_id_to_delete} deleted successfully")

        return {"message": f"Employee {employee_id_to_delete} deleted successfully"}

    except mysql.connector.Error as e:
        logger.error(f"Database error while deleting employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")




logger = logging.getLogger(__name__)


@router.put("/employee/{username}", response_model=employee.EmployeeResponse)
async def update_employee(
        username: str,  # username should be str, not int
        employee_update: employee.EmployeeUpdate,
        db=Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    cursor, connection = db

    try:
        # Fetch the employee ID using the username
        cursor.callproc("get_employee_id_by_username", [username])
        employee_record = next(cursor.stored_results()).fetchone()

        if not employee_record:
            raise HTTPException(status_code=404, detail="Employee not found")

        employee_id = employee_record['employee_id']

        # Check if the current user has admin access or is the employee
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin_record = cursor.fetchone()
        is_admin = is_admin_record["is_admin"] if is_admin_record else False

        # Check authorization
        if current_user.employee_id != employee_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to update this employee's information")

        # Update the employee information
        update_query = """
            UPDATE employee
            SET first_name = %s, last_name = %s, birthday = %s, employee_nic = %s, gender = %s, 
                marital_status = %s, number_of_dependents = %s, address = %s, 
                contact_number = %s, business_email = %s, job_title = %s, 
                department_id = %s, branch_id = %s
            WHERE employee_id = %s
        """

        cursor.execute(update_query, (
            employee_update.first_name, employee_update.last_name, employee_update.birthday,
            employee_update.employee_nic, employee_update.gender, employee_update.marital_status,
            employee_update.number_of_dependents, employee_update.address, employee_update.contact_number,
            employee_update.business_email, employee_update.job_title, employee_update.department_id,
            employee_update.branch_id, employee_id
        ))

        connection.commit()

        # Fetch the updated employee details
        cursor.callproc("get_employee_details", [employee_id])
        updated_employee = next(cursor.stored_results()).fetchone()

        if not updated_employee:
            raise HTTPException(status_code=404, detail="Failed to retrieve updated employee information")

        logger.info(f"Employee {employee_id} updated successfully")

        return updated_employee

    except mysql.connector.Error as e:
        logger.error(f"Database error while updating employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")



@router.get("/employee_of_month")
async def get_employee_of_the_month(db=Depends(get_db),
        current_user=Depends(get_current_active_user)):
    cursor, connection  = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        # Fetch the employee_id of the employee to be deleted
        cursor.callproc("employee_of_the_month")
        employee_of_month = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        if not employee_of_month:
            raise HTTPException(status_code=404, detail="Employee not found")


        connection.commit()

        logger.info(f"Employee of the month-->")

        return {"message": f"Employee of the month is {user_record}"}

    except mysql.connector.Error as e:
        logger.error(f"Database error while deleting employee: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")





