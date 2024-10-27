from fastapi import FastAPI

from API import employee, users,Leavings,supervisor,listings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Ensure POST is allowed
    allow_headers=["*"],
)
app.include_router(employee.router)
app.include_router(users.router)
app.include_router(Leavings.router)
app.include_router(supervisor.router)
app.include_router(listings.router)

#
@app.get("/")
def welcome():
    return "Welcome to Jupiter HRMS! Still Testing ! Test -1000 "
