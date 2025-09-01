from datetime import datetime, date
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import models
import database
from typing import List


app = FastAPI()
notifications = []

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables (only runs if they don't exist)
models.Base.metadata.create_all(bind=database.engine)

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Pydantic Schemas ---------------- #

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class UserLoginRequest(BaseModel):
    phone: str

class UserSignupRequest(BaseModel):
    username: str
    phone: str

class AssignTimeRequest(BaseModel):
    user_id: int
    time: str   # e.g. "14:30"

class LeaveRequestCreate(BaseModel):
    user_id: int
    username: str
    message: str

class NotificationRequest(BaseModel):
    user_id: int
    username: str
    message: str    

class LeaveRequestResponse(BaseModel):
    id: int
    user_id: int
    username: str
    message: str
    status: str
    created_at: datetime    


# ---------------- Routes ---------------- #

# ---------------- Leave Routes ----------------

# ✅ Submit leave request (user → admin)
@app.post("/notify-admin", response_model=LeaveRequestResponse)
def notify_admin(request: NotificationRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    leave_request = models.LeaveRequest(
        user_id=request.user_id,
        username=request.username,
        message=request.message,
        status="pending"
    )
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)

    return leave_request


# ✅ Get all pending leave requests (for admin dashboard)
@app.get("/leave-requests/pending", response_model=List[LeaveRequestResponse])
def get_pending_leave_requests(db: Session = Depends(get_db)):
    pending_requests = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == "pending"
    ).all()
    return pending_requests


# ✅ Approve leave
@app.post("/leave-requests/{leave_id}/approve")
def approve_leave(leave_id: int, db: Session = Depends(get_db)):
    leave_request = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave_request.status = "approved"
    db.commit()
    return {"message": f"Leave approved for {leave_request.username}"}


# ✅ Reject leave
@app.post("/leave-requests/{leave_id}/reject")
def reject_leave(leave_id: int, db: Session = Depends(get_db)):
    leave_request = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave_request.status = "rejected"
    db.commit()
    return {"message": f"Leave rejected for {leave_request.username}"}


# ✅ Admin login
@app.post("/login/admin")
def login_admin(request: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.username == request.username,
        models.User.password == request.password,
        models.User.role == "admin"
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    return {
        "message": "Admin login successful",
        "role": user.role,
        "username": user.username,
        "userId": user.id
    }


# ✅ User login
@app.post("/login/user")
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.phone == request.phone,
        models.User.role == "user"
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid user credentials")

    return {
        "message": "User login successful",
        "role": user.role,
        "username": user.username,
        "userId": user.id,
        "assigned_time": user.assigned_time
    }


# ✅ User Signup
@app.post("/signup/user")
def signup_user(request: UserSignupRequest, db: Session = Depends(get_db)):
    # check duplicate phone
    existing_user = db.query(models.User).filter(models.User.phone == request.phone).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone already registered")

    new_user = models.User(
        username=request.username,
        phone=request.phone,
        role="user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "userId": new_user.id,
        "username": new_user.username,
        "phone": new_user.phone,
        "role": new_user.role
    }


# ✅ Get all users (only users, not admins)
@app.get("/users") 
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).filter(models.User.role == "user").all()
    return users


# ✅ Get assigned time for a specific user
@app.get("/users/{user_id}/assigned_time")
def get_assigned_time(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"assigned_time": user.assigned_time}


# ✅ Assign time to a user
@app.post("/assign-time")
def assign_time(request: AssignTimeRequest, db: Session = Depends(get_db)):
    # Parse "HH:MM" into today's datetime
    try:
        time_obj = datetime.strptime(request.time, "%H:%M").time()
        full_datetime = datetime.combine(date.today(), time_obj)
    except ValueError:
        raise HTTPException(status_code=400, detail="Time must be in HH:MM format")

    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.assigned_time = full_datetime
    db.commit()
    db.refresh(user)

    return {"message": f"Assigned time {full_datetime} to user {user.username}"}

@app.get("/leave-requests/status/{user_id}", response_model=LeaveRequestResponse)
def get_latest_leave_request_by_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    latest_leave_request = (
        db.query(models.LeaveRequest)
        .filter(models.LeaveRequest.user_id == user_id)
        .order_by(models.LeaveRequest.created_at.desc())  # ✅ use created_at
        .first()
    )

    if not latest_leave_request:
        raise HTTPException(status_code=404, detail="No leave requests found")

    return latest_leave_request
