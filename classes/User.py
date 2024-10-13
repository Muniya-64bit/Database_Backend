from datetime import date;
from datetime import time;
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    username: str
    password: str
    employee_id: str
    access_level :str
    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    username: str
    password: str

    class Config:
        orm_mode = True


class LoginResponse(BaseModel):
    username: str
    token: str

    class Config:
        orm_mode = True


class UserResponse(BaseModel):
    username: str
    employee_id: str
    access_level: str



    class Config:
        orm_mode = True
class UpdatePassword(BaseModel):
    password: str
    class Config:
        orm_mode = True