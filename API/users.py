from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from classes.User import User, UserLogin,LoginResponse
from pydantic import BaseModel
from core.security import pwd_context, verify_password, create_access_token, get_current_active_user
import mysql.connector
import os
from dotenv import load_dotenv
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Database connection dependency
load_dotenv()
def get_db():
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()

# Pydantic model for access update


# Endpoint to register a new user
@router.post("/user/reg", status_code=status.HTTP_201_CREATED)
async def create_user(user: User, db=Depends(get_db)):
    cursor, connection = db
    try:
        # Hash the password
        hashed_password = pwd_context.hash(user.password)
        # Insert the user data with optional nullable fields
        cursor.execute(
            "INSERT INTO users (username, password, Employee_ID,last_login_date,last_login_time) VALUES (%s, %s, %s,%s,%s)",
            (user.username, hashed_password, user.employee_id,user.last_login_date,user.last_login_time)
        )
        connection.commit()

        # Fetch the newly created user to confirm
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

    # Get current date and time for login
    login_date = datetime.now().date()  # Current date
    login_time = datetime.now().time()  # Current time

    # Update last login date and time in a single query
    cursor.execute("""
        UPDATE users
        SET last_login_date = %s, last_login_time = %s
        WHERE username = %s
    """, (login_date, login_time, user.username))
    connection.commit()

    logger.info(f"User {user.username} logged in successfully.")

    # Return response with username and token
    return LoginResponse(
        username=db_user['username'],
        token=access_token
    )


# Endpoint to update another user's access (admin or users with specific access only)
# @router.put("/user/{username}/update", status_code=status.HTTP_200_OK)
# async def update_user_access(
#         username: str,
#         db=Depends(get_db),
#         current_user=Depends(get_current_active_user)
# ):
#     cursor, connection = db
#     try:
#         # Get the target user's current access information
#         cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
#         target_user = cursor.fetchone()
#
#         cursor.excute("SELECT *is_admin FROM user_access where username = %s",(username,))
#         is_admin = cursor.fetchone()
#
#         if not is_admin:
#             raise HTTPException(status_code=404, detail  = "User is not a admin.")
#
#         if not target_user:
#             raise HTTPException(status_code=404, detail="User not found")
#
#         # Check if current user has the right to edit another user's access
#
#
#         # Update the access fields
#         cursor.execute(
#             "UPDATE Users SET Profile_Visibility_Access = %s, Profile_Editing_Access = %s, Other_Profile_Editing_Access = %s "
#             "WHERE User_ID = %s",
#             (
#                 access_update.profile_visibility_access,
#                 access_update.profile_editing_access,
#                 access_update.other_profile_editing_access,
#                 username
#             )
#         )
#         connection.commit()
#
#         logger.info(f"Access updated for user {username}")
#         return {"message": "User access updated successfully"}
#
#     except mysql.connector.Error as e:
#         connection.rollback()
#         logger.error(f"Database error updating access for user {username}: {str(e)}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

# Endpoint to view a user's profile based on access control
@router.get("/user/{username}/profile", status_code=status.HTTP_200_OK)
async def view_user_profile(
    username: str,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    cursor, _ = db
    cursor.execute("SELECT * FROM Users WHERE User_ID = %s", (username,))
    user_profile = cursor.fetchone()

    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")

    cursor.excute("SELECT *is_admin FROM user_access where username = %s", (username,))
    is_admin = cursor.fetchone()

    if not is_admin:
        raise HTTPException(status_code=404, detail="User is not a admin.")

    logger.info(f"User {current_user['username']} viewed profile of {username}")
    return {"user_profile": user_profile}

# Endpoint to edit a user's profile (requires editing access)
@router.put("/user/{username}/edit", status_code=status.HTTP_200_OK)
async def edit_user_profile(
    username: str,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    cursor, connection = db
    cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
    target_user = cursor.fetchone()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    cursor.excute("SELECT * FROM user_access where username = %s", (username,))
    user_access = cursor.fetchone()

    if not user_access['is_admin']:
        raise HTTPException(status_code=404, detail="User is not a admin.")

    try:
        # Perform the profile update
        cursor.execute(
            "UPDATE Users SET is_admin = %s, is_supervisor = %s "
            "WHERE username = %s",
            (
                user_access['is_admin'],
                user_access['is_supervisor'],
                username
            )
        )
        connection.commit()

        logger.info(f"User profile updated for {username}")
        return {"message": "Profile updated successfully"}

    except mysql.connector.Error as e:
        connection.rollback()
        logger.error(f"Error updating profile for user {username}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating profile: {str(e)}")
