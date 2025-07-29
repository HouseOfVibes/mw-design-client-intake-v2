"""
Modern SQLAlchemy models for MW Design Studio Client Intake System
Using SQLAlchemy 2.0 style for FastAPI
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

Base = declarative_base()

class Submission(Base):
    """Client intake submission model"""
    __tablename__ = "submissions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Business Information
    business_name = Column(String(255), nullable=False, index=True)
    website = Column(String(255))
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    
    # Business Details
    products_services = Column(Text)
    brand_story = Column(Text)
    usp = Column(Text)  # Unique Selling Proposition
    company_size = Column(String(100))
    budget = Column(String(100))
    
    # Social Media Goals & Strategy
    goals = Column(ARRAY(String))  # Array of selected goals
    platforms = Column(ARRAY(String))  # Array of social platforms
    timeline = Column(String(100))
    posting_frequency = Column(String(100))
    
    # Target Audience
    demographics = Column(Text)
    problems_solutions = Column(Text)
    
    # Brand & Content Strategy
    brand_voice = Column(String(100))
    content_tone = Column(String(100))
    brand_colors = Column(String(255))
    brand_fonts = Column(String(255))
    existing_content = Column(String(255))
    content_writing = Column(String(255))
    
    # Competition & Market Analysis
    competitors = Column(Text)
    inspiration = Column(Text)
    
    # Additional Information
    additional_info = Column(Text)
    
    # Admin & Workflow Fields
    status = Column(String(50), default="New")  # New, Contacted, Proposal Sent, Won, Lost
    priority = Column(String(20), default="Medium")  # Low, Medium, High, Urgent
    internal_notes = Column(Text)
    assigned_to = Column(String(255))  # Admin user assigned
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # PDF & Export tracking
    pdf_generated = Column(Boolean, default=False)
    pdf_path = Column(String(500))
    last_exported = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Submission(id={self.id}, business='{self.business_name}', status='{self.status}')>"

class User(Base):
    """Admin user model for dashboard access"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

# Pydantic models for API validation and serialization
class SubmissionBase(BaseModel):
    """Base submission model for API"""
    business_name: str
    website: Optional[str] = None
    contact_name: str
    email: EmailStr
    phone: Optional[str] = None
    products_services: Optional[str] = None
    brand_story: Optional[str] = None
    usp: Optional[str] = None
    company_size: Optional[str] = None
    budget: Optional[str] = None
    goals: Optional[List[str]] = []
    platforms: Optional[List[str]] = []
    timeline: Optional[str] = None
    demographics: Optional[str] = None
    problems_solutions: Optional[str] = None
    brand_voice: Optional[str] = None
    content_tone: Optional[str] = None
    brand_colors: Optional[str] = None
    brand_fonts: Optional[str] = None
    competitors: Optional[str] = None
    inspiration: Optional[str] = None
    additional_info: Optional[str] = None

class SubmissionCreate(SubmissionBase):
    """Model for creating submissions"""
    pass

class SubmissionUpdate(BaseModel):
    """Model for updating submission status/admin fields"""
    status: Optional[str] = None
    priority: Optional[str] = None
    internal_notes: Optional[str] = None
    assigned_to: Optional[str] = None

class SubmissionResponse(SubmissionBase):
    """Model for API responses"""
    id: int
    status: str
    priority: str
    created_at: datetime
    updated_at: Optional[datetime]
    pdf_generated: bool
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    """Model for creating users"""
    password: str

class UserResponse(UserBase):
    """Model for user API responses"""
    id: int
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

# Analytics models
class DashboardStats(BaseModel):
    """Dashboard analytics response model"""
    total_submissions: int
    new_submissions: int
    in_progress_submissions: int
    completed_submissions: int
    recent_submissions: List[SubmissionResponse]
    platform_stats: dict
    budget_distribution: dict
    monthly_growth: dict

class SubmissionFilters(BaseModel):
    """Filtering options for submissions list"""
    status: Optional[str] = None
    priority: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_query: Optional[str] = None
    assigned_to: Optional[str] = None
