import logging
from typing import List,Dict
import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, status
from classes.supervisor import SupervisorWithTeam, Leave_Status, TeamMember
from core.security import get_current_active_user
from classes.Leavings import LeaveRequestResponse
from db.db import get_db

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter()
@router.get("/supervisors-with-teams", response_model=List[List[Dict[str, str]]])
async def supervisors_with_teams(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    logger.info(f"User {current_user.username} is attempting to fetch all supervisors with teams")

    cursor, connection = db
    try:
        # Check if the current user is an admin
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        logger.info(f"Checking admin status for user {current_user.username}: {is_admin}")

        if not is_admin:  # Access the first column of the result tuple
            logger.warning(f"User {current_user.username} is not authorized to view this information")
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

        # Fetch all supervisors
        logger.info("Fetching all supervisors from the database")
        cursor.execute("""
        SELECT supervisor.employee_id, employee.first_name, employee.last_name
        FROM supervisor
        JOIN employee ON employee.employee_id = supervisor.employee_id;
        """)
        supervisors = cursor.fetchall()

        if not supervisors:
            logger.info("No supervisors found")
            return []

        all_supervisors_with_teams = []

        # For each supervisor, fetch their team members
        for supervisor_row in supervisors:
            supervisor_id = supervisor_row['employee_id']
            supervisor_name = f"{supervisor_row['first_name']} {supervisor_row['last_name']}"

            logger.info(f"Fetching team members for supervisor {supervisor_name} (ID: {supervisor_id})")

            # Fetch team members for the supervisor
            cursor.execute("""
            SELECT  distinct supervisor.employee_id, employee.first_name, employee.last_name, employee.gender
            FROM supervisor
            JOIN employee ON supervisor.employee_id = employee.employee_id
            WHERE supervisor.supervisor_id = %s
            """, (supervisor_id,))
            team_members = cursor.fetchall()

            # Format the result as a 2D array
            supervisor_with_team = [
                {"employee_id": supervisor_id, "name": supervisor_name}
            ] + [
                {
                    "employee_id": member['employee_id'],
                    "first_name": member['first_name'],
                    "last_name": member['last_name'],
                    "gender": member['gender']
                }
                for member in team_members
            ]

            all_supervisors_with_teams.append(supervisor_with_team)

        logger.info(f"Successfully fetched teams for {len(supervisors)} supervisors")

        return all_supervisors_with_teams

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching supervisor details: {str(e)}")
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

        cursor.callproc('evaluate_leave_request', [status.leave_request_id,status.status_],)
        # supervisor_result = next(cursor.stored_results()).fetchone()
        #
        # if not supervisor_result:
        #     raise HTTPException(status_code=404, detail="Supervisor ID not found.")

        connection.commit()

        return {"message": "Leave request status updated successfully."}

    except mysql.connector.Error as e:
        logger.error(f"Database error while setting leave status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")



