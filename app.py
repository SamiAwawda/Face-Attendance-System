"""
Flask Application for Face Attendance System
High-performance system using MediaPipe and DeepFace
"""

from flask import Flask, render_template, Response, request, jsonify, session, redirect, url_for
from camera_engine import CameraEngine
import os
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize camera engine
camera_engine = None


def init_camera():
    """Initialize the camera engine singleton"""
    global camera_engine
    if camera_engine is None:
        try:
            camera_engine = CameraEngine("firebase_config.json")
        except Exception as e:
            print(f"[Error] Failed to initialize camera engine: {e}")
            # Return None to allow app to start even without Firebase
            return None
    return camera_engine


def require_session(f):
    """Decorator to require active session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'doctor_name' not in session:
            return redirect(url_for('setup'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def setup():
    """Class setup page (landing page)"""
    return render_template('setup.html')


@app.route('/start_session', methods=['POST'])
def start_session():
    """Start a new class session"""
    data = request.form
    
    doctor_name = data.get('doctor_name', '').strip()
    course_name = data.get('course_name', '').strip()
    course_code = data.get('course_code', '').strip()
    
    if not all([doctor_name, course_name, course_code]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    # Store in session
    session['doctor_name'] = doctor_name
    session['course_name'] = course_name
    session['course_code'] = course_code
    session['session_start'] = time.time()
    
    return jsonify({'success': True, 'redirect': url_for('dashboard')})


@app.route('/dashboard')
@require_session
def dashboard():
    """Dashboard / Navigation hub"""
    return render_template('dashboard.html',
                         doctor_name=session.get('doctor_name'),
                         course_name=session.get('course_name'),
                         course_code=session.get('course_code'))


@app.route('/register')
@require_session
def register():
    """Student registration page"""
    # Initialize camera in registration mode
    engine = init_camera()
    if engine:
        engine.stop_camera()  # Stop if already running
        engine.start_camera(mode='registration')
    
    return render_template('register.html')


@app.route('/attendance')
@require_session
def attendance():
    """Attendance tracking page"""
    # Initialize camera in attendance mode
    engine = init_camera()
    if engine:
        engine.stop_camera()  # Stop if already running
        engine.reset_session()  # Reset attendance for new session
        engine.start_camera(mode='attendance')
    
    return render_template('attendance.html')


@app.route('/video_feed')
def video_feed():
    """Video streaming route for MJPEG"""
    def generate():
        engine = init_camera()
        if engine is None:
            # Return a blank frame if camera not initialized
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n'
            return
        
        while True:
            frame = engine.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/capture_face', methods=['POST'])
@require_session
def capture_face():
    """Capture face for registration"""
    data = request.json
    name = data.get('name', '').strip()
    student_id = data.get('student_id', '').strip()
    
    if not all([name, student_id]):
        return jsonify({'success': False, 'message': 'Name and ID are required'}), 400
    
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500
    
    # Capture face and embedding
    result = engine.capture_face()
    if result is None:
        return jsonify({'success': False, 'message': 'No face detected. Please position your face in the frame.'}), 400
    
    face_img, embedding = result
    
    # Register student to Firebase
    success = engine.register_student(name, student_id, embedding)
    
    if success:
        return jsonify({'success': True, 'message': f'Successfully registered {name}!'})
    else:
        return jsonify({'success': False, 'message': 'Failed to save to database'}), 500


@app.route('/api/get_recognized_students')
@require_session
def get_recognized_students():
    """Get list of recognized students in current session"""
    engine = init_camera()
    if engine is None:
        return jsonify({'students': []})
    
    # Get recognized students
    recognized = engine.recognized_students
    
    # Format for response
    students = []
    for student_id, info in recognized.items():
        students.append({
            'student_id': student_id,
            'name': info['name'],
            'timestamp': time.strftime('%H:%M:%S', time.localtime(info['timestamp']))
        })
    
    # Sort by timestamp (newest first)
    students.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({'students': students})


@app.route('/api/mark_attendance', methods=['POST'])
@require_session
def api_mark_attendance():
    """Mark attendance for recognized students"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500
    
    # Get session info
    session_info = {
        'doctor_name': session.get('doctor_name'),
        'course_name': session.get('course_name'),
        'course_code': session.get('course_code')
    }
    
    # Mark attendance for all recognized students who haven't been marked yet
    newly_marked = []
    for student_id in engine.recognized_students.keys():
        if student_id not in engine.attendance_marked:
            if engine.mark_attendance(student_id, session_info):
                newly_marked.append({
                    'student_id': student_id,
                    'name': engine.recognized_students[student_id]['name']
                })
    
    return jsonify({
        'success': True,
        'marked_count': len(newly_marked),
        'students': newly_marked
    })


@app.route('/api/session_stats')
@require_session
def session_stats():
    """Get current session statistics"""
    engine = init_camera()
    if engine is None:
        return jsonify({'total_recognized': 0, 'total_marked': 0})
    
    return jsonify({
        'total_recognized': len(engine.recognized_students),
        'total_marked': len(engine.attendance_marked)
    })


@app.route('/end_session')
def end_session():
    """End the current session"""
    engine = init_camera()
    if engine:
        engine.stop_camera()
        engine.reset_session()
    
    session.clear()
    return redirect(url_for('setup'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
