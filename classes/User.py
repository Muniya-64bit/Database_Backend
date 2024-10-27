from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str
    employee_id: str
    access_level :str
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    username: str
    token: str
    role:str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    username: str
    employee_id: str
    access_level: str



    class Config:
        from_attributes = True
class UpdatePassword(BaseModel):
    password: str
    class Config:
        from_attributes = True