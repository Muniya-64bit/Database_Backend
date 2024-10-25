import os
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Annotated

import jwt
import mysql.connector
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600000

# Database connection function
def get_db():
    connection = mysql.connector.connect(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME'))
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    password: str
    employee_id: str
    login_date: date
    disabled: Optional[bool] = None
    class Config:
        orm_mode = True

class UserInDB(BaseModel):
    username: str
    password: str
    employee_id: str
    last_login_date: date
    disabled: Optional[bool] = None

    class Config:
        orm_mode = True  # Add hashed_password field to store the hashed password in DB

# Password hashing and verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# User authentication and database query
def get_user(cursor, username: str):
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user_record = cursor.fetchone()
    if user_record:
        return UserInDB(**user_record)
    return None

def authenticate_user(cursor, username: str, password: str):
    user = get_user(cursor, username)
    if not user or not verify_password(password, user['password']):
        return False
    return user

# Token creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=100000))
    to_encode.update({"exp": expire})

    if "sub" not in to_encode:
        raise ValueError("The 'sub' claim must be set in the token")

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get the current user
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db=Depends(get_db)):
    cursor, connection = db
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}, )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user(cursor, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# Verify that the user is active
async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Endpoint to log in and get the access token
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db=Depends(get_db)):
    cursor, connection = db
    user = authenticate_user(cursor, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}, )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user['username']}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint to get current user details
@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

# Endpoint to read items owned by the current user
@app.get("/users/me/items/")
async def read_own_items(current_user: Annotated[User, Depends(get_current_active_user)]):
    return [{"item_id": "Foo", "owner": current_user.username}]
