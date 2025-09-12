from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(255))
    website = db.Column(db.String(255))
    products_services = db.Column(db.Text)
    brand_story = db.Column(db.Text)
    usp = db.Column(db.Text)
    company_size = db.Column(db.String(255))
    social_media = db.Column(db.String(255))
    follower_counts = db.Column(db.String(255))
    management = db.Column(db.String(255))
    goals = db.Column(db.Text)  # Store as JSON string
    kpi = db.Column(db.String(255))
    paid_ads = db.Column(db.String(255))
    timeline = db.Column(db.String(255))
    demographics = db.Column(db.Text)
    problems_solutions = db.Column(db.Text)
    brand_voice = db.Column(db.String(255))
    content_tone = db.Column(db.String(255))
    platforms = db.Column(db.Text)  # Store as JSON string
    management_type = db.Column(db.String(255))
    existing_content = db.Column(db.String(255))
    content_writing = db.Column(db.String(255))
    brand_colors = db.Column(db.String(255))
    brand_fonts = db.Column(db.String(255))
    logo_graphics = db.Column(db.String(255))
    competitors = db.Column(db.Text)
    inspiration = db.Column(db.Text)
    budget = db.Column(db.String(255))
    launch_timeline = db.Column(db.String(255))
    content_provision = db.Column(db.String(255))
    posting_frequency = db.Column(db.String(255))
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    additional_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # New comprehensive form fields
    slogan = db.Column(db.Text)
    social_handles = db.Column(db.Text)
    social_management = db.Column(db.String(255))
    kpis = db.Column(db.Text)
    ideal_customer = db.Column(db.Text)
    brand_words = db.Column(db.Text)
    posting_approach = db.Column(db.String(255))
    content_availability = db.Column(db.String(255))
    industry = db.Column(db.String(255))
    logo_status = db.Column(db.String(255))
    start_date = db.Column(db.String(255))
    approval_level = db.Column(db.String(255))
    inspiration_accounts = db.Column(db.Text)
    social_challenges = db.Column(db.Text)
    questions_about_services = db.Column(db.Text)
    
    # New service-specific fields
    services_needed = db.Column(db.Text)  # Store as JSON string
    photography_type = db.Column(db.Text)  # Store as JSON string
    photography_location = db.Column(db.String(255))
    photography_timeline = db.Column(db.String(255))
    brand_services = db.Column(db.Text)  # Store as JSON string
    brand_stage = db.Column(db.String(255))
    brand_priority = db.Column(db.String(255))
    marketing_services = db.Column(db.Text)  # Store as JSON string
    project_urgency = db.Column(db.String(255))
    current_challenges = db.Column(db.Text)
    success_measurement = db.Column(db.Text)
    
    # Notion integration fields
    notion_page_id = db.Column(db.String(255))
    synced_to_notion = db.Column(db.Boolean, default=False)
    notion_sync_error = db.Column(db.Text)
    last_notion_sync = db.Column(db.DateTime)
    
    # Admin workflow fields
    status = db.Column(db.String(50), default='New')
    priority = db.Column(db.String(20), default='Medium')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    internal_notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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
            try:
                import json
                goals_list = json.loads(self.goals) if isinstance(self.goals, str) else self.goals
                goals_text = "\n".join([f"• {goal}" for goal in goals_list[:10]])  # Limit for Notion
                properties["Goals"] = {
                    "rich_text": [{"text": {"content": goals_text[:2000]}}]
                }
            except (json.JSONDecodeError, TypeError):
                properties["Goals"] = {
                    "rich_text": [{"text": {"content": str(self.goals)[:2000]}}]
                }
        
        if self.platforms:
            try:
                import json
                platforms_list = json.loads(self.platforms) if isinstance(self.platforms, str) else self.platforms
                # Notion multi-select has limits
                platform_names = [p for p in platforms_list[:10] if len(str(p)) <= 100]
                if platform_names:
                    properties["Platforms"] = {
                        "multi_select": [{"name": str(platform)} for platform in platform_names]
                    }
            except (json.JSONDecodeError, TypeError):
                properties["Platforms"] = {
                    "rich_text": [{"text": {"content": str(self.platforms)[:2000]}}]
                }
        
        return properties

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
