from flask import Flask, render_template, request, jsonify, url_for, redirect
from datetime import datetime
import qrcode
import json
import os
import base64
from io import BytesIO
import logging
from werkzeug.utils import secure_filename

try:
    from flask_socketio import SocketIO, emit
except ImportError:
    raise ImportError(
        "Flask-SocketIO is not installed. Please install it by running:\n"
        "    pip install flask-socketio\n"
        "or check your virtual environment."
    )

# Configure logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create base directory path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['DATA_FOLDER'] = os.path.join(BASE_DIR, 'data')

socketio = SocketIO(app)

# Ensure required directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['DATA_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# JSON file paths
ATTENDANCE_FILE = os.path.join(app.config['DATA_FOLDER'], 'attendance.json')

def load_json_file(file_path, default=None):
    if default is None:
        default = []
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON file {file_path}: {str(e)}")
        return default

def save_json_file(file_path, data):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write with temporary file
        temp_path = file_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Atomic replace
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file {file_path}: {str(e)}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        lecture_name = request.form['lecture_name']
        date = request.form['date']
        time = request.form['time']
        
        # Create QR code data string with a link to the form
        qr_data = url_for('attendance_form', lecture_name=lecture_name, date=date, time=time, _external=True)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Create image and convert to base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        attendance_records = load_json_file(ATTENDANCE_FILE, [])
        filtered_records = [record for record in attendance_records if record['lecture_name'] == lecture_name and record['date'] == date and record['time'] == time]
        
        return render_template('teacher.html', qr_code=img_str, lecture_name=lecture_name, date=date, time=time, records=filtered_records, show_form=False)
    
    return render_template('teacher.html', records=[], show_form=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/attendance-form', methods=['GET', 'POST'])
def attendance_form():
    if request.method == 'POST':
        data = request.form
        photo = request.files['photo']
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        if not photo.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only PNG, JPG, JPEG allowed'
            }), 400

        # Save photo with secure filename including lecture, date, and time
        lecture_name = data['lecture_name']
        date = data['date']
        time = data['time']
        roll_no = data['roll_no']
        # Sanitize all parts for filename
        def sanitize(s):
            return "".join(c for c in s if c.isalnum() or c in ('-', '_')).rstrip()
        filename = secure_filename(
            f"student_{sanitize(roll_no)}_{sanitize(lecture_name)}_{sanitize(date)}_{sanitize(time)}.jpg"
        )
        photo_path = os.path.join('uploads', filename)
        absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        photo.save(absolute_path)
        
        # Load attendance data
        attendance_records = load_json_file(ATTENDANCE_FILE, [])
        
        # Add new attendance record
        new_attendance = {
            'lecture_name': lecture_name,
            'date': date,
            'time': time,
            'student_name': data['name'],
            'roll_no': roll_no,
            'photo': photo_path
        }
        attendance_records.append(new_attendance)
        
        if save_json_file(ATTENDANCE_FILE, attendance_records):
            logging.debug(f"Emitting new attendance: {new_attendance}")
            socketio.emit('new_attendance', new_attendance, namespace='/')
            success_message = 'Attendance submitted successfully'
        else:
            success_message = 'Failed to save attendance data'
            
        return render_template('attendance_form.html', lecture_name=lecture_name, date=date, time=time, success_message=success_message)
    
    lecture_name = request.args.get('lecture_name')
    date = request.args.get('date')
    time = request.args.get('time')
    return render_template('attendance_form.html', lecture_name=lecture_name, date=date, time=time)

@app.route('/submit-attendance', methods=['POST'])
def submit_attendance():
    try:
        data = request.form
        photo = request.files['photo']
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        if not photo.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only PNG, JPG, JPEG allowed'
            }), 400

        # Save photo with secure filename including lecture, date, and time
        lecture_name = data['lecture_name']
        date = data['date']
        time = data['time']
        roll_no = data['roll_no']
        def sanitize(s):
            return "".join(c for c in s if c.isalnum() or c in ('-', '_')).rstrip()
        filename = secure_filename(
            f"student_{sanitize(roll_no)}_{sanitize(lecture_name)}_{sanitize(date)}_{sanitize(time)}.jpg"
        )
        photo_path = os.path.join('uploads', filename)
        absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        photo.save(absolute_path)
        
        # Load attendance data
        attendance_records = load_json_file(ATTENDANCE_FILE, [])
        
        # Add new attendance record
        new_attendance = {
            'lecture_name': lecture_name,
            'date': date,
            'time': time,
            'student_name': data['name'],
            'roll_no': roll_no,
            'photo': photo_path
        }
        attendance_records.append(new_attendance)
        
        if save_json_file(ATTENDANCE_FILE, attendance_records):
            logging.debug(f"Emitting new attendance: {new_attendance}")
            socketio.emit('new_attendance', new_attendance, namespace='/')
            return jsonify({'success': True, 'message': 'Attendance submitted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save attendance data'}), 500
            
    except Exception as e:
        logging.error(f"Error submitting attendance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin')
def admin():
    attendance_records = load_json_file(ATTENDANCE_FILE, [])
    lectures = {}
    for record in attendance_records:
        key = (record['lecture_name'], record['date'], record['time'])
        if key not in lectures:
            lectures[key] = []
        lectures[key].append(record)
    return render_template('admin.html', lectures=lectures)

@app.route('/show-attendance/<lecture_name>/<date>/<time>', methods=['GET', 'POST'])
def show_attendance(lecture_name, date, time):
    attendance_records = load_json_file(ATTENDANCE_FILE, [])
    if request.method == 'POST' and 'delete_roll_no' in request.form:
        delete_roll_no = request.form['delete_roll_no']
        new_records = []
        for record in attendance_records:
            if (
                record['lecture_name'] == lecture_name and
                record['date'] == date and
                record['time'] == time and
                record['roll_no'] == delete_roll_no
            ):
                # Delete the photo file if it exists
                photo_path = record.get('photo')
                if photo_path:
                    abs_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(photo_path))
                    if os.path.exists(abs_photo_path):
                        try:
                            os.remove(abs_photo_path)
                        except Exception as e:
                            logging.error(f"Failed to delete photo {abs_photo_path}: {e}")
                continue  # Skip adding this record
            new_records.append(record)
        save_json_file(ATTENDANCE_FILE, new_records)
        attendance_records = new_records
    filtered_records = [
        record for record in attendance_records
        if record['lecture_name'] == lecture_name and record['date'] == date and record['time'] == time
    ]
    return render_template('attendance.html', records=filtered_records)

# Add Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    logging.debug('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logging.debug('Client disconnected')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 2334))
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
