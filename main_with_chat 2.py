"""
MW Design Studio - Enhanced Admin System with Google Chat Integration
FastAPI + Tailwind CSS + PostgreSQL + Google Chat Webhooks
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
import asyncio

# Import our models and database
from database_v2 import get_db, init_db
from models_v2 import Submission, User, SubmissionUpdate
from google_chat_notifier import google_chat_notifier

# Initialize FastAPI app
app = FastAPI(
    title="MW Design Studio - Enhanced Client Intake System",
    description="Modern client intake system with Google Chat notifications, advanced analytics, and comprehensive admin dashboard",
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
    # Test Google Chat webhooks on startup
    await test_google_chat_webhooks()

async def test_google_chat_webhooks():
    """Test Google Chat webhooks on application startup"""
    try:
        results = google_chat_notifier.test_webhooks()
        working_webhooks = [k for k, v in results.items() if v]
        if working_webhooks:
            print(f"✅ Google Chat webhooks configured: {', '.join(working_webhooks)}")
            await google_chat_notifier.send_admin_alert(
                "success",
                "MW Design Studio Client Intake System is online and ready!",
                {"working_webhooks": ", ".join(working_webhooks)}
            )
        else:
            print("⚠️ No Google Chat webhooks configured. Check environment variables.")
    except Exception as e:
        print(f"❌ Error testing webhooks: {str(e)}")

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
    """Process form submission and send Google Chat notification"""
    
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
        
        # Prepare submission data for Google Chat notification
        submission_data = {
            "id": new_submission.id,
            "business_name": business_name,
            "website": website,
            "contact_name": contact_name,
            "email": email,
            "phone": phone,
            "budget": budget,
            "timeline": timeline,
            "platforms": platforms or [],
            "goals": goals or [],
            "company_size": company_size,
            "brand_voice": brand_voice,
            "content_tone": content_tone,
            "products_services": products_services
        }
        
        # Send Google Chat notification asynchronously
        try:
            asyncio.create_task(
                google_chat_notifier.send_new_submission_notification(submission_data)
            )
        except Exception as e:
            # Log the error but don't fail the submission
            print(f"Failed to send Google Chat notification: {str(e)}")
        
        # Return success response
        return JSONResponse({
            "success": True,
            "message": "Submission received successfully! Our team has been notified.",
            "submission_id": new_submission.id
        })
        
    except Exception as e:
        # Send error alert to admin
        try:
            asyncio.create_task(
                google_chat_notifier.send_admin_alert(
                    "error",
                    f"Failed to process client submission: {str(e)}",
                    {"business_name": business_name, "email": email}
                )
            )
        except:
            pass
        
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

# API Routes for Dynamic Updates with Google Chat Notifications
@app.post("/admin/submission/{submission_id}/status")
async def update_submission_status(
    submission_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """Update submission status via API with Google Chat notification"""
    
    body = await request.json()
    new_status = body.get("status")
    
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    old_status = submission.status
    submission.status = new_status
    submission.updated_at = datetime.utcnow()
    db.commit()
    
    # Send Google Chat notification for status change
    try:
        submission_data = {
            "id": submission.id,
            "business_name": submission.business_name,
            "contact_name": submission.contact_name,
            "email": submission.email,
            "budget": submission.budget
        }
        
        asyncio.create_task(
            google_chat_notifier.send_status_update_notification(
                submission_data, old_status, new_status
            )
        )
    except Exception as e:
        print(f"Failed to send status update notification: {str(e)}")
    
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
    updated_count = db.query(Submission).filter(
        Submission.id.in_(submission_ids)
    ).update(
        {
            "status": new_status,
            "updated_at": datetime.utcnow()
        },
        synchronize_session=False
    )
    
    db.commit()
    
    # Send admin notification about bulk update
    try:
        asyncio.create_task(
            google_chat_notifier.send_admin_alert(
                "info",
                f"Bulk status update completed: {updated_count} submissions updated to '{new_status}'",
                {"submission_count": updated_count, "new_status": new_status}
            )
        )
    except Exception as e:
        print(f"Failed to send bulk update notification: {str(e)}")
    
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
    
    business_name = submission.business_name
    
    db.delete(submission)
    db.commit()
    
    # Send admin notification about deletion
    try:
        asyncio.create_task(
            google_chat_notifier.send_admin_alert(
                "warning",
                f"Submission deleted: {business_name}",
                {"submission_id": submission_id, "business_name": business_name}
            )
        )
    except Exception as e:
        print(f"Failed to send deletion notification: {str(e)}")
    
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
        export_type = f"selected ({len(submission_ids)} submissions)"
    else:
        # Export all submissions
        submissions = db.query(Submission).all()
        export_type = f"all ({len(submissions)} submissions)"
    
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
    
    # Send admin notification about export
    try:
        asyncio.create_task(
            google_chat_notifier.send_admin_alert(
                "info",
                f"Data export completed: {export_type}",
                {"export_type": export_type, "timestamp": datetime.now().isoformat()}
            )
        )
    except Exception as e:
        print(f"Failed to send export notification: {str(e)}")
    
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

# Google Chat Webhook Management Routes
@app.get("/admin/webhooks/test")
async def test_webhooks():
    """Test all configured Google Chat webhooks"""
    try:
        results = google_chat_notifier.test_webhooks()
        return JSONResponse({
            "success": True,
            "results": results,
            "message": "Webhook test completed"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": "Webhook test failed"
        })

@app.post("/admin/webhooks/send-test-notification")
async def send_test_notification():
    """Send a test notification to Google Chat"""
    try:
        # Create test submission data
        test_data = {
            "id": 999,
            "business_name": "Test Business Inc.",
            "contact_name": "Test Contact",
            "email": "test@example.com",
            "phone": "(555) 123-4567",
            "budget": "$5,000-10,000",
            "timeline": "Within 1 month",
            "platforms": ["Instagram", "Facebook", "LinkedIn"],
            "goals": ["Increase Brand Awareness", "Generate Leads"],
            "website": "https://test-business.com"
        }
        
        success = await google_chat_notifier.send_new_submission_notification(test_data)
        
        return JSONResponse({
            "success": success,
            "message": "Test notification sent" if success else "Test notification failed"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": "Failed to send test notification"
        })

@app.get("/health")
async def health_check():
    """Health check for Render deployment"""
    return {
        "status": "healthy", 
        "service": "MW Design Studio Client Intake v2.0 with Google Chat Integration",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "FastAPI Backend",
            "PostgreSQL Database",
            "Google Chat Webhooks",
            "Advanced Analytics",
            "Real-time Notifications"
        ]
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main_with_chat:app", host="0.0.0.0", port=port, reload=True)
