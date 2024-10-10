
from pydantic import BaseModel
from typing import Optional
from datetime import date;
from datetime import time;
class User(BaseModel):
    username: str
    password: str
    employee_id: str
    last_login_date: Optional[date] = None
    last_login_time: Optional[time] = None



    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    username: str
    password: str
    employee_id: Optional[str] =None


    class Config:
        orm_mode = True

class LoginResponse(BaseModel):
    username:str
    token:str

    class Config:
        orm_mode = True
