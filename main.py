"""
MW Design Studio - Modern Client Intake System
FastAPI + Tailwind CSS + PostgreSQL
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime
from typing import List, Optional
import os
from pathlib import Path

# Import our models and database
from database import get_db, init_db
from models import Submission, User
from pdf_generator import generate_client_pdf

# Initialize FastAPI app
app = FastAPI(
    title="MW Design Studio - Client Intake System",
    description="Modern client intake system with branded PDF generation and admin dashboard",
    version="2.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main client intake form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit")
async def submit_intake_form(
    request: Request,
    db: Session = Depends(get_db),
    # Business Information
    business_name: str = Form(...),
    website: Optional[str] = Form(None),
    contact_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    
    # Business Details
    products_services: Optional[str] = Form(None),
    brand_story: Optional[str] = Form(None),
    usp: Optional[str] = Form(None),
    company_size: Optional[str] = Form(None),
    budget: Optional[str] = Form(None),
    
    # Social Media Goals
    goals: List[str] = Form([]),
    platforms: List[str] = Form([]),
    timeline: Optional[str] = Form(None),
    
    # Target Audience
    demographics: Optional[str] = Form(None),
    problems_solutions: Optional[str] = Form(None),
    
    # Brand & Content
    brand_voice: Optional[str] = Form(None),
    content_tone: Optional[str] = Form(None),
    brand_colors: Optional[str] = Form(None),
    brand_fonts: Optional[str] = Form(None),
    
    # Competition & Inspiration
    competitors: Optional[str] = Form(None),
    inspiration: Optional[str] = Form(None),
    
    # Additional Information
    additional_info: Optional[str] = Form(None)
):
    """Process form submission and generate PDF"""
    
    try:
        # Create new submission
        new_submission = Submission(
            business_name=business_name,
            website=website,
            contact_name=contact_name,
            email=email,
            phone=phone,
            products_services=products_services,
            brand_story=brand_story,
            usp=usp,
            company_size=company_size,
            budget=budget,
            goals=goals,
            platforms=platforms,
            timeline=timeline,
            demographics=demographics,
            problems_solutions=problems_solutions,
            brand_voice=brand_voice,
            content_tone=content_tone,
            brand_colors=brand_colors,
            brand_fonts=brand_fonts,
            competitors=competitors,
            inspiration=inspiration,
            additional_info=additional_info,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)
        
        # Generate and return PDF
        pdf_path = generate_client_pdf(new_submission)
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=f"{business_name}_client_intake.pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing submission: {str(e)}")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard with analytics"""
    
    # Get submission statistics
    total_submissions = db.query(Submission).count()
    recent_submissions = db.query(Submission).order_by(Submission.created_at.desc()).limit(10).all()
    
    # Calculate some basic analytics
    budget_distribution = db.query(Submission.budget).all()
    platform_stats = {}
    
    for submission in db.query(Submission).all():
        if submission.platforms:
            for platform in submission.platforms:
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_submissions": total_submissions,
        "recent_submissions": recent_submissions,
        "platform_stats": platform_stats,
        "budget_distribution": budget_distribution
    })

@app.get("/admin/submissions", response_class=HTMLResponse)
async def list_submissions(request: Request, db: Session = Depends(get_db)):
    """List all submissions with filtering"""
    
    submissions = db.query(Submission).order_by(Submission.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/submissions.html", {
        "request": request,
        "submissions": submissions
    })

@app.get("/admin/submission/{submission_id}", response_class=HTMLResponse)
async def view_submission(submission_id: int, request: Request, db: Session = Depends(get_db)):
    """View detailed submission"""
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return templates.TemplateResponse("admin/submission_detail.html", {
        "request": request,
        "submission": submission
    })

@app.get("/health")
async def health_check():
    """Health check for Render deployment"""
    return {"status": "healthy", "service": "MW Design Studio Client Intake v2.0"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
