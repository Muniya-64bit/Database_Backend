import logging
import os
from typing import List

import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from mysql.connector import pooling

from classes import supervisor
from classes.supervisor import SupervisorWithTeam, Leave_Status, TeamMember
from classes.supervisor import supervisor_
from core.security import get_current_active_user
from classes.Leavings import LeaveRequestResponse
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
async def all_supervisors(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check admin status
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        # Log admin status to verify the fetch
        logger.info(f"Admin status for user {current_user.username}: {is_admin}")

        # Ensure the user has admin rights
        if not is_admin :
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

        # Call the stored procedure `show_supervisor`
        logger.info("Calling stored procedure 'show_supervisor'")
        cursor.callproc('show_supervisor')

        # Fetch the results from the procedure
        result_cursor = next(cursor.stored_results(), None)

        if result_cursor is None:
            logger.error("No result set returned from stored procedure 'show_supervisor'")
            raise HTTPException(status_code=500, detail="No results returned from the stored procedure")

        supervisors = result_cursor.fetchall()

        # Log fetched supervisors for debugging
        logger.info(f"Supervisors fetched: {supervisors}")

        # Build the response
        all_supervisor_response = [
            supervisor_(
                supervisor_id=row['supervisor_id'],
                first_name=row['first_name'],
                last_name = row['last_name']
            ) for row in supervisors
        ]

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
        cursor.execute("SELECT is_supervisor FROM user_access WHERE username = %s", (current_user.username,))
        is_supervisor = cursor.fetchone()
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        supervisor_id = next(cursor.stored_results()).fetchone()
        # Check visibility access
        if not is_supervisor :
            raise HTTPException(status_code=403, detail="Not authorized to view this information")
        # Fetch all supervisors
        cursor.execute("""
        SELECT supervisor.employee_id, employee.first_name,employee.last_name
        FROM supervisor 
        join employee
        on employee.employee_id  = supervisor.employee_id
        where supervisor_id  = %s ;""",(supervisor_id,))
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

@router.get("/supervisor/team/",response_model=List[TeamMember])
async def supervisor_team(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check admin status
        cursor.execute("SELECT is_supervisor FROM user_access WHERE username = %s", (current_user.username,))
        is_supervisor = cursor.fetchone()

        # Log admin status to verify the fetch
        logger.info(f"Admin status for user {current_user.username}: {is_supervisor}")

        # Ensure the user has admin rights
        if not is_supervisor:
            raise HTTPException(status_code=403, detail="Not authorized to view this information")
        logger.info("Calling stored procedure 'get_employee_id_by_username'")
        cursor.callproc('get_employee_id_by_username', [current_user.username, ])

        # Fetch the results from the procedure
        stored_result = next(cursor.stored_results(), None)

        if not stored_result:
            logger.error("No result set returned from the stored procedure 'get_employee_id_by_username'")
            raise HTTPException(status_code=500, detail="No results returned from the stored procedure")

        supervisor_id = stored_result.fetchone()['employee_id']  # Extract supervisor_id from the result
        # Call the stored procedure `show_supervisor`
        logger.info("Calling stored procedure 'show_all_employee_team'")
        cursor.callproc('employee_team',[supervisor_id,])

        # Fetch the results from the procedure
        result_cursor = next(cursor.stored_results(), None)

        if result_cursor is None:
            logger.error("No result set returned from stored procedure 'show_employee_team'")
            raise HTTPException(status_code=500, detail="No results returned from the stored procedure")

        employee_team = result_cursor.fetchall()

        # Log fetched supervisors for debugging
        logger.info(f"employees fetched: {employee_team}")

        # Build the response
        all_supervisor_response = [
            TeamMember(
                employee_id=row['employee_id'],
                first_name=row['first_name'],
                last_name=row['last_name']
            ) for row in employee_team
        ]

        return all_supervisor_response

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching supervisors: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get("/team_leaves", response_model=List[LeaveRequestResponse])
async def all_leaves(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check if the current user is a supervisor
        cursor.execute("SELECT is_supervisor FROM user_access WHERE username = %s", (current_user.username,))
        is_supervisor = cursor.fetchone()

        # Log admin status to verify the fetch
        logger.info(f"Supervisor status for user {current_user.username}: {is_supervisor}")

        # Ensure the user has supervisor rights
        if not is_supervisor :
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

        # Call the stored procedure to get the supervisor's employee ID
        logger.info("Calling stored procedure 'get_employee_id_by_username'")
        cursor.callproc('get_employee_id_by_username', [current_user.username,])

        # Fetch the results from the procedure
        stored_result = next(cursor.stored_results(), None)

        if not stored_result:
            logger.error("No result set returned from the stored procedure 'get_employee_id_by_username'")
            raise HTTPException(status_code=500, detail="No results returned from the stored procedure")

        supervisor_id = stored_result.fetchone()['employee_id']  # Extract supervisor_id from the result

        # Log fetched supervisor ID for debugging
        logger.info(f"Supervisor ID fetched: {supervisor_id}")

        # Query to get leave requests for employees under the supervisor
        cursor.execute("""
            SELECT * FROM leave_request
            WHERE employee_id IN (SELECT employee_id FROM supervisor WHERE supervisor.supervisor_id = %s);
        """, (supervisor_id,))

        team_leaves = cursor.fetchall()

        # Build the response
        all_leaves_requests = [
            LeaveRequestResponse(
                leave_request_id=row['leave_request_id'],
                employee_id=row['employee_id'],
                request_date=row['request_date'],
                leave_start_date=row['leave_start_date'],
                period_of_absence=row['period_of_absence'],
                reason_for_absence=row['reason_for_absence'],
                type_of_leave=row['type_of_leave'],
                request_status=row['request_status']
            ) for row in team_leaves
        ]

        return all_leaves_requests

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching leaves: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

