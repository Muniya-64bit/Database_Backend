from pydantic import BaseModel
from typing import Optional, List,Dict

class supervisor_(BaseModel):
    employee_id:str
    name:str

    class Config:
        orm_mode = True

class TeamMember(BaseModel):
    employee_id: str
    name: str

    class Config:
        orm_mode = True


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
