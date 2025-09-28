# MW Design Studio - Modern Client Intake System v2.0

A cutting-edge client intake system built with **FastAPI**, **Tailwind CSS**, and **PostgreSQL**. Features beautiful MW Design Studio branding, multi-step forms, branded PDF generation, and a powerful admin dashboard.

![MW Design Studio](https://img.shields.io/badge/MW%20Design%20Studio-Client%20Intake%20v2.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue)

## 🚀 **What's New in v2.0**

### **Modern Tech Stack**
- **FastAPI** - High-performance Python web framework
- **Tailwind CSS** - Utility-first CSS framework for beautiful, responsive design
- **PostgreSQL** - Robust database with advanced features
- **Alpine.js** - Lightweight JavaScript framework for interactivity

### **Enhanced User Experience**
- **Multi-step Form** with progress indicator
- **Responsive Design** optimized for all devices
- **Real-time Validation** and error handling
- **Smooth Animations** and micro-interactions

### **Advanced Admin Features**
- **Analytics Dashboard** with charts and insights
- **Advanced Filtering** and search capabilities
- **Client Status Tracking** (New → Contacted → Won/Lost)
- **Bulk Operations** and data export
- **Email Integration** for client follow-ups

## ✨ **Key Features**

### **Client Experience**
- 🎨 **Beautiful MW Design Studio Branding** with gradient headers and logo
- 📋 **Comprehensive 6-Step Form** covering all aspects of social media strategy
- 📱 **Mobile-First Design** that works perfectly on any device
- ⚡ **Instant PDF Generation** with professional branded reports
- 🔄 **Real-time Progress Tracking** through form completion

### **Admin Dashboard**
- 📊 **Analytics & Insights** - Track submissions, conversion rates, and trends
- 🔍 **Advanced Search & Filtering** - Find clients quickly with smart filters
- 📈 **Client Pipeline Management** - Track leads through your sales process
- 📤 **Data Export** - CSV, Excel, and PDF export options
- 👥 **Team Collaboration** - Internal notes and assignment features

### **Technical Excellence**
- 🚀 **High Performance** - FastAPI delivers blazing-fast response times
- 🔒 **Security First** - Built-in CSRF protection, SQL injection prevention
- 📱 **API-First Design** - RESTful API with automatic documentation
- 🔄 **Auto-backup** - Scheduled database backups and export features
- 📈 **Scalable Architecture** - Handles growth from startup to enterprise

## 🎨 **MW Design Studio Brand Colors**

```css
:root {
    --mw-navy: #1E3A8A;      /* Primary Navy Blue */
    --mw-teal: #20B2AA;      /* Secondary Teal */
    --mw-light-teal: #4FD1C7; /* Accent Light Teal */
    --mw-gradient: linear-gradient(135deg, #1E3A8A 0%, #20B2AA 50%, #4FD1C7 100%);
}
```

## 🚀 **Quick Start Guide**

### **Option 1: One-Click Render Deployment**

1. **Fork this repository** to your GitHub account
2. **Connect to Render**: 
   - Go to [render.com](https://render.com)
   - Connect your GitHub account
   - Select this repository
3. **Auto-Deploy**: Render will automatically detect the `render.yaml` and deploy!

### **Option 2: Local Development**

```bash
# Clone the repository
git clone https://github.com/HouseOfVibes/mw-design-client-intake.git
cd mw-design-client-intake

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements_v2.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python database_v2.py

# Run the application
uvicorn main:app --reload

# Access the application
# Client Form: http://localhost:8000
# Admin Dashboard: http://localhost:8000/admin
# API Docs: http://localhost:8000/docs
```

## 🔧 **Environment Configuration**

Create a `.env` file in your project root:

```env
# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-super-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/mw_design_intake_v2
# For local development, leave empty to use SQLite

# Admin User (Created automatically)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@mwdesign.agency
ADMIN_PASSWORD=mwdesign2024!

# Email Settings (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Storage
UPLOAD_FOLDER=./uploads
MAX_FILE_SIZE=10MB
```

## 📁 **Project Structure**

```
mw-design-client-intake/
├── main.py                    # FastAPI application entry point
├── models_v2.py              # SQLAlchemy models & Pydantic schemas
├── database_v2.py            # Database configuration & utilities
├── pdf_generator.py          # Branded PDF generation
├── requirements_v2.txt       # Modern Python dependencies
├── render.yaml              # Render deployment configuration
├── static/
│   ├── images/
│   │   └── mw_logo.png       # MW Design Studio logo
│   └── css/
│       └── custom.css        # Additional custom styles
├── templates/
│   ├── index_v2.html         # Modern client intake form
│   ├── admin/
│   │   ├── dashboard.html    # Analytics dashboard
│   │   ├── submissions.html  # Submissions management
│   │   └── reports.html      # Reporting interface
│   └── pdf/
│       └── client_report.html # Branded PDF template
├── uploads/                  # Generated PDFs and files
└── migrations/              # Database migrations (future)
```

## 🎯 **Form Sections**

The client intake form is organized into 6 logical sections:

1. **Business Information** - Company details, contact info, budget
2. **Business Overview** - Products, services, brand story, USP
3. **Social Media Goals** - Objectives, KPIs, target platforms
4. **Target Audience** - Demographics, problems, solutions
5. **Brand & Content** - Voice, tone, colors, fonts, existing assets
6. **Competition & Strategy** - Competitors, inspiration, timeline

## 📊 **Admin Dashboard Features**

### **Analytics Overview**
- Total submissions and conversion rates
- Monthly growth trends
- Platform preference analysis
- Budget distribution charts
- Geographic distribution (if enabled)

### **Client Management**
- Lead scoring and prioritization
- Custom status tracking
- Internal notes and collaboration
- Follow-up reminders
- Document management

### **Reporting & Export**
- Custom date range reports
- CSV/Excel export for external tools
- Branded PDF client summaries
- Email campaign integration
- Performance metrics

## 🔒 **Security Features**

- **CSRF Protection** - Built-in cross-site request forgery protection
- **SQL Injection Prevention** - Parameterized queries with SQLAlchemy
- **Input Validation** - Pydantic models validate all form data
- **Rate Limiting** - Prevent spam and abuse
- **Secure Headers** - Security-focused HTTP headers
- **Environment-based Configuration** - Separate dev/prod settings

## 🚀 **Deployment Options**

### **Render.com (Recommended)**
- Free tier available
- Automatic HTTPS
- PostgreSQL database included
- GitHub integration
- Environment variable management

### **Alternative Platforms**
- **Heroku** - Classic platform with easy PostgreSQL
- **Railway** - Modern alternative to Heroku
- **DigitalOcean App Platform** - Simple container deployment
- **AWS/GCP/Azure** - Enterprise-grade cloud platforms

## 📈 **Performance & Scaling**

- **FastAPI Performance** - Up to 3x faster than Flask
- **Database Optimization** - Indexed queries and connection pooling
- **Static File CDN** - Tailwind CSS served from CDN
- **Efficient Rendering** - Server-side templates with client-side enhancements
- **Caching Strategy** - Redis integration ready for high traffic

## 🤝 **Contributing**

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 **Support & Contact**

**MW Design Studio**
- 🌐 Website: [mwdesign.agency](https://mwdesign.agency)
- 📧 Email: info@mwdesign.agency
- 💼 Business: Professional social media management & strategy

**Technical Support**
- 🐛 Issues: GitHub Issues page
- 📖 Documentation: This README and code comments
- 💬 Discussions: GitHub Discussions

## 📄 **License**

This project is proprietary to MW Design Studio. All rights reserved.

---

**Built with ❤️ by MW Design Studio for amazing clients worldwide.**

*Transform your social media presence with professional strategy and stunning design.*
