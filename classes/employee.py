import datetime as d
from typing import Optional

from pydantic import BaseModel


class EmployeeBase(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    birthday: Optional[d.datetime] = None  # Will be formatted as a string
    nic: str
    gender: str
    marital_status: str
    number_of_dependents: int
    address: str
    contact_number: str
    business_email: str
    job_title: str
    employee_status: str
    department_name: str
    branch_name: str
    profile_photo: Optional[str] = None

    # Emergency contact details


    class Config:
        orm_mode = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    birthday: Optional[d.datetime] = None  # Will be formatted as a string
    employee_nic: str
    gender: str
    marital_status: str
    number_of_dependents: int
    address: str
    contact_number: str
    business_email: str
    job_title: str
    department_id: int
    branch_id: int
    profile_photo: Optional[str] = None

    class Config:
        orm_mode = True
