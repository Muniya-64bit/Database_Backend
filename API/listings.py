import logging
import os

import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from mysql.connector import pooling
import uuid
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
#
async def get_db():
    connection = mysql.connector.connect(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME'))
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()


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



