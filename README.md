# SAMS - Student Attendance Management System

SAMS is a web-based Student Attendance Management System built with Flask. it allows teachers to generate unique QR codes for lectures, which students can scan to submit their attendance. The system includes photo verification to ensure the integrity of the attendance records.

## Features

- **Teacher Dashboard**: Generate QR codes for specific lectures, dates, and times.
- **QR Code Attendance**: Students scan a QR code to access the attendance form.
- **Photo Verification**: Students must upload a photo along with their name and roll number.
- **Real-time Updates**: Uses Socket.IO to provide real-time attendance updates to the teacher.
- **Admin Interface**: View all attendance records organized by lecture.
- **Record Management**: Ability to view and delete specific attendance entries.

## Tech Stack

- **Backend**: Python (Flask)
- **Real-time**: Flask-SocketIO
- **QR Generation**: `qrcode` library
- **Frontend**: HTML, CSS (Bootstrap), JavaScript
- **Data Storage**: JSON-based file storage

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ykbind/SAMS.git
   cd SAMS
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```
   The application will start on `http://0.0.0.0:2334` (or the port specified in the `PORT` environment variable).

## Project Structure

- `app.py`: The main Flask application containing all routes and logic.
- `templates/`: HTML templates for the teacher, student, and admin views.
- `static/`: Static assets like CSS, JS, and uploaded student photos.
- `data/`: Stores attendance records in `attendance.json`.
- `requirements.txt`: Python dependencies.

## Usage

1. **Teacher**: Navigate to `/teacher` to create a lecture session and display the QR code.
2. **Student**: Scan the QR code to be redirected to the attendance form. Fill in details and upload a photo.
3. **Admin**: Navigate to `/admin` to view aggregated attendance reports.

## License

[MIT License](LICENSE)
