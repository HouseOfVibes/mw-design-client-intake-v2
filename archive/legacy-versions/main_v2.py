"""
MW Design Studio - Enhanced Admin System
FastAPI + Tailwind CSS + PostgreSQL with Advanced Analytics
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc, or_
import uvicorn
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import json
import calendar
import io
import csv

# Import our models and database
from database_v2 import get_db, init_db
from models_v2 import Submission, User, SubmissionUpdate

# Initialize FastAPI app
app = FastAPI(
    title="MW Design Studio - Enhanced Client Intake System",
    description="Modern client intake system with advanced analytics, branded PDF generation, and comprehensive admin dashboard",
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

# Main Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main client intake form"""
    return templates.TemplateResponse("complete_form.html", {"request": request})

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
    posting_frequency: Optional[str] = Form(None),
    
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
            posting_frequency=posting_frequency,
            demographics=demographics,
            problems_solutions=problems_solutions,
            brand_voice=brand_voice,
            content_tone=content_tone,
            brand_colors=brand_colors,
            brand_fonts=brand_fonts,
            competitors=competitors,
            inspiration=inspiration,
            additional_info=additional_info,
            status="New",
            priority="Medium",
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)
        
        # Return success response
        return JSONResponse({
            "success": True,
            "message": "Submission received successfully!",
            "submission_id": new_submission.id
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing submission: {str(e)}")

# Enhanced Admin Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Enhanced admin dashboard with comprehensive analytics"""
    
    # Get submission statistics
    total_submissions = db.query(Submission).count()
    new_submissions = db.query(Submission).filter(Submission.status == "New").count()
    in_progress_submissions = db.query(Submission).filter(
        Submission.status.in_(["Contacted", "Proposal Sent"])
    ).count()
    won_submissions = db.query(Submission).filter(Submission.status == "Won").count()
    
    # Calculate conversion rate
    conversion_rate = round((won_submissions / total_submissions * 100) if total_submissions > 0 else 0, 1)
    
    # Get recent submissions
    recent_submissions = db.query(Submission).order_by(Submission.created_at.desc()).limit(10).all()
    
    # Platform analytics
    platform_stats = {}
    all_submissions = db.query(Submission).all()
    
    for submission in all_submissions:
        if submission.platforms:
            for platform in submission.platforms:
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
    
    # Prepare platform chart data
    platform_labels = list(platform_stats.keys())
    platform_data = list(platform_stats.values())
    
    # Timeline analytics (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_submissions = db.query(
        func.date(Submission.created_at).label('date'),
        func.count(Submission.id).label('count')
    ).filter(
        Submission.created_at >= thirty_days_ago
    ).group_by(
        func.date(Submission.created_at)
    ).order_by('date').all()
    
    # Create timeline data
    timeline_labels = []
    timeline_data = []
    
    for day_data in daily_submissions:
        timeline_labels.append(day_data.date.strftime('%m/%d'))
        timeline_data.append(day_data.count)
    
    return templates.TemplateResponse("admin/modern_dashboard.html", {
        "request": request,
        "total_submissions": total_submissions,
        "new_submissions": new_submissions,
        "in_progress_submissions": in_progress_submissions,
        "conversion_rate": conversion_rate,
        "recent_submissions": recent_submissions,
        "platform_labels": platform_labels,
        "platform_data": platform_data,
        "timeline_labels": timeline_labels,
        "timeline_data": timeline_data
    })

@app.get("/admin/submissions", response_class=HTMLResponse)
async def admin_submissions(request: Request, db: Session = Depends(get_db)):
    """Enhanced submissions management interface"""
    
    # Get all submissions with analytics
    submissions = db.query(Submission).order_by(Submission.created_at.desc()).all()
    
    # Calculate summary stats
    total_submissions = len(submissions)
    new_count = len([s for s in submissions if s.status == "New"])
    in_progress_count = len([s for s in submissions if s.status in ["Contacted", "Proposal Sent"]])
    
    # Convert submissions to dict for JSON serialization
    submissions_data = []
    for submission in submissions:
        submissions_data.append({
            "id": submission.id,
            "business_name": submission.business_name,
            "website": submission.website,
            "contact_name": submission.contact_name,
            "email": submission.email,
            "phone": submission.phone,
            "budget": submission.budget,
            "status": submission.status,
            "priority": submission.priority,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
            "platforms": submission.platforms or [],
            "goals": submission.goals or []
        })
    
    return templates.TemplateResponse("admin/submissions_manager.html", {
        "request": request,
        "submissions": submissions_data,
        "total_submissions": total_submissions,
        "new_count": new_count,
        "in_progress_count": in_progress_count
    })

@app.get("/admin/submission/{submission_id}", response_class=HTMLResponse)
async def view_submission_detail(submission_id: int, request: Request, db: Session = Depends(get_db)):
    """View detailed submission"""
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return templates.TemplateResponse("admin/submission_detail.html", {
        "request": request,
        "submission": submission
    })

# API Routes for Dynamic Updates
@app.post("/admin/submission/{submission_id}/status")
async def update_submission_status(
    submission_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """Update submission status via API"""
    
    body = await request.json()
    new_status = body.get("status")
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.status = new_status
    submission.updated_at = datetime.utcnow()
    db.commit()
    
    return JSONResponse({"success": True, "message": "Status updated successfully"})

@app.post("/admin/submission/{submission_id}/priority")
async def update_submission_priority(
    submission_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """Update submission priority via API"""
    
    body = await request.json()
    new_priority = body.get("priority")
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.priority = new_priority
    submission.updated_at = datetime.utcnow()
    db.commit()
    
    return JSONResponse({"success": True, "message": "Priority updated successfully"})

@app.post("/admin/submissions/bulk-update-status")
async def bulk_update_status(request: Request, db: Session = Depends(get_db)):
    """Bulk update submission statuses"""
    
    body = await request.json()
    submission_ids = body.get("submission_ids", [])
    new_status = body.get("status")
    
    if not submission_ids or not new_status:
        raise HTTPException(status_code=400, detail="Missing submission IDs or status")
    
    # Update all specified submissions
    db.query(Submission).filter(
        Submission.id.in_(submission_ids)
    ).update(
        {
            "status": new_status,
            "updated_at": datetime.utcnow()
        },
        synchronize_session=False
    )
    
    db.commit()
    
    return JSONResponse({
        "success": True, 
        "message": f"Updated {len(submission_ids)} submissions to {new_status}"
    })

@app.delete("/admin/submission/{submission_id}")
async def delete_submission(submission_id: int, db: Session = Depends(get_db)):
    """Delete a submission"""
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    db.delete(submission)
    db.commit()
    
    return JSONResponse({"success": True, "message": "Submission deleted successfully"})

@app.get("/admin/export/submissions")
async def export_submissions(request: Request, db: Session = Depends(get_db)):
    """Export submissions to CSV"""
    
    # Get query parameters
    ids_param = request.query_params.get("ids")
    
    if ids_param:
        # Export specific submissions
        submission_ids = [int(id) for id in ids_param.split(",")]
        submissions = db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
    else:
        # Export all submissions
        submissions = db.query(Submission).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Business Name', 'Contact Name', 'Email', 'Phone',
        'Website', 'Budget', 'Status', 'Priority', 'Created At',
        'Products/Services', 'Brand Story', 'USP', 'Goals', 'Platforms'
    ])
    
    # Write data
    for submission in submissions:
        writer.writerow([
            submission.id,
            submission.business_name,
            submission.contact_name,
            submission.email,
            submission.phone or '',
            submission.website or '',
            submission.budget or '',
            submission.status,
            submission.priority,
            submission.created_at.strftime('%Y-%m-%d %H:%M:%S') if submission.created_at else '',
            submission.products_services or '',
            submission.brand_story or '',
            submission.usp or '',
            ', '.join(submission.goals) if submission.goals else '',
            ', '.join(submission.platforms) if submission.platforms else ''
        ])
    
    # Create response
    csv_content = output.getvalue()
    output.close()
    
    response = Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=mw_design_submissions_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )
    
    return response

@app.get("/health")
async def health_check():
    """Health check for Render deployment"""
    return {
        "status": "healthy", 
        "service": "MW Design Studio Client Intake v2.0",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main_v2:app", host="0.0.0.0", port=port, reload=True)
