import logging
import os
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status,Body
from pantic import BaseModel

from classes.User import User, UserLogin, LoginResponse,UpdatePassword
from core.security import pwd_context, verify_password, create_access_token, get_current_active_user

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Database connection dependency
load_dotenv()


def get_db():
    connection = mysql.connector.connect(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME'))
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()


# Pydantic model for access update


# # Endpoint to register a new user
@router.post("/user/reg", status_code=status.HTTP_201_CREATED)
async def create_user(user: User, db=Depends(get_db)):
    cursor, connection = db
    try:
        # Hash the password
        hashed_password = pwd_context.hash(user.password)

        # Call stored procedure to create user account based on access level
        cursor.callproc("create_user_account", [user.username, hashed_password, user.employee_id, user.access_level])
        connection.commit()

        # Fetch the newly created user record to confirm
        cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
        new_user = cursor.fetchone()

        if not new_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after insertion")

        logger.info(f"User {user.username} registered successfully.")
        return {"message": "User registered successfully", "user": new_user}

    except mysql.connector.Error as e:
        connection.rollback()  # Rollback transaction on error
        logger.error(f"Database error during user registration: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error during user registration: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


# Endpoint to log in a user and generate an access token
@router.post("/login", response_model=LoginResponse)
async def login_user(user: UserLogin, db=Depends(get_db)):
    cursor, connection = db

    # Fetch the user record by username
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    db_user = cursor.fetchone()

    # Check if the user exists and verify the password
    if not db_user or not verify_password(user.password, db_user['password']):
        logger.warning(f"Login failed for username {user.username}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid credentials")

    # Create access token
    access_token = create_access_token(data={"sub": db_user['username']})
    logger.info(f"User {user.username} logged in successfully.")

    # Return response with username and token
    return LoginResponse(username=db_user['username'], token=access_token)


@router.put("/user/{username}", status_code=status.HTTP_200_OK)
async def update_user_access(
        username: str,
        password_: UpdatePassword = Body(...),  # Use Body to specify the request body
        db=Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    cursor, connection = db
    try:
        # Get the target user's current access information
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        target_user = cursor.fetchone()

        # Check if current user is admin
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin_record = cursor.fetchone()
        is_admin = is_admin_record["is_admin"] if is_admin_record else False

        if not is_admin:
            raise HTTPException(status_code=403, detail="User is not an admin.")

        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update the user's password (ensure you hash the password in a real application)
        cursor.execute(
            "UPDATE users SET password = %s WHERE username = %s",
            (password_.password, target_user['username'])  # Assuming 'user_id' is the correct key
        )
        connection.commit()

        logger.info(f"Access updated for user {username}")
        return {"message": "User access updated successfully"}
###
    except mysql.connector.Error as e:
        connection.rollback()
        logger.error(f"Database error updating access for user {username}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")

