"""
Vercel Serverless Function for MW Design Studio Intake Form
This handles form submission to Notion without requiring a database
"""
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Notion integration
try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False

# Initialize Flask app
# Vercel needs absolute paths
import sys
from pathlib import Path

# Get the base directory (parent of api folder)
if '/var/task' in sys.path[0]:  # Running on Vercel
    BASE_DIR = Path('/var/task')
else:  # Running locally
    BASE_DIR = Path(__file__).parent.parent

app = Flask(__name__,
            template_folder=str(BASE_DIR / 'templates'),
            static_folder=str(BASE_DIR / 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-for-vercel')
CORS(app)

# Notion configuration
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DB_ID = os.environ.get('NOTION_DATABASE_ID')

if NOTION_AVAILABLE and NOTION_TOKEN:
    notion_client = Client(auth=NOTION_TOKEN)
else:
    notion_client = None

def send_to_notion(form_data):
    """Send form data directly to Notion database"""
    if not notion_client or not NOTION_DB_ID:
        return False

    try:
        # Extract services needed array
        services_needed = form_data.getlist('services_needed') if hasattr(form_data, 'getlist') else form_data.get('services_needed', [])

        # Create Notion page properties
        properties = {
            "Name": {
                "title": [{"text": {"content": form_data.get('contact_name', '')}}]
            },
            "Business Name": {
                "rich_text": [{"text": {"content": form_data.get('business_name', '')}}]
            },
            "Email": {
                "email": form_data.get('email', '')
            },
            "Phone": {
                "phone_number": form_data.get('phone') if form_data.get('phone') else None
            },
            "Preferred Contact Method": {
                "select": {"name": form_data.get('preferred_contact', '')} if form_data.get('preferred_contact') else None
            },
            "Services Needed": {
                "multi_select": [{"name": service} for service in services_needed]
            },
            "Project Goals": {
                "rich_text": [{"text": {"content": form_data.get('project_goals', '')}}]
            },
            "Preferred Start Date": {
                "rich_text": [{"text": {"content": form_data.get('start_date', '')}}]
            },
            "Budget Range": {
                "select": {"name": form_data.get('budget_range', '')} if form_data.get('budget_range') else None
            },
            "Additional Information": {
                "rich_text": [{"text": {"content": form_data.get('additional_info', '')}}]
            },
            "Status": {
                "select": {"name": "New"}
            }
        }

        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}

        # Create the page
        response = notion_client.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties=properties
        )

        return True
    except Exception as e:
        print(f"Notion error: {str(e)}")
        return False

@app.route('/')
def home():
    """Render the intake form"""
    return render_template('index.html')

@app.route('/submit_form_new', methods=['POST'])
def submit_form():
    """Handle form submission"""
    try:
        # Send to Notion
        if send_to_notion(request.form):
            return redirect('/success')
        else:
            return jsonify({"error": "Failed to submit form"}), 500
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success():
    """Show success page"""
    return render_template('submission_success.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "MW Design Studio Intake Form"}), 200

# Vercel requires the app to be exposed as 'app'
# This allows Vercel to handle the serverless function properly