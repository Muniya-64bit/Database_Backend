from fastapi import FastAPI

from API import employee, users, Leavings, supervisor

app = FastAPI()
app.include_router(employee.router)
app.include_router(users.router)
app.include_router(Leavings.router)
app.include_router(supervisor.router)


@app.get("/")
def welcome():
    return "Welcome to Jupiter HRMS! Still Testing ! Test -1000 "
