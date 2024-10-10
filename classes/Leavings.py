from datetime import date
from typing import Optional

from pydantic import BaseModel


class LeaveRequestBase(BaseModel):
    Leave_Request_ID: int
    Employee_ID: str
    Supervisor_ID: str
    Request_Date: str
    Leave_Start_Date: str
    Period_of_Absence: int
    Reason_for_Absence: str
    Type_of_Leave: str
    Request_Status: str


class LeaveRequestCreate(LeaveRequestBase):
    pass


class LeaveRequestUpdate(BaseModel):
    Period_of_Absence: Optional[int]
    Reason_for_Absence: Optional[str]
    Type_of_Leave: Optional[str]
    Request_Status: Optional[str]


class LeaveRequestResponse(BaseModel):
    leave_request_id: int
    employee_id: str
    supervisor_id: str
    request_date: date
    leave_start_date: date
    period_of_absence: int
    reason_for_absence: str
    type_of_leave: str
    request_status: str

    class Config:
        orm_mode = True
