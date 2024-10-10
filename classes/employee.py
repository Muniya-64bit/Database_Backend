import datetime as d
from typing import Optional

from pydantic import BaseModel


class EmployeeBase(BaseModel):
    employee_id: str
    name: str
    birthday: Optional[d.datetime] = None  # Will be formatted as a string
    NIC: str
    gender: str
    marital_status: str
    number_of_dependents: int
    address: str
    contact_number: str
    emergency_contact_id: int
    business_email: str
    position_id: str
    supervisor_id: Optional[str] = None
    department_id: str
    branch_id: str
    leaves_record_id: int

    class Config:
        orm_mode = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    class Config:
        orm_mode = True
