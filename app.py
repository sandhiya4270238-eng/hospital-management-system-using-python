from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, User, Patient, Doctor, Appointment, Bed, Bill
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ml_model import predict_disease

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    if not User.query.first():
        admin = User(
            name='Admin User',
            email='admin@hospital.com',
            password=generate_password_hash('admin123'),
            role='Admin'
        )
        db.session.add(admin)
        db.session.commit()
    
    if not Bed.query.first():
        beds_data = [
            Bed(bed_number='G101', type='General'),
            Bed(bed_number='G102', type='General'),
            Bed(bed_number='G103', type='General', status='Occupied'),
            Bed(bed_number='ICU01', type='ICU', status='Occupied'),
            Bed(bed_number='ICU02', type='ICU'),
            Bed(bed_number='E01', type='Emergency')
        ]
        db.session.bulk_save_objects(beds_data)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user.role)
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect_role_dashboard(user.role)
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user.role)
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Patient')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
            
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'Patient':
            patient = Patient(user_id=new_user.id)
            db.session.add(patient)
            db.session.commit()
        elif role == 'Doctor':
            doctor = Doctor(user_id=new_user.id, specialization='General Physician')
            db.session.add(doctor)
            db.session.commit()
            
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def redirect_role_dashboard(role):
    if role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'Doctor':
        return redirect(url_for('doctor_dashboard'))
    elif role == 'Patient':
        return redirect(url_for('patient_dashboard'))
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        return redirect(url_for('index'))
    stats = {
        'total_patients': User.query.filter_by(role='Patient').count(),
        'total_doctors': User.query.filter_by(role='Doctor').count(),
        'appointments_count': Appointment.query.count(),
        'available_beds': Bed.query.filter_by(status='Available').count()
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/beds')
@login_required
def manage_beds():
    if current_user.role != 'Admin':
        return redirect(url_for('index'))
    beds = Bed.query.all()
    return render_template('admin/beds.html', beds=beds)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'Doctor':
        return redirect(url_for('index'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.date, Appointment.time).all()
    from datetime import date
    today_appts = [a for a in appointments if a.date == date.today()]
    
    stats = {
        'today_patients': len(today_appts),
        'pending_appointments': len([a for a in appointments if a.status == 'Pending'])
    }
        
    return render_template('doctor/dashboard.html', appointments=today_appts, stats=stats)

@app.route('/appointment/<int:id>/update/<status>', methods=['POST'])
@login_required
def update_appointment(id, status):
    if current_user.role != 'Doctor':
        return redirect(url_for('index'))
    appt = Appointment.query.get_or_404(id)
    appt.status = status
    
    if status == 'Completed':
        # Generate a dummy bill upon completion
        bill = Bill(patient_id=appt.patient_id, amount=50.0, details=f'Consultation with Dr. {appt.doctor.user.name}')
        db.session.add(bill)
        
    db.session.commit()
    flash(f'Appointment marked as {status}', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'Patient':
        return redirect(url_for('index'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date, Appointment.time).all()
        
    return render_template('patient/dashboard.html', appointments=appointments)

@app.route('/patient/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role != 'Patient':
        return redirect(url_for('index'))
        
    doctors = Doctor.query.all()
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    from datetime import date, datetime
    today = date.today().isoformat()
    
    if request.method == 'POST':
        doc_id = request.form.get('doctor_id')
        appt_date_str = request.form.get('date')
        appt_time_str = request.form.get('time')
        
        appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
        appt_time = datetime.strptime(appt_time_str, '%H:%M').time()
        
        # Check for conflicts
        conflict = Appointment.query.filter_by(doctor_id=doc_id, date=appt_date, time=appt_time).first()
        if conflict:
            flash('This time slot is already booked for this doctor. Please select another.', 'error')
        else:
            new_appt = Appointment(patient_id=patient.id, doctor_id=doc_id, date=appt_date, time=appt_time, status='Pending')
            db.session.add(new_appt)
            db.session.commit()
            flash('Appointment successfully requested!', 'success')
            return redirect(url_for('patient_dashboard'))
            
    return render_template('patient/book.html', doctors=doctors, today=today)

@app.route('/patient/bills')
@login_required
def patient_bills():
    if current_user.role != 'Patient':
        return redirect(url_for('index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    bills = Bill.query.filter_by(patient_id=patient.id).order_by(Bill.date_issued.desc()).all()
    return render_template('patient/bills.html', bills=bills)

@app.route('/patient/predict', methods=['GET', 'POST'])
@login_required
def ai_predictor():
    if current_user.role != 'Patient':
        return redirect(url_for('index'))
        
    result = None
    if request.method == 'POST':
        selected_symptoms = request.form.getlist('symptoms')
        symptoms_dict = {sym: 1 for sym in selected_symptoms}
        result = predict_disease(symptoms_dict)
        
    return render_template('patient/predict.html', result=result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
