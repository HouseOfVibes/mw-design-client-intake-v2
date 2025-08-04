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

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
