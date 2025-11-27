"""
Flask Application for Face Attendance System - 4-Phase Workflow
Phase 1: Gateway, Phase 2: Admin Portal, Phase 3: Professor Portal, Phase 4: Smart Attendance
"""

from flask import Flask, render_template, Response, request, jsonify, session, redirect, url_for
from camera_engine import CameraEngine
import os
from functools import wraps
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Admin password (simple authentication)
ADMIN_PASSWORD = "admin123"

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
            return None
    return camera_engine


def require_session(f):
    """Decorator to require active class session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'course_code' not in session:
            return redirect(url_for('doctor_login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== PHASE 1: GATEWAY ====================

@app.route('/')
def index():
    """Main gateway page with dual portals"""
    return render_template('index.html')


# ==================== PHASE 2: ADMIN PORTAL ====================

@app.route('/admin_login')
def admin_login():
    """Admin login page"""
    return render_template('admin_login.html')


@app.route('/admin_auth', methods=['POST'])
def admin_auth():
    """Admin password authentication"""
    password = request.json.get('password', '')
    
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
    else:
        return jsonify({'success': False, 'message': 'Invalid password'}), 401


@app.route('/admin_dashboard')
@require_admin
def admin_dashboard():
    """Admin dashboard with student management"""
    return render_template('admin_dashboard.html')


@app.route('/api/get_all_students')
@require_admin
def get_all_students():
    """Get all registered students from Firebase"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'students': []}), 500
    
    try:
        students_ref = engine.db.collection('students')
        docs = students_ref.stream()
        
        students = []
        for doc in docs:
            data = doc.to_dict()
            students.append({
                'id': doc.id,
                'student_id': data.get('student_id', ''),
                'name': data.get('name', 'Unknown'),
                'registered_at': data.get('registered_at', None)
            })
        
        # Sort by registration date (newest first)
        students.sort(key=lambda x: x.get('registered_at') or '', reverse=True)
        
        return jsonify({'success': True, 'students': students, 'total': len(students)})
    except Exception as e:
        print(f"[Error] Failed to fetch students: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete_student/<student_id>', methods=['DELETE'])
@require_admin
def delete_student(student_id):
    """Delete a student from Firebase"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500
    
    try:
        # Delete from Firebase
        engine.db.collection('students').document(student_id).delete()
        
        # Invalidate cache
        engine.last_cache_update = 0
        
        print(f"[Admin] Deleted student: {student_id}")
        return jsonify({'success': True, 'message': f'Student {student_id} deleted successfully'})
    except Exception as e:
        print(f"[Error] Failed to delete student: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/get_session_count')
@require_admin
def get_session_count():
    """Get total number of attendance sessions"""
    engine = init_camera()
    if engine is None:
        return jsonify({'total': 0})
    
    try:
        # Count unique sessions (by timestamp date)
        attendance_ref = engine.db.collection('attendance')
        docs = attendance_ref.stream()
        
        sessions = set()
        for doc in docs:
            data = doc.to_dict()
            marked_at = data.get('marked_at', '')
            if marked_at:
                # Extract date part
                date_part = marked_at.split(' ')[0] if ' ' in marked_at else marked_at
                course = data.get('course_code', 'unknown')
                sessions.add(f"{date_part}_{course}")
        
        return jsonify({'total': len(sessions)})
    except Exception as e:
        print(f"[Error] Failed to count sessions: {e}")
        return jsonify({'total': 0})


@app.route('/api/add_course', methods=['POST'])
@require_admin
def add_course():
    """Add a new course to Firebase"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500
    
    data = request.json
    course_name = data.get('course_name', '').strip()
    course_code = data.get('course_code', '').strip()
    doctor_name = data.get('doctor_name', '').strip()
    password = data.get('password', '').strip()
    start_date = data.get('start_date', '').strip()
    total_lectures = data.get('total_lectures', '')
    class_capacity = data.get('class_capacity', '')
    
    if not all([course_name, course_code, doctor_name, password, start_date, total_lectures, class_capacity]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    try:
        total_lectures = int(total_lectures)
        class_capacity = int(class_capacity)
        if total_lectures <= 0 or class_capacity <= 0:
            return jsonify({'success': False, 'message': 'Total lectures and capacity must be positive'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid total lectures or capacity'}), 400
    
    try:
        # Convert start_date string to timestamp
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        
        course_data = {
            'course_name': course_name,
            'course_code': course_code,
            'doctor_name': doctor_name,
            'password': password,
            'start_date': start_date_obj,
            'total_lectures': total_lectures,
            'class_capacity': class_capacity,
            'created_at': datetime.now()
        }
        
        # Use course_code as document ID
        engine.db.collection('courses').document(course_code).set(course_data)
        
        print(f"[Admin] Created course: {course_code}")
        return jsonify({'success': True, 'message': f'Course {course_code} created successfully'})
    except Exception as e:
        print(f"[Error] Failed to create course: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/get_all_courses')
@require_admin
def get_all_courses():
    """Get all courses from Firebase"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'courses': []}), 500
    
    try:
        courses_ref = engine.db.collection('courses')
        docs = courses_ref.stream()
        
        courses = []
        for doc in docs:
            data = doc.to_dict()
            courses.append({
                'course_code': doc.id,
                'course_name': data.get('course_name', ''),
                'doctor_name': data.get('doctor_name', ''),
                'start_date': data.get('start_date'),
                'total_lectures': data.get('total_lectures', 0)
            })
        
        # Sort by course_code
        courses.sort(key=lambda x: x['course_code'])
        
        return jsonify({'success': True, 'courses': courses, 'total': len(courses)})
    except Exception as e:
        print(f"[Error] Failed to fetch courses: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete_course/<course_code>', methods=['DELETE'])
@require_admin
def delete_course(course_code):
    """Delete a course from Firebase"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500
    
    try:
        # Delete from Firebase
        engine.db.collection('courses').document(course_code).delete()
        
        print(f"[Admin] Deleted course: {course_code}")
        return jsonify({'success': True, 'message': f'Course {course_code} deleted successfully'})
    except Exception as e:
        print(f"[Error] Failed to delete course: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin_logout')
def admin_logout():
    """Logout from admin panel"""
    session.pop('is_admin', None)
    return redirect(url_for('index'))


# ==================== PHASE 3: DOCTOR PORTAL (COURSE-BASED) ====================

@app.route('/doctor_login')
def doctor_login():
    """Doctor login page with course selection"""
    return render_template('doctor_login.html')


@app.route('/api/get_courses_list')
def get_courses_list():
    """Get all courses for dropdown (no auth required)"""
    engine = init_camera()
    if engine is None:
        return jsonify({'courses': []})
    
    try:
        courses_ref = engine.db.collection('courses')
        docs = courses_ref.stream()
        
        courses = []
        for doc in docs:
            data = doc.to_dict()
            courses.append({
                'course_code': doc.id,
                'course_name': data.get('course_name', ''),
                'doctor_name': data.get('doctor_name', '')
            })
        
        # Sort by course_name
        courses.sort(key=lambda x: x['course_name'])
        
        return jsonify({'courses': courses})
    except Exception as e:
        print(f"[Error] Failed to fetch courses: {e}")
        return jsonify({'courses': []})


@app.route('/doctor_auth', methods=['POST'])
def doctor_auth():
    """Verify course password and start session"""
    data = request.json
    course_code = data.get('course_code', '').strip()
    password = data.get('password', '').strip()
    
    if not all([course_code, password]):
        return jsonify({'success': False, 'message': 'Course and password required'}), 400
    
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'System not initialized'}), 500
    
    try:
        # Get course from Firebase
        course_ref = engine.db.collection('courses').document(course_code)
        course_doc = course_ref.get()
        
        if not course_doc.exists:
            return jsonify({'success': False, 'message': 'Course not found'}), 404
        
        course_data = course_doc.to_dict()
        
        # Verify password
        if course_data.get('password') != password:
            return jsonify({'success': False, 'message': 'Invalid password'}), 401
        
        # Store course info in session
        session['course_code'] = course_code
        session['course_name'] = course_data.get('course_name')
        session['doctor_name'] = course_data.get('doctor_name')
        session['start_date'] = course_data.get('start_date')
        session['total_lectures'] = course_data.get('total_lectures')
        session['class_capacity'] = course_data.get('class_capacity', 0)
        
        print(f"[Doctor] Logged into course: {course_code}")
        return jsonify({'success': True, 'redirect': url_for('course_stats')})
        
    except Exception as e:
        print(f"[Error] Doctor authentication failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/course_stats')
@require_session
def course_stats():
    """Course analytics dashboard before starting attendance"""
    course_code = session.get('course_code')
    class_capacity = session.get('class_capacity', 0)
    
    # Calculate current week
    start_date = session.get('start_date')
    current_week = 1
    start_dt = None
    if start_date:
        try:
            if hasattr(start_date, 'seconds'):
                # Firestore timestamp
                start_dt = datetime.fromtimestamp(start_date.seconds)
            else:
                start_dt = start_date
            
            days_diff = (datetime.now() - start_dt).days
            current_week = max(1, (days_diff // 7) + 1)
        except Exception as e:
            print(f"[Error] Week calculation failed: {e}")
    
    # Fetch and analyze attendance history
    engine = init_camera()
    total_attendance = 0
    weekly_history = []
    
    if engine and start_dt:
        try:
            attendance_ref = engine.db.collection('attendance')
            docs = attendance_ref.where('course_code', '==', course_code).stream()
            
            # Group by week
            weeks_data = {}
            for doc in docs:
                data = doc.to_dict()
                marked_at = data.get('timestamp')
                
                if marked_at and hasattr(marked_at, 'seconds'):
                    marked_dt = datetime.fromtimestamp(marked_at.seconds)
                    days_since_start = (marked_dt - start_dt).days
                    week_num = (days_since_start // 7) + 1
                    
                    if week_num not in weeks_data:
                        weeks_data[week_num] = set()
                    
                    # Track unique students per week
                    student_id = data.get('student_id')
                    if student_id:
                        weeks_data[week_num].add(student_id)
            
            # Build weekly history list
            for week_num in sorted(weeks_data.keys()):
                present_count = len(weeks_data[week_num])
                absent_count = max(0, class_capacity - present_count)
                weekly_history.append({
                    'week': week_num,
                    'present': present_count,
                    'absent': absent_count
                })
                total_attendance += present_count
            
        except Exception as e:
            print(f"[Error] Failed to fetch attendance history: {e}")
    
    # Calculate remaining lectures
    total_lectures = session.get('total_lectures', 0)
    remaining_lectures = max(0, total_lectures - current_week)
    
    # Calculate overall stats
    total_present = sum(w['present'] for w in weekly_history)
    total_absent = (class_capacity * len(weekly_history)) - total_present if weekly_history else 0
    
    return render_template('course_stats.html',
                         course_code=session.get('course_code'),
                         course_name=session.get('course_name'),
                         doctor_name=session.get('doctor_name'),
                         current_week=current_week,
                         total_lectures=total_lectures,
                         remaining_lectures=remaining_lectures,
                         class_capacity=class_capacity,
                         total_present=total_present,
                         total_absent=total_absent,
                         weekly_history=weekly_history)


# ==================== PHASE 4: SMART ATTENDANCE ====================

@app.route('/start_attendance_session', methods=['POST'])
@require_session
def start_attendance_session():
    """Start attendance session from course stats"""
    # Set session start time and default duration
    session['session_start'] = time.time()
    session['lecture_duration'] = 90  # Default 90 minutes
    
    return jsonify({'success': True, 'redirect': url_for('attendance')})


@app.route('/attendance')
@require_session
def attendance():
    """Smart attendance tracking page with countdown timer"""
    # Initialize camera in attendance mode
    engine = init_camera()
    if engine:
        engine.stop_camera()  # Stop if already running
        engine.reset_session()  # Reset attendance for new session
        engine.start_camera(mode='attendance')
    
    return render_template('attendance.html',
                         doctor_name=session.get('doctor_name'),
                         course_name=session.get('course_name'),
                         course_code=session.get('course_code'),
                         duration=session.get('lecture_duration', 90),
                         start_time=session.get('session_start', time.time()))


@app.route('/register')
def register():
    """Student registration page (can be accessed from admin or professor)"""
    # Initialize camera in registration mode
    engine = init_camera()
    if engine:
        engine.stop_camera()  # Stop if already running
        engine.start_camera(mode='registration')
    
    return render_template('register.html')


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
def get_recognized_students():
    """Get list of recognized students in current session (only NEW ones)"""
    engine = init_camera()
    if engine is None:
        return jsonify({'students': []})
    
    # Get recognized students
    recognized = engine.recognized_students
    
    # Format for response - only return students not yet in attendance_marked
    students = []
    for student_id, info in recognized.items():
        students.append({
            'student_id': student_id,
            'name': info['name'],
            'timestamp': time.strftime('%H:%M:%S', time.localtime(info['timestamp'])),
            'is_marked': student_id in engine.attendance_marked
        })
    
    # Sort by timestamp (newest first)
    students.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({'students': students})


@app.route('/api/mark_attendance', methods=['POST'])
def api_mark_attendance():
    """Mark attendance for recognized students (auto-called from frontend)"""
    if 'course_code' not in session:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
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
    
    # Store course info before clearing session
    is_admin = session.get('is_admin', False)
    has_course = 'course_code' in session
    
    # For course users, preserve course session to show stats
    course_code = session.get('course_code')
    course_name = session.get('course_name')
    doctor_name = session.get('doctor_name')
    start_date = session.get('start_date')
    total_lectures = session.get('total_lectures')
    class_capacity = session.get('class_capacity')
    
    # Clear only session-specific data
    session.pop('session_start', None)
    session.pop('lecture_duration', None)
    
    if is_admin:
        return redirect(url_for('admin_dashboard'))
    elif has_course:
        # Redirect to course stats to see final attendance
        return redirect(url_for('course_stats'))
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
