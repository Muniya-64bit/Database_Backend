import datetime as d
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


#
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
    emergency_contact_name: str
    emergency_contact_nic: str
    emergency_contact_address: str
    emergency_contact_number: str

    # Emergency contact details

    class Config:
        from_attributes = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    employee_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birthday: Optional[d.datetime] = None
    employee_nic: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    number_of_dependents: Optional[int] = None
    address: Optional[str] = None
    contact_number: Optional[str] = None
    business_email: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[int] = None
    branch_id: Optional[int] = None

    class Config:
        from_attributes = True


class Pie_graph_gender(BaseModel):
    gender: str
    presentage_by_gender: float

    class Config:
        from_attributes = True


class Pie_graph_role(BaseModel):
    role: str
    presentage_by_role: float

    class Config:
        from_attributes = True


class Pie_graph_pay_grade(BaseModel):
    pay_grade: int
    presentage_by_pay_grade: float

    class Config:
        from_attributes = True


class Pie_graph_pay_department(BaseModel):
    department_name: str
    presentage_by_department: Decimal

    class Config:
        from_attributes = True