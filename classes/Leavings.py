from datetime import date
from typing import Optional

from pydantic import BaseModel


class LeaveRequestBase(BaseModel):
    employee_id: str
    leave_start_date: date
    period_of_absence: str
    reason_for_absence: str
    type_of_leave: str

class LeaveRequestCreate(LeaveRequestBase):
    pass


class LeaveRequestUpdate(BaseModel):
    Period_of_Absence: Optional[int]
    Reason_for_Absence: Optional[str]
    Type_of_Leave: Optional[str]
    Request_Status: Optional[str]


class LeaveRequestResponse(BaseModel):
    first_name:str
    last_name:str
    gender:str
    leave_request_id: int
    employee_id: str
    request_date: date
    leave_start_date: date
    period_of_absence: int
    reason_for_absence: str
    type_of_leave: str
    request_status: str

    class Config:
        orm_mode = True
