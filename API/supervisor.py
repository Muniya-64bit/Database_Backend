import logging
import os
from typing import List

import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import pooling

from classes import supervisor
from classes.supervisor import SupervisorWithTeam, Leave_Status
from classes.supervisor import supervisor_
from core.security import get_current_active_user

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Query for counting absent employees
router = APIRouter()

# Database connection pool
load_dotenv()
dbconfig = {"host": os.getenv('DB_HOST'), "user": os.getenv('DB_USER'), "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME'), }
db_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)


# Database connection dependency
def get_db():
    connection = db_pool.get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()


@router.get("/supervisors", response_model=List[supervisor.supervisor_])
async def all_spervisors(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:

        # Check admin status using a stored procedure
        cursor.execute("SELECT is_admin from user_access where username = %s", (current_user.username,))
        is_admin = cursor.fetchone()
        # Check visibility access
        if not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view this  information")

        cursor.execute("""
        select employee.employee_id,employee.name
        from employee
        join employee as e
        where e.supervisor_id = employee.employee_id
        """)
        supervisors = cursor.fetchall()

        all_supervisor_response = [supervisor_(employee_id=row['employee_id'], name=row['name']

        ) for row in supervisors]

        return all_supervisor_response

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching supervisors: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get("/supervisors-with-teams", response_model=List[SupervisorWithTeam])
async def supervisors_with_teams(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check admin status using a stored procedure
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        # Check visibility access
        if not is_admin or not is_admin['is_admin']:
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

        # Fetch all supervisors
        cursor.execute("""
        SELECT employee.employee_id, employee.name 
        FROM employee 
        WHERE employee.employee_id IN (
            SELECT DISTINCT supervisor_id FROM employee WHERE supervisor_id IS NOT NULL
        )
        """)
        supervisors = cursor.fetchall()

        all_supervisors_with_teams = []

        # For each supervisor, fetch their team members
        for supervisor_row in supervisors:
            supervisor_id = supervisor_row['employee_id']
            supervisor_name = supervisor_row['name']

            # Fetch team members for the supervisor
            cursor.execute("""
            SELECT DISTINCT employee_id, name 
            FROM employee 
            WHERE supervisor_id = %s

            """, (supervisor_id,))
            team_members = cursor.fetchall()

            # Construct the response
            supervisor_with_team = {"supervisor": {"employee_id": supervisor_id, "name": supervisor_name},
                "team": [{"employee_id": member['employee_id'], "name": member['name']} for member in team_members]}

            all_supervisors_with_teams.append(supervisor_with_team)

        return all_supervisors_with_teams

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching employee details: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.put("/leavings/status")
async def leave_status(status: Leave_Status, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check admin status using a stored procedure
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        # Check visibility access (whether the user is an admin)
        if not is_admin or not is_admin['is_admin']:
            raise HTTPException(status_code=403, detail="Not authorized to update leave status.")

        # Ensure status fields are provided
        if not status.leave_request_id or not status.status_:
            raise HTTPException(status_code=400, detail="Missing leave_request_id or status.")

        # Update leave request status
        cursor.execute("""
                        UPDATE leave_request
                        SET request_status = %s
                        WHERE leave_request_id = %s
        """, (status.status_, status.leave_request_id))

        connection.commit()

        return {"message": "Leave request status updated successfully."}

    except mysql.connector.Error as e:
        logger.error(f"Database error while setting leave status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")
