from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import pandas as pd
import os
import json
import logging
import base64
import numpy as np
import cv2
import face_recognition

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Paths to store data
ENCODINGS_FILE = 'data/encodings.json'
USERS_FILE = 'data/users.json'
STUDENTS_FILE = 'data/students.xlsx'
PREDEFINED_PASSWORD = 'Skynet'

# Load existing encodings
def load_encodings():
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, 'r') as f:
            encodings = json.load(f)
            return {k: np.array(v) for k, v in encodings.items()}
    return {}

# Save encodings
def save_encodings(encodings):
    encodings_to_save = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in encodings.items()}
    with open(ENCODINGS_FILE, 'w') as f:
        json.dump(encodings_to_save, f)

# Load users
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save user accounts
def save_user(username, password, role):
    users = load_users()
    users[username] = {'password': password, 'role': role}
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# Load existing students
def load_students():
    if os.path.exists(STUDENTS_FILE):
        return pd.read_excel(STUDENTS_FILE)
    return pd.DataFrame(columns=['Name', 'Student Code', 'City', 'State', 'Course'])

# Save student data
def save_student_data(data):
    df = load_students()
    existing_student = df[df['Student Code'] == data['Student Code']]
    if not existing_student.empty:
        df.loc[existing_student.index, ['Name', 'City', 'State', 'Course']] = (
            data['Name'], data['City'], data['State'], data['Course']
        )
        df.to_excel(STUDENTS_FILE, index=False)
        return True  # Indicate that the student data was updated
    else:
        new_data = pd.DataFrame([data])
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_excel(STUDENTS_FILE, index=False)
        return True  # Indicate that a new student was added

# Average face encodings
def average_encodings(existing_encoding, new_encoding):
    return [(existing + new) / 2 for existing, new in zip(existing_encoding, new_encoding)]

# Update encodings for a student
def update_student_encoding(student_code, new_encoding):
    encodings = load_encodings()
    if student_code in encodings:
        encodings[student_code] = average_encodings(encodings[student_code], new_encoding)
    else:
        encodings[student_code] = new_encoding
    save_encodings(encodings)

# Process Base64-encoded image data
def process_image_data(image_data):
    image_bytes = base64.b64decode(image_data)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            return redirect(url_for('professor_dashboard' if users[username]['role'] == 'professor' else 'student_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        predefined_password = request.form.get('predefined_password')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif role == 'professor' and predefined_password != PREDEFINED_PASSWORD:
            flash("Incorrect predefined password.", "danger")
        else:
            users = load_users()
            if username in users:
                flash("Username already exists.", "danger")
            else:
                save_user(username, password, role)
                flash(f"{username} registered successfully! You can now log in.", "success")
    return render_template('register.html')

@app.route('/professor_dashboard')
def professor_dashboard():
    return render_template('professor_dashboard.html')

@app.route('/view_attendance')
def view_attendance():
    return render_template('view_attendance.html')

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/enroll_students', methods=['GET', 'POST'])
def enroll_students():
    if request.method == 'POST':
        name = request.form.get('name')
        student_code = request.form.get('student_code')
        city = request.form.get('city')
        state = request.form.get('state')
        course = request.form.get('course')
        image_data = request.form.get('imageData')

        if name and student_code and city and state and course and image_data:
            student_data = {
                'Name': name,
                'Student Code': student_code,
                'City': city,
                'State': state,
                'Course': course
            }

            if save_student_data(student_data):
                image = process_image_data(image_data)
                face_encodings = face_recognition.face_encodings(image)

                if face_encodings:
                    update_student_encoding(student_code, face_encodings[0])
                    flash(f'Student {name} enrolled/updated successfully!', 'success')
                else:
                    flash('No face detected in the image!', 'danger')
            else:
                flash('Student code already exists!', 'danger')
        else:
            flash('All fields are required!', 'danger')

    return render_template('enroll_students.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000)
