# MW Design Studio - Client Intake System

A comprehensive Flask-based web application for collecting social media client intake information, generating professional PDF summaries, and managing client relationships.

## Features

- **Client Intake Form**: Comprehensive 29-question form covering business info, goals, audience, brand voice, platforms, and content strategy
- **PDF Generation**: Professional intake summaries using WeasyPrint
- **Admin Dashboard**: View, manage, and track client submissions
- **User Authentication**: Simple admin login system
- **Responsive Design**: Bootstrap-based UI with MW Design Studio branding
- **Database Storage**: PostgreSQL for data persistence

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- (Optional) Google Chat webhook for notifications

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/mw-design-client-intake.git
cd mw-design-client-intake
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create `.env` file):
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://username:password@localhost/dbname
ADMIN_PASSWORD=your-admin-password
```

4. Run the application:
```bash
python app.py
```

5. Visit `http://localhost:5000` for the client form or `http://localhost:5000/admin/login` for admin access

## Deployment on Render

1. **Create a new Web Service** on render.com
2. **Connect your GitHub repository**
3. **Use these settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -c gunicorn.conf.py app:app`
4. **Add environment variables:**
   - `SECRET_KEY`: Random secret key
   - `DATABASE_URL`: (Render will provide PostgreSQL)
   - `ADMIN_PASSWORD`: Your admin password

## Project Structure

```
mw-design-client-intake/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── requirements.txt            # Python dependencies
├── gunicorn.conf.py           # Production server config
├── README.md                   # This file
├── static/
│   └── style.css              # MW Design Studio styles
└── templates/
    ├── index.html             # Client intake form
    ├── admin_login.html       # Admin login page
    ├── dashboard.html         # Admin dashboard
    ├── view_submission.html   # View submission details
    ├── pdf_template.html      # Simple PDF template
    └── client_intake_strategy.html  # Professional PDF template
```

## Brand Colors

- Navy Blue: `#1E3A8A`
- Teal: `#20B2AA`
- Light Teal: `#4FD1C7`

## API Endpoints

- `GET /` - Client intake form
- `POST /submit_form` - Process form submission
- `GET /admin/login` - Admin login
- `GET /admin/dashboard` - View all submissions
- `GET /admin/submission/<id>` - View specific submission
- `GET /health` - Health check endpoint

## Database Models

### Submission
Stores client intake form data including:
- Business information
- Contact details
- Social media goals and platforms
- Brand voice and content preferences
- Budget and timeline information

### User
Simple user model for admin authentication

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Private - MW Design Studio Internal Use

## Support

For technical support, contact: info@mwdesign.agency
