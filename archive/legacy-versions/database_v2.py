"""
Modern database configuration for FastAPI with SQLAlchemy 2.0
PostgreSQL support for Render deployment
"""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Fix for Render PostgreSQL URL format
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./mw_design_client_intake.db"
    logging.warning("Using SQLite for local development. Set DATABASE_URL for production.")

print(f"Database URL: {DATABASE_URL}")

# SQLAlchemy engine configuration
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration for local development
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL query logging
    )
else:
    # PostgreSQL configuration for production
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False  # Set to True for SQL query logging
    )

# Session configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db() -> Session:
    """
    Dependency function to get database session for FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    """
    try:
        # Import all models to ensure they're registered
        from models_v2 import Submission, User
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully")
        
        # Create default admin user if none exists
        create_default_admin()
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e

def create_default_admin():
    """
    Create default admin user for initial access
    """
    try:
        from models_v2 import User
        from passlib.context import CryptContext
        
        db = SessionLocal()
        
        # Check if any admin users exist
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        
        if not existing_admin:
            # Create password hasher
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Create default admin
            admin_user = User(
                username="admin",
                email="admin@mwdesign.agency",
                full_name="MW Design Studio Admin",
                password_hash=pwd_context.hash("mwdesign2024!"),  # Change this password!
                is_admin=True,
                is_active=True
            )
            
            db.add(admin_user)
            db.commit()
            
            print("✅ Default admin user created")
            print("   Username: admin")
            print("   Password: mwdesign2024!")
            print("   ⚠️  Please change the default password after first login!")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Failed to create default admin: {e}")

def get_db_stats():
    """
    Get basic database statistics for health checks
    """
    try:
        from models_v2 import Submission, User
        
        db = SessionLocal()
        
        stats = {
            "total_submissions": db.query(Submission).count(),
            "total_users": db.query(User).count(),
            "database_type": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite",
            "status": "healthy"
        }
        
        db.close()
        return stats
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def backup_database():
    """
    Create a simple backup of submissions data
    """
    try:
        from models_v2 import Submission
        import json
        from datetime import datetime
        
        db = SessionLocal()
        submissions = db.query(Submission).all()
        
        # Convert to JSON-serializable format
        backup_data = []
        for submission in submissions:
            data = {
                "id": submission.id,
                "business_name": submission.business_name,
                "website": submission.website,
                "contact_name": submission.contact_name,
                "email": submission.email,
                "phone": submission.phone,
                "products_services": submission.products_services,
                "brand_story": submission.brand_story,
                "usp": submission.usp,
                "company_size": submission.company_size,
                "budget": submission.budget,
                "goals": submission.goals,
                "platforms": submission.platforms,
                "timeline": submission.timeline,
                "demographics": submission.demographics,
                "problems_solutions": submission.problems_solutions,
                "brand_voice": submission.brand_voice,
                "content_tone": submission.content_tone,
                "brand_colors": submission.brand_colors,
                "brand_fonts": submission.brand_fonts,
                "competitors": submission.competitors,
                "inspiration": submission.inspiration,
                "additional_info": submission.additional_info,
                "status": submission.status,
                "priority": submission.priority,
                "created_at": submission.created_at.isoformat() if submission.created_at else None,
                "updated_at": submission.updated_at.isoformat() if submission.updated_at else None
            }
            backup_data.append(data)
        
        # Save backup file
        backup_filename = f"mw_design_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        db.close()
        
        print(f"✅ Database backup created: {backup_filename}")
        return backup_filename
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

# Test database connection
def test_connection():
    """
    Test database connection
    """
    try:
        db = SessionLocal()
        # Try a simple query
        db.execute("SELECT 1")
        db.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    # Test the database connection
    test_connection()
    
    # Initialize database
    init_db()
    
    # Show database stats
    stats = get_db_stats()
    print(f"📊 Database Stats: {stats}")
