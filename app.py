import os
import re
import secrets
from datetime import datetime
import logging

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import escape
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

# No database needed - submissions go directly to Notion
print("✅ Running without local database - all submissions go to Notion")

# Initialize Notion client if available
notion_client = None
NOTION_DB_ID = None

if NOTION_AVAILABLE:
    notion_token = os.environ.get('NOTION_TOKEN')
    NOTION_DB_ID = os.environ.get('NOTION_DATABASE_ID')
    
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

def send_to_notion_direct(form_data):
    """Send form data directly to Notion database (for simplified form)"""
    if not notion_client or not NOTION_DB_ID:
        logger.warning("Notion client not available")
        return False

    try:
        # Security: Log form submission attempt
        ip_address = request.remote_addr if request else 'Unknown'
        log_security_event('Form Submission Attempt', ip_address=ip_address,
                          details=f'Business: {form_data.get("business_name", "Unknown")}')

        # Security: Additional validation for critical fields
        email = form_data.get('email', '')
        if email and '@' not in email:
            logger.warning(f"Suspicious email format: {email}")
            return False
        # Extract services needed array
        services_needed = form_data.getlist('services_needed')

        # Create Notion page properties based on simplified form
        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": form_data.get('contact_name', '')
                        }
                    }
                ]
            },
            "Contact Name": {
                "rich_text": [
                    {
                        "text": {
                            "content": form_data.get('contact_name', '')
                        }
                    }
                ]
            },
            "Business Name": {
                "rich_text": [
                    {
                        "text": {
                            "content": form_data.get('business_name', '')
                        }
                    }
                ]
            },
            "Email": {
                "email": form_data.get('email', '')
            },
            "Phone": {
                "phone_number": form_data.get('phone') if form_data.get('phone') else None
            },
            "Preferred Contact": {
                "select": {
                    "name": form_data.get('preferred_contact', '')
                } if form_data.get('preferred_contact') else None
            },
            "Services Needed": {
                "multi_select": [
                    {"name": service} for service in services_needed
                ]
            },
            "Project Goals": {
                "rich_text": [
                    {
                        "text": {
                            "content": form_data.get('project_goals', '')
                        }
                    }
                ]
            },
            "Preferred Start Date": {
                "rich_text": [
                    {
                        "text": {
                            "content": form_data.get('start_date', '')
                        }
                    }
                ]
            },
            "Budget Range": {
                "select": {
                    "name": form_data.get('budget_range', '')
                } if form_data.get('budget_range') else None
            },
            "Additional Information": {
                "rich_text": [
                    {
                        "text": {
                            "content": form_data.get('additional_info', '')
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "New"
                }
            }
        }

        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}

        # Create the page
        response = notion_client.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties=properties
        )

        logger.info(f"Successfully created Notion page: {response['id']}")

        # Security: Log successful submission
        log_security_event('Form Submission Success', ip_address=ip_address,
                          details=f'Notion page created: {response["id"][:10]}...')
        return True

    except Exception as e:
        logger.error(f"Failed to send data to Notion: {str(e)}")

        # Security: Log failed submission
        log_security_event('Form Submission Failed', ip_address=ip_address,
                          details=f'Notion error: {str(e)[:100]}')
        return False

# No local database tables needed - using Notion as database

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

@app.route('/submit_form_new', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
def submit_form_new():
    """New simplified form submission handler for Notion integration"""
    try:
        # Validate required fields for simplified form
        business_name = sanitize_input(request.form.get('business_name', ''))
        contact_name = sanitize_input(request.form.get('contact_name', ''))
        email = sanitize_input(request.form.get('email', ''))
        project_goals = sanitize_input(request.form.get('project_goals', ''))

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

        # Validate project goals (required)
        is_valid, msg = validate_text_field(project_goals, 'Project goals', 2000, required=True)
        if not is_valid:
            flash(msg, 'danger')
            log_security_event('Invalid Form Submission', details=f'Project goals validation failed: {msg}')
            return redirect(url_for('home'))

        # Validate phone (optional)
        phone = sanitize_input(request.form.get('phone', ''))
        if phone:
            is_valid, msg = validate_phone(phone)
            if not is_valid:
                flash(msg, 'danger')
                log_security_event('Invalid Form Submission', details=f'Phone validation failed: {msg}')
                return redirect(url_for('home'))

        # Send to Notion first
        notion_success = False
        if notion_client and NOTION_DB_ID:
            try:
                notion_success = send_to_notion_direct(request.form)
                if notion_success:
                    logger.info("Successfully sent form data to Notion")
                else:
                    logger.warning("Failed to send form data to Notion")
            except Exception as e:
                logger.error(f"Notion integration error: {e}")

        # Send to Google Chat if available
        if CHAT_AVAILABLE and chat_notifier:
            try:
                # Create simplified form data for notification
                chat_data = {
                    'business_name': business_name,
                    'contact_name': contact_name,
                    'email': email,
                    'phone': phone,
                    'project_goals': project_goals,
                    'services_needed': request.form.getlist('services_needed'),
                    'preferred_contact': request.form.get('preferred_contact', ''),
                    'start_date': request.form.get('start_date', ''),
                    'budget_range': request.form.get('budget_range', ''),
                    'additional_info': request.form.get('additional_info', '')
                }

                chat_notifier.send_simple_notification(chat_data)
                logger.info("Successfully sent Google Chat notification")
            except Exception as e:
                logger.error(f"Google Chat notification failed: {e}")

        # Show appropriate success message
        if notion_success:
            flash('Thank you! Your intake form has been submitted successfully. We\'ll be in touch soon!', 'success')
        else:
            flash('Thank you! Your intake form has been submitted. We\'ll be in touch soon!', 'success')

    except Exception as e:
        logger.error(f'Error submitting form: {e}')
        flash('Sorry, there was an error submitting your form. Please try again or contact us directly.', 'danger')

    # Redirect to success page
    return redirect(url_for('submission_success'))

# Old database-based form submission removed - using only Notion submission

@app.route('/success', methods=['GET', 'POST'])
def submission_success():
    """Display success page after form submission"""
    return render_template('submission_success.html')

# All dashboard and admin functionality removed - submissions go directly to Notion

# Enhanced Error handlers for security and UX
@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 error page with proper SEO"""
    log_security_event('Page Not Found', details=f'404 for URL: {request.url}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Custom 500 error handler"""
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

# No database tables needed - using Notion as database

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
