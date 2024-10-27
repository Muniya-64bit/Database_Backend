# main.py

import logging
from typing import List, Dict
import mysql.connector
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from db.db import get_db
from core.security import get_current_active_user

app = FastAPI()
router = APIRouter()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeaveRequestResponse(BaseModel):
    leave_request_id: int
    employee_id: int
    first_name: str
    last_name: str
    gender: str
    request_date: str
    leave_start_date: str
    period_of_absence: int
    reason_for_absence: str
    type_of_leave: str
    request_status: str


class LeaveStatus(BaseModel):
    leave_request_id: int
    status_: str


@app.get("/supervisors-with-teams", response_model=List[List[Dict[str, str]]])
async def supervisors_with_teams(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    logger.info(f"User {current_user.username} is attempting to fetch all supervisors with teams")

    cursor, connection = db
    try:
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()
        logger.info(f"Checking admin status for user {current_user.username}: {is_admin}")

        if not is_admin or not is_admin["is_admin"]:
            logger.warning(f"User {current_user.username} is not authorized to view this information")
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

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

        for supervisor_row in supervisors:
            supervisor_id = supervisor_row['employee_id']
            supervisor_name = f"{supervisor_row['first_name']} {supervisor_row['last_name']}"
            cursor.execute("""
            SELECT employee.employee_id, employee.first_name, employee.last_name, employee.gender
            FROM employee
            JOIN supervisor ON supervisor.employee_id = employee.employee_id
            WHERE supervisor.supervisor_id = %s
            """, (supervisor_id,))
            team_members = cursor.fetchall()

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


@app.put("/leavings/status")
async def leave_status_update(status: LeaveStatus, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        if not is_admin or not is_admin['is_admin']:
            raise HTTPException(status_code=403, detail="Not authorized to update leave status.")

        if not status.leave_request_id or not status.status_:
            raise HTTPException(status_code=400, detail="Missing leave_request_id or status.")

        cursor.callproc('evaluate_leave_request', [status.leave_request_id, status.status_])
        connection.commit()

        return {"message": "Leave request status updated successfully."}

    except mysql.connector.Error as e:
        logger.error(f"Database error while setting leave status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


app.include_router(router)
