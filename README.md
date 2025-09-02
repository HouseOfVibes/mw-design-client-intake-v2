# MW Design Studio - Enhanced Client Intake System

A comprehensive Flask-based web application for collecting social media client intake information, generating professional PDF summaries, managing client relationships, and integrating with Notion for seamless client portal management.

## ✨ Features

### **Client Experience**
- **Comprehensive Intake Form**: 29-question form covering business info, goals, audience, brand voice, platforms, and content strategy
- **📄 Instant PDF Reports**: Professional branded intake summaries using WeasyPrint
- **MW Design Studio Branding**: Beautiful gradient design with your brand colors
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile

### **Admin Dashboard**
- **Analytics Dashboard**: Overview stats, recent submissions, and sync status
- **🔍 Advanced Search & Filtering**: Find submissions by status, business name, contact, or email
- **Status Management**: Track submissions through your workflow (New → In Progress → Completed)
- **📝 Internal Notes**: Team collaboration with internal submission notes
- **CSV Export**: Export data for reporting or external tools

### **Integrations**
- **💬 Google Chat Notifications**: Instant team alerts when new forms are submitted
- **Notion Integration**: (Optional) Sync submissions to Notion database - currently disabled due to deployment optimization
- **CSV Export**: Export all submission data for external analysis
- **Graceful Degradation**: App works perfectly even if integrations are unavailable

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- (Optional) Notion workspace and integration token

### Installation

1. **Clone and setup:**
```bash
git clone https://github.com/your-username/mw-design-client-intake.git
cd mw-design-client-intake
pip install -r requirements.txt
```

2. **Environment setup (create `.env` file):**
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://username:password@localhost/dbname

# Google Chat Integration (Optional)
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/your-webhook-url

# Notion Integration (Optional - currently disabled)
# NOTION_TOKEN=secret_xxxxxxxxxxxxx
# NOTION_DB_ID=xxxxxxxxxx

# Email Settings (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

3. **Run the application:**
```bash
python app.py
```

4. **Access the application:**
- Client form: `http://localhost:5000`
- Admin dashboard: `http://localhost:5000/login`

## 🌐 Render Deployment

### One-Click Deploy
1. **Create Web Service** on render.com
2. **Connect your GitHub repository**
3. **Build & Start Commands:**
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn -c gunicorn.conf.py app:app`

### Environment Variables
```env
SECRET_KEY=your-random-secret-key
DATABASE_URL=(provided by Render PostgreSQL)
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/your-webhook-url (optional)
# NOTION_TOKEN=secret_xxxxxxxxxxxxx (currently disabled)
# NOTION_DB_ID=your-database-id (currently disabled)
```

## 💬 Google Chat Setup (Optional)

### 1. Create Google Chat Webhook
1. Open Google Chat and go to the space where you want notifications
2. Click the space name → "Apps & integrations" → "Add webhooks"
3. Name it "MW Design Studio Notifications"
4. Copy the webhook URL
5. Set the `GOOGLE_CHAT_WEBHOOK_URL` environment variable

### 2. Test Notifications
When forms are submitted, you'll receive rich notifications with:
- Business name and contact details
- Submission timestamp
- Direct links to manage the submission

## Notion Setup (Currently Disabled)

*Note: Notion integration is temporarily disabled to avoid deployment compilation issues. It can be re-enabled in future updates.*

### 1. Create Notion Database (For Future Use)
Create a database with these properties:
- **Business Name** (Title)
- **Contact Person** (Text)
- **Email** (Email)
- **Phone** (Phone)
- **Website** (URL)
- **Company Size** (Select: "1-10", "11-50", "51-200", "200+")
- **Budget** (Select: "$1,000-5,000", "$5,000-10,000", "$10,000-25,000", "$25,000+")
- **Status** (Select: "New", "Contacted", "In Progress", "Completed", "On Hold")
- **Priority** (Select: "Low", "Medium", "High", "Urgent")
- **Created** (Date)
- **Goals** (Text)
- **Platforms** (Multi-select: "Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "YouTube")
- **Products/Services** (Text)
- **Brand Story** (Text)
- **Target Demographics** (Text)
- **Brand Voice** (Select)
- **Content Tone** (Select)
- **Timeline** (Select)
- **Posting Frequency** (Select)
- **Internal Notes** (Text)

### 2. Create Integration
1. Go to [notion.com/my-integrations](https://www.notion.com/my-integrations)
2. Click "New integration"
3. Name it "MW Design Studio Intake"
4. Enable "Read content", "Update content", "Insert content"
5. Copy the **Internal Integration Token**

### 3. Share Database
1. Open your database in Notion
2. Click "..." → "Connections" → "Connect to" → Select your integration
3. Copy the database ID from the URL (32-character string)

## Project Structure

```
mw-design-client-intake/
├── app.py                           # Main Flask application with Notion integration
├── models.py                        # Database models
├── requirements.txt                 # Python dependencies
├── gunicorn.conf.py                # Production server config
├── README.md                        # This file
├── .gitignore                       # Git ignore rules
├── static/
│   └── style.css                    # MW Design Studio styles
└── templates/
    ├── index.html                   # Client intake form
    ├── admin_login.html             # Admin login
    ├── dashboard.html               # Enhanced admin dashboard
    ├── submissions_list.html        # All submissions with filters
    ├── view_submission.html         # Detailed submission view
    ├── client_intake_strategy.html  # Professional PDF template
    ├── login.html                   # User login
    └── register.html                # User registration
```

## Brand Colors

Your beautiful MW Design Studio palette:
- **Midnight Blue**: `#0D273E`
- **Deep Teal**: `#0A5068`
- **Cerulean Blue**: `#1A60B0`
- **Turquoise Splash**: `#229B7`
- **Royal Purple**: `#5E248C`
- **Imperial Gold**: `#B59643`
- **Charcoal Slate**: `#0E323C`
- **Light Mist**: `#BF5F7A`

## 🔌 API Endpoints

### Public
- `GET /` - Client intake form
- `POST /submit_form` - Process form submission (creates PDF + Notion page)

### Admin (Login Required)
- `GET /dashboard` - Admin dashboard with stats
- `GET /admin/submissions` - All submissions with search/filter
- `GET /submission/<id>` - Detailed submission view
- `POST /admin/submission/<id>/update-status` - Update submission status
- `GET /admin/export/csv` - Export submissions to CSV
- `POST /admin/notion/sync-all` - Sync all unsynced submissions (disabled)
- `POST /admin/notion/sync/<id>` - Sync single submission (disabled)

### System
- `GET /health` - Health check for monitoring

## 💾 Database Models

### Submission
Complete client intake data including:
- Business and contact information
- Social media goals and platforms
- Brand voice and content preferences
- Budget and timeline information
- **Admin fields**: status, priority, internal notes
- **Notion sync**: tracking fields for integration status

### User
Admin authentication with role-based access

## Workflow

1. **Client submits form** → Creates database record + sends Google Chat notification
2. **Team gets notified** → Instant Google Chat alert with client details
3. **Admin manages** → Login to dashboard, update status, add notes, track progress
4. **Export data** → CSV reports for analysis or external tools
5. **Future integration** → Notion sync can be re-enabled when needed

## Development

### Adding New Features
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (especially Notion integration)
5. Submit a pull request

### Testing Notion Integration
1. Create a test Notion database
2. Set up integration and get credentials
3. Submit test form submissions
4. Verify data appears correctly in Notion
5. Test manual sync functionality

## 📞 Support

**MW Design Studio Internal Use**
- Technical support: info@mwdesign.agency
- For Notion setup help: Check the detailed setup guide above
- For Render deployment issues: Check environment variables and logs

## 🔒 Security Notes

- Never commit `.env` files or secrets to git
- Use strong SECRET_KEY in production
- Notion tokens have specific permissions - don't overprivision
- Regular backup of PostgreSQL database recommended
- Monitor Render logs for any sync errors

---

**Ready to transform your client intake process with professional PDFs and seamless Notion integration!**
