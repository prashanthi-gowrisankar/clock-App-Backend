from sqlalchemy import Column, Integer, String, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from my_backend.database import Base
from datetime import datetime

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="leave_requests")
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20))
    username = Column(String(100), unique=True, nullable=True)
    password = Column(String(100), nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    assigned_time = Column(DateTime, nullable=True)
    leave_requests = relationship("LeaveRequest", back_populates="user")
