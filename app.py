import os
from flask import Flask, render_template, request, make_response, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from weasyprint import HTML
from models import db, Submission, User
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy', 'service': 'Content Strategy Studio'}

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
        flash('Form submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting form: {e}', 'danger')

    html = render_template('pdf_template.html', data=request.form)
    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=client_intake.pdf'
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
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    submissions = Submission.query.order_by(Submission.created_at.desc()).all()
    return render_template('dashboard.html', submissions=submissions)

@app.route('/submission/<int:submission_id>')
@login_required
def view_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    return render_template('view_submission.html', submission=submission)

@app.route('/download_pdf/<int:submission_id>')
@login_required
def download_pdf(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    html = render_template('pdf_template.html', data=submission)
    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=submission_{submission.id}.pdf'
    return response

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
