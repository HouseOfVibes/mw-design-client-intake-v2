import os
import io
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import logging

from flask import Flask, render_template, request, make_response, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from weasyprint import HTML
from werkzeug.utils import secure_filename

# Import your existing models
from models import db, Submission, User
from dotenv import load_dotenv

# Notion integration
try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    print("notion-client not installed. Notion integration disabled.")

# Google Chat integration
try:
    from google_chat_notifier import GoogleChatNotifier
    chat_notifier = GoogleChatNotifier()
    CHAT_AVAILABLE = True
    print("✅ Google Chat integration enabled")
except ImportError as e:
    CHAT_AVAILABLE = False
    chat_notifier = None
    print(f"⚠️  Google Chat notifier not available: {e}")
except Exception as e:
    CHAT_AVAILABLE = False
    chat_notifier = None
    print(f"❌ Google Chat integration failed: {e}")

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production')

# Handle database URL from Render - FORCE PostgreSQL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Fail fast if no database URL - don't fall back to SQLite
    raise RuntimeError("DATABASE_URL environment variable is required")

# Fix for SQLAlchemy - Render uses postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"🔗 Database URL: {database_url[:50]}...")  # Debug print
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Notion client if available
notion_client = None
NOTION_DB_ID = None

if NOTION_AVAILABLE:
    notion_token = os.environ.get('NOTION_TOKEN')
    NOTION_DB_ID = os.environ.get('NOTION_DB_ID')
    
    if notion_token and NOTION_DB_ID:
        try:
            notion_client = Client(auth=notion_token)
            print("✅ Notion integration enabled")
        except Exception as e:
            print(f"❌ Notion integration failed: {e}")
            notion_client = None
    else:
        print("⚠️  Notion credentials not found. Integration disabled.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Enhanced Submission model methods (add these to your models.py)
def enhance_submission_model():
    """Add Notion integration methods to Submission model"""
    
    # Add new fields for Notion tracking
    Submission.notion_page_id = db.Column(db.String(255))
    Submission.synced_to_notion = db.Column(db.Boolean, default=False)
    Submission.notion_sync_error = db.Column(db.Text)
    Submission.last_notion_sync = db.Column(db.DateTime)
    
    # Add admin workflow fields
    Submission.status = db.Column(db.String(50), default='New')
    Submission.priority = db.Column(db.String(20), default='Medium')
    Submission.assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    Submission.internal_notes = db.Column(db.Text)
    Submission.updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_notion_properties(self):
        """Convert submission to Notion page properties format"""
        properties = {
            "Business Name": {
                "title": [{"text": {"content": self.business_name or ""}}]
            },
            "Contact Person": {
                "rich_text": [{"text": {"content": self.contact_name or ""}}]
            },
            "Email": {
                "email": self.email or ""
            },
            "Phone": {
                "phone_number": self.phone or ""
            },
            "Website": {
                "url": self.website or ""
            },
            "Company Size": {
                "select": {"name": self.company_size or "Not specified"}
            },
            "Budget": {
                "select": {"name": self.budget or "Not specified"}
            },
            "Status": {
                "select": {"name": getattr(self, 'status', 'New')}
            },
            "Priority": {
                "select": {"name": getattr(self, 'priority', 'Medium')}
            },
            "Created": {
                "date": {"start": self.created_at.isoformat() if self.created_at else None}
            },
            "Products/Services": {
                "rich_text": [{"text": {"content": (self.products_services or "")[:2000]}}]
            },
            "Brand Story": {
                "rich_text": [{"text": {"content": (self.brand_story or "")[:2000]}}]
            },
            "Target Demographics": {
                "rich_text": [{"text": {"content": (self.demographics or "")[:2000]}}]
            },
            "Brand Voice": {
                "select": {"name": self.brand_voice or "Not specified"}
            },
            "Content Tone": {
                "select": {"name": self.content_tone or "Not specified"}
            },
            "Timeline": {
                "select": {"name": self.timeline or "Not specified"}
            },
            "Posting Frequency": {
                "select": {"name": self.posting_frequency or "Not specified"}
            }
        }
        
        # Handle array fields
        if self.goals:
            goals_text = "\n".join([f"• {goal}" for goal in self.goals[:10]])  # Limit for Notion
            properties["Goals"] = {
                "rich_text": [{"text": {"content": goals_text[:2000]}}]
            }
        
        if self.platforms:
            # Notion multi-select has limits
            platform_names = [p for p in self.platforms[:10] if len(p) <= 100]
            if platform_names:
                properties["Platforms"] = {
                    "multi_select": [{"name": platform} for platform in platform_names]
                }
        
        return properties
    
    # Add the method to the Submission class
    Submission.to_notion_properties = to_notion_properties

# Notion Integration Functions
def create_notion_page(submission):
    """Create a new page in Notion database for the submission"""
    if not notion_client or not NOTION_DB_ID:
        logger.warning("Notion client not available")
        return None
        
    try:
        logger.info(f"Creating Notion page for submission {submission.id}")
        
        response = notion_client.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties=submission.to_notion_properties()
        )
        
        # Update submission with Notion details
        submission.notion_page_id = response['id']
        submission.synced_to_notion = True
        submission.last_notion_sync = datetime.utcnow()
        submission.notion_sync_error = None
        
        db.session.commit()
        
        logger.info(f"✅ Created Notion page {response['id']} for submission {submission.id}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to create Notion page: {str(e)}"
        logger.error(error_msg)
        
        submission.synced_to_notion = False
        submission.notion_sync_error = error_msg
        db.session.commit()
        
        return None

def update_notion_page(submission):
    """Update existing Notion page with submission changes"""
    if not notion_client or not submission.notion_page_id:
        return create_notion_page(submission)
    
    try:
        logger.info(f"Updating Notion page {submission.notion_page_id}")
        
        response = notion_client.pages.update(
            page_id=submission.notion_page_id,
            properties=submission.to_notion_properties()
        )
        
        submission.last_notion_sync = datetime.utcnow()
        submission.notion_sync_error = None
        db.session.commit()
        
        logger.info(f"✅ Updated Notion page {submission.notion_page_id}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to update Notion page: {str(e)}"
        logger.error(error_msg)
        
        submission.notion_sync_error = error_msg
        db.session.commit()
        
        return None

# Create tables and enhance model
with app.app_context():
    db.create_all()
    enhance_submission_model()

# Your existing routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy', 'service': 'MW Design Studio - Client Intake'}

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        new_submission = Submission(
            business_name=request.form.get('businessName'),
            website=request.form.get('website'),
            products_services=request.form.get('productsServices'),
            brand_story=request.form.get('brandStory'),
            usp=request.form.get('usp'),
            company_size=request.form.get('companySize'),
            social_media=request.form.get('socialMedia'),
            follower_counts=request.form.get('followerCounts'),
            management=request.form.get('management'),
            goals=request.form.getlist('goals'),
            kpi=request.form.get('kpi'),
            paid_ads=request.form.get('paidAds'),
            timeline=request.form.get('timeline'),
            demographics=request.form.get('demographics'),
            problems_solutions=request.form.get('problemsSolutions'),
            brand_voice=request.form.get('brandVoice'),
            content_tone=request.form.get('contentTone'),
            platforms=request.form.getlist('platforms'),
            management_type=request.form.get('managementType'),
            existing_content=request.form.get('existingContent'),
            content_writing=request.form.get('contentWriting'),
            brand_colors=request.form.get('brandColors'),
            brand_fonts=request.form.get('brandFonts'),
            logo_graphics=request.form.get('logoGraphics'),
            competitors=request.form.get('competitors'),
            inspiration=request.form.get('inspiration'),
            budget=request.form.get('budget'),
            launch_timeline=request.form.get('launchTimeline'),
            content_provision=request.form.get('contentProvision'),
            posting_frequency=request.form.get('postingFrequency'),
            contact_name=request.form.get('contactName'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            additional_info=request.form.get('additionalInfo'),
        )
        
        db.session.add(new_submission)
        db.session.commit()
        
        # Send Google Chat notification
        if CHAT_AVAILABLE and chat_notifier:
            try:
                chat_notifier.send_new_submission_sync({
                    'id': new_submission.id,
                    'business_name': new_submission.business_name,
                    'contact_name': new_submission.contact_name,
                    'email': new_submission.email,
                    'phone': new_submission.phone,
                    'website': new_submission.website,
                    'created_at': new_submission.created_at.isoformat() if new_submission.created_at else None
                })
            except Exception as e:
                logger.error(f"Google Chat notification failed: {e}")
        
        # Try to sync to Notion
        notion_success = False
        if notion_client:
            try:
                create_notion_page(new_submission)
                notion_success = True
                flash('Form submitted successfully and synced to Notion!', 'success')
            except Exception as e:
                logger.error(f"Notion sync failed: {e}")
                flash('Form submitted successfully! (Notion sync pending)', 'warning')
        else:
            flash('Form submitted successfully!', 'success')
            
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error submitting form: {e}')
        flash(f'Error submitting form: {e}', 'danger')

    # Generate and return PDF as before
    html = render_template('client_intake_strategy.html', 
                          business_name=new_submission.business_name,
                          contact_name=new_submission.contact_name,
                          email=new_submission.email,
                          website=new_submission.website,
                          created_at=new_submission.created_at,
                          products_services=new_submission.products_services,
                          usp=new_submission.usp,
                          brand_story=new_submission.brand_story,
                          social_media=new_submission.social_media,
                          goals=new_submission.goals,
                          kpi=new_submission.kpi,
                          paid_ads=new_submission.paid_ads,
                          timeline=new_submission.timeline,
                          demographics=new_submission.demographics,
                          problems_solutions=new_submission.problems_solutions,
                          brand_voice=new_submission.brand_voice,
                          content_tone=new_submission.content_tone,
                          platforms=new_submission.platforms,
                          management_type=new_submission.management_type,
                          existing_content=new_submission.existing_content,
                          content_writing=new_submission.content_writing,
                          brand_colors=new_submission.brand_colors,
                          brand_fonts=new_submission.brand_fonts,
                          competitors=new_submission.competitors,
                          inspiration=new_submission.inspiration,
                          additional_info=new_submission.additional_info)
    
    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={secure_filename(new_submission.business_name or "client")}_intake.pdf'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('admin_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Enhanced dashboard with statistics
    total_submissions = Submission.query.count()
    new_submissions = Submission.query.filter_by(status='New').count() if hasattr(Submission, 'status') else 0
    
    # Get recent submissions
    submissions = Submission.query.order_by(Submission.created_at.desc()).limit(10).all()
    
    # Notion sync stats
    synced_count = 0
    failed_sync_count = 0
    if notion_client:
        synced_count = Submission.query.filter_by(synced_to_notion=True).count()
        failed_sync_count = Submission.query.filter(Submission.notion_sync_error.isnot(None)).count()
    
    return render_template('dashboard.html', 
                         submissions=submissions,
                         total_submissions=total_submissions,
                         new_submissions=new_submissions,
                         synced_count=synced_count,
                         failed_sync_count=failed_sync_count,
                         notion_enabled=notion_client is not None)

@app.route('/admin/submissions')
@login_required
def submissions_list():
    """Enhanced submissions list with filtering"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # Build query
    query = Submission.query
    
    # Apply filters
    if hasattr(Submission, 'status') and status_filter != 'all':
        query = query.filter(Submission.status == status_filter)
    
    # Apply search
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Submission.business_name.ilike(search_pattern),
                Submission.contact_name.ilike(search_pattern),
                Submission.email.ilike(search_pattern)
            )
        )
    
    # Get all submissions
    submissions = query.order_by(Submission.created_at.desc()).all()
    
    return render_template('submissions_list.html',
                         submissions=submissions,
                         current_filters={
                             'status': status_filter,
                             'search': search_query
                         })

@app.route('/submission/<int:submission_id>')
@login_required
def view_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    return render_template('view_submission.html', submission=submission)

@app.route('/download_pdf/<int:submission_id>')
@login_required
def download_pdf(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    html = render_template('client_intake_strategy.html', **submission.__dict__)
    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=submission_{submission.id}.pdf'
    return response

# New Enhanced Admin Routes
@app.route('/admin/submission/<int:submission_id>/update-status', methods=['POST'])
@login_required
def update_submission_status(submission_id):
    """Update submission status and sync to Notion"""
    submission = Submission.query.get_or_404(submission_id)
    
    new_status = request.form.get('status')
    new_priority = request.form.get('priority')
    internal_notes = request.form.get('internal_notes')
    
    # Update fields
    if hasattr(submission, 'status'):
        submission.status = new_status
    if hasattr(submission, 'priority'):
        submission.priority = new_priority
    if hasattr(submission, 'internal_notes'):
        submission.internal_notes = internal_notes
    
    submission.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Sync to Notion if available
    if notion_client:
        update_notion_page(submission)
    
    flash('Submission updated successfully!', 'success')
    return redirect(url_for('view_submission', submission_id=submission_id))

@app.route('/admin/export/csv')
@login_required
def export_csv():
    """Export submissions to CSV"""
    submissions = Submission.query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = [
        'ID', 'Business Name', 'Contact Name', 'Email', 'Phone', 'Website',
        'Company Size', 'Budget', 'Status', 'Priority', 'Created At',
        'Products/Services', 'Brand Story', 'Demographics', 'Goals', 'Platforms'
    ]
    writer.writerow(headers)
    
    # Write data
    for submission in submissions:
        row = [
            submission.id,
            submission.business_name or '',
            submission.contact_name or '',
            submission.email or '',
            submission.phone or '',
            submission.website or '',
            submission.company_size or '',
            submission.budget or '',
            getattr(submission, 'status', 'New'),
            getattr(submission, 'priority', 'Medium'),
            submission.created_at.strftime('%Y-%m-%d %H:%M:%S') if submission.created_at else '',
            submission.products_services or '',
            submission.brand_story or '',
            submission.demographics or '',
            '; '.join(submission.goals) if submission.goals else '',
            '; '.join(submission.platforms) if submission.platforms else ''
        ]
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    filename = f"mw_design_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@app.route('/admin/notion/sync-all', methods=['POST'])
@login_required
def sync_all_notion():
    """Sync all unsynced submissions to Notion"""
    if not notion_client:
        flash('Notion integration not available', 'error')
        return redirect(url_for('dashboard'))
    
    unsynced = Submission.query.filter_by(synced_to_notion=False).all()
    
    success_count = 0
    for submission in unsynced:
        if create_notion_page(submission):
            success_count += 1
    
    flash(f'Synced {success_count} of {len(unsynced)} submissions to Notion', 
          'success' if success_count == len(unsynced) else 'warning')
    
    return redirect(url_for('dashboard'))

@app.route('/admin/notion/sync/<int:submission_id>', methods=['POST'])
@login_required
def sync_single_notion(submission_id):
    """Sync single submission to Notion"""
    if not notion_client:
        flash('Notion integration not available', 'error')
        return redirect(url_for('view_submission', submission_id=submission_id))
    
    submission = Submission.query.get_or_404(submission_id)
    
    if submission.notion_page_id:
        result = update_notion_page(submission)
    else:
        result = create_notion_page(submission)
    
    if result:
        flash('Successfully synced to Notion!', 'success')
    else:
        flash('Failed to sync to Notion. Check logs for details.', 'error')
    
    return redirect(url_for('view_submission', submission_id=submission_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
