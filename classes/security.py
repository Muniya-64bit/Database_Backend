from datetime import date
from typing import Optional

from pydantic import BaseModel


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
