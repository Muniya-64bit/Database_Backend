from typing import List, Dict
from pydantic import BaseModel


class supervisor_(BaseModel):
    supervisor_id: str
    first_name: str
    last_name: str

    class Config:
        orm_mode = True


class TeamMember(BaseModel):
    employee_id: str
    first_name: str
    last_name:str
    class Config:
        orm_mode = True

#
class SupervisorWithTeam(BaseModel):
    supervisor: Dict[str, str]  # To hold supervisor details (employee_id and name)
    team: List[TeamMember]  # A list of team members

    class Config:
        orm_mode = True


class Leave_Status(BaseModel):
    leave_request_id: int
    status_: str

    class Config:
        orm_mode = True
