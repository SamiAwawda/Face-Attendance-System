"""
Flask Application for Face Attendance System - 4-Phase Workflow
Phase 1: Gateway, Phase 2: Admin Portal, Phase 3: Professor Portal, Phase 4: Smart Attendance
"""

from flask import Flask, render_template, Response, request, jsonify, session, redirect, url_for, send_file
from camera_engine import CameraEngine
import os
from functools import wraps
import time
from datetime import datetime
import pandas as pd
from io import BytesIO

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
    lecture_time = data.get('lecture_time', '').strip()
    total_lectures = data.get('total_lectures', '')
    class_capacity = data.get('class_capacity', '')
    
    if not all([course_name, course_code, doctor_name, password, start_date, lecture_time, total_lectures, class_capacity]):
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
            'lecture_time': lecture_time,
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
    """Course analytics dashboard with detailed lecture timeline (1 Lecture = 1 Week)"""
    from datetime import timedelta
    
    course_code = session.get('course_code')
    class_capacity = session.get('class_capacity', 0)
    total_lectures = session.get('total_lectures', 0)
    
    # Parse start_date
    start_date = session.get('start_date')
    start_dt = None
    if start_date:
        try:
            if hasattr(start_date, 'seconds'):
                # Firestore timestamp - convert to naive datetime
                start_dt = datetime.fromtimestamp(start_date.seconds).replace(tzinfo=None)
            else:
                start_dt = start_date
                # Ensure it's naive if it has timezone info
                if hasattr(start_dt, 'tzinfo') and start_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=None)
        except Exception as e:
            print(f"[Error] Failed to parse start_date: {e}")
    
    # Calculate current week
    current_week = 1
    if start_dt:
        days_diff = (datetime.now() - start_dt).days
        current_week = max(1, (days_diff // 7) + 1)
    
    # Fetch attendance records from Firebase (query by lecture_date for each week)
    engine = init_camera()
    
    # Generate Lecture Timeline (1 Lecture = 1 Week)
    lecture_timeline = []
    total_present = 0
    total_absent = 0
    today = datetime.now().date()
    
    for i in range(total_lectures):
        # Calculate the lecture date (week i starts on start_date + i weeks)
        lecture_date = start_dt + timedelta(weeks=i) if start_dt else None
        
        # Determine if this lecture has occurred yet
        if lecture_date:
            lecture_date_only = lecture_date.date()
            lecture_date_str = lecture_date_only.strftime('%Y-%m-%d')
            
            # Query attendance for this specific lecture date
            week_present = 0
            week_absent = 0
            
            if engine:
                try:
                    attendance_ref = engine.db.collection('attendance')
                    # Query by course_code AND lecture_date
                    query = attendance_ref.where('course_code', '==', course_code).where('lecture_date', '==', lecture_date_str)
                    docs = list(query.stream())
                    week_present = len(docs)
                    week_absent = class_capacity - week_present
                except Exception as e:
                    print(f"[Error] Failed to query attendance for {lecture_date_str}: {e}")
            
            # Smart status logic
            if lecture_date_only < today:
                # Past lecture - always completed
                status = "Completed"
            elif lecture_date_only == today:
                # Today's lecture - check if attendance has been taken
                if week_present > 0:
                    status = "In Progress"
                else:
                    status = "Ready to Start"
            else:
                # Future lecture
                status = "Upcoming"
                week_present = '-'
                week_absent = '-'
        else:
            lecture_date_only = None
            week_present = '-'
            week_absent = '-'
            status = "Unknown"
        
        
        # Calculate attendance rate for completed/in-progress lectures
        if status in ['Completed', 'In Progress'] and week_present != '-':
            attendance_rate = round((week_present / class_capacity * 100), 1) if class_capacity > 0 else 0
        else:
            attendance_rate = None
        
        # Add to timeline
        lecture_timeline.append({
            'week_num': i + 1,  # Display as Week 1, Week 2, etc.
            'date': lecture_date_only,
            'status': status,
            'present': week_present,
            'absent': week_absent,
            'attendance_rate': attendance_rate
        })
        
        # Aggregate totals (only count completed lectures with actual numbers)
        if status == "Completed" and week_present != '-':
            total_present += week_present
            total_absent += week_absent
    
    # Calculate remaining lectures
    remaining_lectures = max(0, total_lectures - current_week)
    
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
                         lecture_timeline=lecture_timeline)


# ==================== PHASE 4: SMART ATTENDANCE ====================

@app.route('/start_attendance_session', methods=['POST'])
@require_session
def start_attendance_session():
    """Start attendance session from course stats with custom duration"""
    # Get custom duration from request (in minutes)
    data = request.json or {}
    custom_duration = data.get('duration', 90)  # Default 90 minutes
    
    # Validate duration (must be positive integer between 1 and 300 minutes)
    try:
        custom_duration = int(custom_duration)
        if custom_duration < 1 or custom_duration > 300:
            custom_duration = 90
    except (ValueError, TypeError):
        custom_duration = 90
    
    # Set session start time and custom duration
    session['session_start'] = time.time()
    session['lecture_duration'] = custom_duration
    
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


@app.route('/api/get_lecture_details/<course_code>/<date_str>')
def get_lecture_details(course_code, date_str):
    """Get list of students who attended a specific lecture"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'System not initialized'}), 500
    
    try:
        # Query attendance records for this course and specific date
        attendance_ref = engine.db.collection('attendance')
        # Use lecture_date field for direct querying
        query = attendance_ref.where('course_code', '==', course_code).where('lecture_date', '==', date_str)
        docs = query.stream()
        
        # Collect students
        students = []
        for doc in docs:
            data = doc.to_dict()
            # Extract time from marked_at field
            marked_at_str = data.get('marked_at', '')
            try:
                # Parse full timestamp and extract time
                marked_time = marked_at_str.split(' ')[1] if ' ' in marked_at_str else marked_at_str
            except:
                marked_time = 'N/A'
            
            students.append({
                'student_id': data.get('student_id', 'Unknown'),
                'name': data.get('name', 'Unknown'),
                'marked_at': marked_time
            })
        
        # Sort by time marked
        students.sort(key=lambda x: x['marked_at'])
        
        return jsonify({
            'success': True,
            'students': students,
            'total': len(students)
        })
        
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        print(f"[Error] Failed to fetch lecture details: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/export_attendance/<course_code>/<date_str>')
def export_attendance(course_code, date_str):
    """Export attendance list for a specific lecture to Excel"""
    engine = init_camera()
    if engine is None:
        return jsonify({'success': False, 'message': 'System not initialized'}), 500
    
    try:
        # Query attendance records for this course and specific date
        attendance_ref = engine.db.collection('attendance')
        query = attendance_ref.where('course_code', '==', course_code).where('lecture_date', '==', date_str)
        docs = query.stream()
        
        # Collect attendance data
        attendance_data = []
        for doc in docs:
            data = doc.to_dict()
            # Extract time from marked_at field
            marked_at_str = data.get('marked_at', '')
            try:
                marked_time = marked_at_str.split(' ')[1] if ' ' in marked_at_str else marked_at_str
            except:
                marked_time = 'N/A'
            
            attendance_data.append({
                'Student Name': data.get('name', 'Unknown'),
                'Student ID': data.get('student_id', 'Unknown'),
                'Time Marked': marked_time
            })
        
        # Sort by time marked
        attendance_data.sort(key=lambda x: x['Time Marked'])
        
        # Create pandas DataFrame
        df = pd.DataFrame(attendance_data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Attendance')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Attendance']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length
        
        output.seek(0)
        
        # Generate filename
        filename = f'Attendance_{course_code}_{date_str}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"[Error] Failed to export attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/end_session', methods=['GET', 'POST'])
def end_session():
    """End the current session with proper attendance finalization"""
    from datetime import timedelta
    
    engine = init_camera()
    
    # For POST requests (explicit end session), finalize attendance
    if request.method == 'POST':
        course_code = session.get('course_code')
        
        if engine and course_code:
            # Get session info for marking attendance
            session_info = {
                'doctor_name': session.get('doctor_name'),
                'course_name': session.get('course_name'),
                'course_code': course_code
            }
            
            # Mark any remaining recognized students who haven't been marked yet
            final_marked = []
            for student_id in engine.recognized_students.keys():
                if student_id not in engine.attendance_marked:
                    if engine.mark_attendance(student_id, session_info):
                        final_marked.append({
                            'student_id': student_id,
                            'name': engine.recognized_students[student_id]['name']
                        })
            
            # Identify current lecture based on today's date
            start_date = session.get('start_date')
            if start_date:
                try:
                    # Parse start_date
                    if hasattr(start_date, 'seconds'):
                        start_dt = datetime.fromtimestamp(start_date.seconds).replace(tzinfo=None)
                    else:
                        start_dt = start_date
                        if hasattr(start_dt, 'tzinfo') and start_dt.tzinfo is not None:
                            start_dt = start_dt.replace(tzinfo=None)
                    
                    # Calculate current lecture week
                    today = datetime.now()
                    days_since_start = (today - start_dt).days
                    current_lecture_week = (days_since_start // 7) + 1
                    
                    # Log session summary
                    print(f"[Session End] Course: {course_code}, Week: {current_lecture_week}")
                    print(f"[Session End] Total Marked: {len(engine.attendance_marked)}")
                    print(f"[Session End] Final Marked: {len(final_marked)}")
                    
                except Exception as e:
                    print(f"[Error] Failed to identify current lecture: {e}")
    
    # Stop camera and reset session
    if engine:
        engine.stop_camera()
        engine.reset_session()
    
    # Store course info before clearing session
    is_admin = session.get('is_admin', False)
    has_course = 'course_code' in session
    
    # Clear only session-specific data (preserve course session)
    session.pop('session_start', None)
    session.pop('lecture_duration', None)
    
    # Redirect appropriately
    if is_admin:
        return redirect(url_for('admin_dashboard'))
    elif has_course:
        # Redirect to course stats to see final attendance
        return redirect(url_for('course_stats'))
    
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
