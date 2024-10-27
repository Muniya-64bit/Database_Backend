import logging
from typing import List

import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, status

from classes import supervisor
from classes.Leavings import LeaveRequestResponse
from classes.employee import Pie_graph_gender, Pie_graph_pay_grade, Pie_graph_role
from classes.supervisor import supervisor_, TeamMember
from core.middleware import logger
from core.security import get_current_active_user
from db.db import get_db


router = APIRouter()


@router.get("/all_admins")
async def admin_list(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, _ = db

    try:
        # Check if the current user is an admin (can be done before fetching admins)
        cursor.callproc("is_admin", [current_user.username])
        admin_record = next(cursor.stored_results()).fetchone()
        is_admin = admin_record["is_admin"] if admin_record else False

        if not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view admin list")

        # Fetch all admin details using the 'admins' stored procedure
        cursor.callproc("admins")
        admin_records = next(cursor.stored_results()).fetchall()

        if not admin_records:
            raise HTTPException(status_code=404, detail="No admins found")

        # Map the SQL result to a response list of dictionaries
        admin_list = [
            {
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "employee_id": record["employee_id"]
            }
            for record in admin_records
        ]

        return admin_list

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching admin details: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

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
#
    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching leaves: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

@router.get("/on_leave")
async def get_on_leave(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        # Fetch the employee_id of the employee to be deleted
        cursor.callproc("get_leave_count")
        on_leave = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        if not on_leave:
            raise HTTPException(status_code=404, detail="Employee not found")

        connection.commit()

        logger.info(f"number of employee on leave->")

        return {"message": on_leave}

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching  data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")


@router.get("/today_full_time")
def get_on_fulltime(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        # Fetch the employee_id of the employee to be deleted
        cursor.callproc("get_fulltime_employee_count_presentage")
        full_time = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        if not full_time:
            raise HTTPException(status_code=404, detail="Employee not found")

        connection.commit()

        logger.info(f"number of employee full time-->")

        return {"message": full_time}

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching  data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")


@router.get("/today_half_time")
def get_on_halftome(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        # Fetch the employee_id of the employee to be deleted
        cursor.callproc("get_parttime_employee_count_presentage")
        part_time = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        if not part_time:
            raise HTTPException(status_code=404, detail="Employee not found")

        connection.commit()

        logger.info(f"number of employee part time-->")

        return {"message": part_time}

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching  data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")



@router.get("/pie_graph_gender", response_model=List[Pie_graph_gender])
def graph_by_gender(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch the gender percentages for employees
        cursor.callproc("employees_by_gender_presentages")
        results = next(cursor.stored_results()).fetchall()  # Assuming multiple rows are returned

        if not results:
            raise HTTPException(status_code=404, detail="No gender data found")

        # Convert the results into a list of Pie_graph_gender instances
        pie_chart_data = [Pie_graph_gender(gender=row["gender"], presentage_by_gender=row["presentage_by_gender"])
                          for row in results]

        logger.info("Fetched pie chart data by gender successfully")

        return pie_chart_data

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching graph data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")




@router.get("/pie_graph_paygrade", response_model=List[Pie_graph_pay_grade])
def graph_by_paygrade(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch the pay grade percentages for employees
        cursor.callproc("employees_by_pay_grade_presentages")
        paygrade_results = next(cursor.stored_results()).fetchall()  # Assuming multiple rows are returned

        if not paygrade_results:
            raise HTTPException(status_code=404, detail="No pay grade data found")

        # Convert the results into a list of PieGraphPayGrade instances
        pie_chart_data = [
            Pie_graph_pay_grade(pay_grade=row["pay_grade"], presentage_by_pay_grade=row["presentage_by_pay_grade"])
            for row in paygrade_results
        ]

        logger.info("Fetched pie chart data by pay grade successfully")

        return pie_chart_data

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching graph data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")


@router.get("/pie_graph_role", response_model=List[Pie_graph_role])
def graph_by_role(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Fetch the employee_id of the current user
        cursor.callproc("get_employee_id_by_username", [current_user.username])
        user_record = next(cursor.stored_results()).fetchone()

        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch the role percentages for employees
        cursor.callproc("employees_by_role_presentages")
        role_results = next(cursor.stored_results()).fetchall()  # Assuming multiple rows are returned

        if not role_results:
            raise HTTPException(status_code=404, detail="No role data found")

        # Convert the results into a list of PieGraphRole instances
        pie_chart_data = [
            Pie_graph_role(role=row["job_title"], presentage_by_role=row["presentage_by_role"])
            for row in role_results
        ]

        logger.info("Fetched pie chart data by role successfully")

        return pie_chart_data

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching graph data: {str(e)}")
        connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")
