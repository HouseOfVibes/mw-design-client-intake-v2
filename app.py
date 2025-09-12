import os
import io
import csv
import json
import smtplib
import re
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import logging

from flask import Flask, render_template, request, make_response, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from weasyprint import HTML
from werkzeug.utils import secure_filename
from markupsafe import escape

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
    print("Google Chat integration enabled")
except ImportError as e:
    CHAT_AVAILABLE = False
    chat_notifier = None
    print(f"WARNING: Google Chat notifier not available: {e}")
except Exception as e:
    CHAT_AVAILABLE = False
    chat_notifier = None
    print(f"ERROR: Google Chat integration failed: {e}")

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Generate secure secret key if not provided
if not os.environ.get('SECRET_KEY'):
    secret_key = secrets.token_urlsafe(32)
    print(f"Generated SECRET_KEY: {secret_key}")
    os.environ['SECRET_KEY'] = secret_key

# Secure Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file upload
    WTF_CSRF_TIME_LIMIT=3600,  # CSRF token expires in 1 hour
)

# Initialize security extensions
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://'),
)

# Handle database URL - Allow SQLite for development
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Use SQLite for development/testing
    database_url = 'sqlite:///local_database.db'
    print("⚠️  Using SQLite for development. Set DATABASE_URL for production.")

# Fix for SQLAlchemy - Render uses postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
if not os.environ.get('FLASK_ENV') == 'production':
    print(f"🔗 Database URL: {database_url[:50]}...")  # Only show in dev
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
            print("Notion integration enabled")
        except Exception as e:
            print(f"ERROR: Notion integration failed: {e}")
            notion_client = None
    else:
        print("WARNING: Notion credentials not found. Integration disabled.")

# Set up secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Security logging
security_logger = logging.getLogger('security')
security_handler = logging.FileHandler('security.log')
security_logger.addHandler(security_handler)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Security Headers Middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Only add HSTS in production
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response

# Input Validation Functions
def validate_email(email):
    """Validate email format"""
    if not email or len(email) > 320:  # RFC compliant max length
        return False, "Invalid email length"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, "Valid"

def validate_phone(phone):
    """Validate phone number"""
    if not phone:
        return True, "Valid"  # Optional field
    
    # Remove common formatting characters
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    if len(clean_phone) < 10 or len(clean_phone) > 15:
        return False, "Phone number must be 10-15 digits"
    
    return True, "Valid"

def validate_text_field(text, field_name, max_length=2000, required=False):
    """Validate text fields"""
    if required and (not text or not text.strip()):
        return False, f"{field_name} is required"
    
    if text and len(text) > max_length:
        return False, f"{field_name} must be less than {max_length} characters"
    
    # Check for potential XSS patterns
    dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
    text_lower = text.lower() if text else ''
    
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            return False, f"Invalid characters in {field_name}"
    
    return True, "Valid"

def sanitize_input(text):
    """Sanitize user input"""
    if not text:
        return ''
    
    # Escape HTML and remove potential XSS
    sanitized = escape(str(text).strip())
    
    # Additional sanitization - remove null bytes
    sanitized = sanitized.replace('\\x00', '')
    
    return str(sanitized)

def log_security_event(event_type, user_id=None, ip_address=None, details=""):
    """Log security events"""
    ip = ip_address or request.remote_addr
    security_logger.warning(f"{datetime.now()} - {event_type} - User: {user_id} - IP: {ip} - {details}")

# Notion integration methods are now in models.py

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
        
        logger.info(f"Created Notion page {response['id']} for submission {submission.id}")
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
        
        logger.info(f"Updated Notion page {submission.notion_page_id}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to update Notion page: {str(e)}"
        logger.error(error_msg)
        
        submission.notion_sync_error = error_msg
        db.session.commit()
        
        return None

# Create tables
with app.app_context():
    db.create_all()

# Your existing routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy', 'service': 'MW Design Studio - Client Intake'}

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engines"""
    return send_file('static/robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Generate dynamic XML sitemap"""
    from flask import Response
    from datetime import datetime
    
    # Base URL for the site
    base_url = request.url_root.rstrip('/')
    
    # Sitemap XML structure
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{date}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{base_url}/health</loc>
        <lastmod>{date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.3</priority>
    </url>
</urlset>'''.format(
        base_url=base_url,
        date=datetime.now().strftime('%Y-%m-%d')
    )
    
    return Response(xml_content, mimetype='application/xml')

@app.route('/submit_form', methods=['POST'])
@limiter.limit("5 per minute")
def submit_form():
    try:
        # Validate required fields
        business_name = sanitize_input(request.form.get('business_name', ''))
        contact_name = sanitize_input(request.form.get('contact_name', ''))
        email = sanitize_input(request.form.get('email', ''))
        
        # Validate business name (required)
        is_valid, msg = validate_text_field(business_name, 'Business name', 255, required=True)
        if not is_valid:
            flash(msg, 'danger')
            log_security_event('Invalid Form Submission', details=f'Business name validation failed: {msg}')
            return redirect(url_for('home'))
        
        # Validate contact name (required)
        is_valid, msg = validate_text_field(contact_name, 'Contact name', 255, required=True)
        if not is_valid:
            flash(msg, 'danger')
            log_security_event('Invalid Form Submission', details=f'Contact name validation failed: {msg}')
            return redirect(url_for('home'))
        
        # Validate email (required)
        is_valid, msg = validate_email(email)
        if not is_valid:
            flash(msg, 'danger')
            log_security_event('Invalid Form Submission', details=f'Email validation failed: {msg}')
            return redirect(url_for('home'))
        
        # Validate phone (optional)
        phone = sanitize_input(request.form.get('phone', ''))
        is_valid, msg = validate_phone(phone)
        if not is_valid:
            flash(msg, 'danger')
            log_security_event('Invalid Form Submission', details=f'Phone validation failed: {msg}')
            return redirect(url_for('home'))
        
        # Sanitize all other text fields
        website = sanitize_input(request.form.get('website', ''))
        products_services = sanitize_input(request.form.get('products_services', ''))
        brand_story = sanitize_input(request.form.get('brand_story', ''))
        usp = sanitize_input(request.form.get('usp', ''))
        slogan = sanitize_input(request.form.get('slogan', ''))
        
        # Validate website URL if provided
        if website and not (website.startswith('http://') or website.startswith('https://')):
            if not website.startswith('www.'):
                website = f'https://{website}'
            else:
                website = f'https://{website}'
        new_submission = Submission(
            business_name=business_name,
            website=website,
            products_services=products_services,
            brand_story=brand_story,
            usp=usp,
            slogan=slogan,
            company_size=sanitize_input(request.form.get('company_size', '')),
            social_handles=sanitize_input(request.form.get('social_handles', '')),
            follower_counts=sanitize_input(request.form.get('follower_counts', '')),
            social_management=sanitize_input(request.form.get('social_management', '')),
            goals=json.dumps([sanitize_input(goal) for goal in request.form.getlist('goals')]),
            kpis=sanitize_input(request.form.get('kpis', '')),
            paid_ads=sanitize_input(request.form.get('paid_ads', '')),
            timeline=sanitize_input(request.form.get('timeline', '')),
            ideal_customer=sanitize_input(request.form.get('ideal_customer', '')),
            demographics=sanitize_input(request.form.get('demographics', '')),
            problems_solutions=sanitize_input(request.form.get('problems_solutions', '')),
            brand_voice=sanitize_input(request.form.get('brand_voice', '')),
            content_tone=sanitize_input(request.form.get('content_tone', '')),
            brand_words=sanitize_input(request.form.get('brand_words', '')),
            platforms=json.dumps([sanitize_input(platform) for platform in request.form.getlist('platforms')]),
            posting_approach=sanitize_input(request.form.get('posting_approach', '')),
            content_availability=sanitize_input(request.form.get('content_availability', '')),
            contact_name=contact_name,
            email=email,
            phone=phone,
            industry=sanitize_input(request.form.get('industry', '')),
            brand_colors=sanitize_input(request.form.get('brand_colors', '')),
            brand_fonts=sanitize_input(request.form.get('brand_fonts', '')),
            logo_status=sanitize_input(request.form.get('logo_status', '')),
            competitors=sanitize_input(request.form.get('competitors', '')),
            budget=sanitize_input(request.form.get('budget', '')),
            start_date=sanitize_input(request.form.get('start_date', '')),
            posting_frequency=sanitize_input(request.form.get('posting_frequency', '')),
            approval_level=sanitize_input(request.form.get('approval_level', '')),
            inspiration_accounts=sanitize_input(request.form.get('inspiration_accounts', '')),
            social_challenges=sanitize_input(request.form.get('social_challenges', '')),
            questions_about_services=sanitize_input(request.form.get('questions_about_services', '')),
            additional_info=sanitize_input(request.form.get('additional_info', '')),
            
            # New service-specific fields (sanitized)
            services_needed=','.join([sanitize_input(service) for service in request.form.getlist('services_needed')]),
            photography_type=','.join([sanitize_input(ptype) for ptype in request.form.getlist('photography_type')]),
            photography_location=sanitize_input(request.form.get('photography_location', '')),
            photography_timeline=sanitize_input(request.form.get('photography_timeline', '')),
            brand_services=','.join([sanitize_input(service) for service in request.form.getlist('brand_services')]),
            brand_stage=sanitize_input(request.form.get('brand_stage', '')),
            brand_priority=sanitize_input(request.form.get('brand_priority', '')),
            marketing_services=','.join([sanitize_input(service) for service in request.form.getlist('marketing_services')]),
            project_urgency=sanitize_input(request.form.get('project_urgency', '')),
            current_challenges=sanitize_input(request.form.get('current_challenges', '')),
            success_measurement=sanitize_input(request.form.get('success_measurement', '')),
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

    # Redirect to success page instead of generating PDF
    return redirect(url_for('submission_success'))

@app.route('/success', methods=['GET', 'POST'])
def submission_success():
    """Display success page after form submission"""
    return render_template('submission_success.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')
        
        # Validate input
        if not username or not password:
            flash('Username and password are required', 'danger')
            log_security_event('Invalid Login Attempt', details='Missing credentials')
            return render_template('admin_login.html')
        
        if len(username) > 255 or len(password) > 255:
            flash('Invalid credentials', 'danger')
            log_security_event('Invalid Login Attempt', details='Credential length exceeded')
            return render_template('admin_login.html')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=False, duration=timedelta(hours=2))
            log_security_event('Successful Login', user_id=user.id, details=f'User {username} logged in')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            log_security_event('Failed Login Attempt', details=f'Failed login for username: {username}')
            
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
@login_required  # Only existing admins can create new accounts
@limiter.limit("3 per hour")  # Strict rate limiting for account creation
def register():
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', '')).strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate inputs
        if not username or not password:
            flash('Username and password are required.', 'danger')
            log_security_event('Invalid Registration Attempt', user_id=current_user.id, details='Missing credentials')
            return render_template('register.html')
        
        # Username validation
        if len(username) < 3 or len(username) > 50:
            flash('Username must be between 3-50 characters.', 'danger')
            return render_template('register.html')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username can only contain letters, numbers, and underscores.', 'danger')
            return render_template('register.html')
        
        # Password validation
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('register.html')
        
        # Confirm password match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            log_security_event('Registration Attempt - Duplicate Username', user_id=current_user.id, details=f'Attempted username: {username}')
            return render_template('register.html')
        
        # Create user
        try:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! New admin account created.', 'success')
            log_security_event('New User Created', user_id=current_user.id, details=f'Created user: {username}')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')
            
    return render_template('register.html')

def validate_password(password):
    """Validate password strength"""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Valid password"

# Enhanced Error handlers for security and UX
@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 error page with proper SEO"""
    log_security_event('Page Not Found', details=f'404 for URL: {request.url}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Custom 500 error handler"""
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    log_security_event('Internal Server Error', details=f'500 error for URL: {request.url}')
    return render_template('404.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    """Custom 403 error handler"""
    log_security_event('Access Forbidden', details=f'403 error for URL: {request.url}')
    return render_template('404.html'), 403

@app.errorhandler(429)
def rate_limit_handler(error):
    """Rate limit exceeded error"""
    log_security_event('Rate Limit Exceeded', details=f'Rate limit hit for URL: {request.url}')
    return jsonify(error='Rate limit exceeded. Please try again later.'), 429

@app.errorhandler(413)
def request_entity_too_large(error):
    """File upload too large"""
    log_security_event('Upload Too Large', details=f'Large upload attempt for URL: {request.url}')
    return jsonify(error='File too large. Maximum size is 16MB.'), 413

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

if __name__ == '__main__':
    # Secure production configuration
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5000))
    
    if debug_mode:
        print("⚠️  Running in DEBUG mode. Set FLASK_ENV=production for production use.")
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        print("✅ Running in PRODUCTION mode")
        app.run(debug=False, host='0.0.0.0', port=port)
