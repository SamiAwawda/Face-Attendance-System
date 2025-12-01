"""
High-Performance Camera Engine for Face Attendance System
Uses MediaPipe for face detection and DeepFace for face recognition
"""

import cv2
import mediapipe as mp
import numpy as np
from deepface import DeepFace
import threading
import time
from typing import Optional, List, Dict, Tuple
import firebase_admin
from firebase_admin import credentials, firestore


class CameraEngine:
    """
    Camera engine with dual modes:
    - Registration Mode: For capturing and encoding faces
    - Attendance Mode: For real-time face recognition
    """
    
    def __init__(self, firebase_config_path: str = "firebase_config.json"):
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range (< 2m), 1 for full-range
            min_detection_confidence=0.5
        )
        
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        
        # Camera state
        self.camera = None
        self.is_running = False
        self.lock = threading.Lock()
        self.current_frame = None
        self.mode = "registration"  # "registration" or "attendance"
        
        # Attendance tracking
        self.recognized_students = {}  # {student_id: {name, timestamp}}
        self.attendance_marked = set()  # Set of student IDs already marked in this session
        self.students_cache = []  # Cache of students from Firebase
        self.last_cache_update = 0
        self.cache_lifetime = 60  # Refresh cache every 60 seconds
        
        # Performance optimization
        self.frame_skip = 2  # Process every Nth frame
        self.frame_count = 0
        
    def start_camera(self, mode: str = "registration"):
        """Start the camera in specified mode"""
        self.mode = mode
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.is_running = True
        
        # Load students cache for attendance mode
        if mode == "attendance":
            self._update_students_cache()
    
    def stop_camera(self):
        """Stop the camera and release resources"""
        self.is_running = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def _update_students_cache(self):
        """Update the local cache of students from Firebase"""
        current_time = time.time()
        if current_time - self.last_cache_update < self.cache_lifetime:
            return
        
        try:
            students_ref = self.db.collection('students')
            docs = students_ref.stream()
            self.students_cache = []
            
            for doc in docs:
                data = doc.to_dict()
                if 'embedding' in data and data['embedding']:
                    self.students_cache.append({
                        'id': doc.id,
                        'name': data.get('name', 'Unknown'),
                        'student_id': data.get('student_id', ''),
                        'embedding': np.array(data['embedding'])
                    })
            
            self.last_cache_update = current_time
            print(f"[Cache] Loaded {len(self.students_cache)} students")
        except Exception as e:
            print(f"[Error] Failed to update students cache: {e}")
    
    def get_frame(self) -> Optional[bytes]:
        """
        Get the current frame with face detection overlay
        Returns JPEG-encoded frame for streaming
        """
        if not self.is_running or self.camera is None:
            return None
        
        success, frame = self.camera.read()
        if not success:
            return None
        
        # Frame skipping for performance
        self.frame_count += 1
        if self.frame_count % self.frame_skip != 0:
            # Return cached frame
            if self.current_frame is not None:
                return self.current_frame
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        results = self.face_detection.process(rgb_frame)
        
        # Draw bounding boxes
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                h, w, _ = frame.shape
                
                # Calculate bounding box coordinates
                x = int(bboxC.xmin * w)
                y = int(bboxC.ymin * h)
                box_w = int(bboxC.width * w)
                box_h = int(bboxC.height * h)
                
                # In attendance mode, try to recognize the face
                if self.mode == "attendance":
                    name_label, status = self._recognize_face(frame, x, y, box_w, box_h)
                    
                    # Color-coded boxes based on status
                    if status == "new":
                        color = (0, 255, 0)  # GREEN for new students
                        name_label = name_label
                    elif status == "already_marked":
                        color = (0, 215, 255)  # GOLD for already marked
                        name_label = f"{name_label} ✓"
                    else:
                        color = (0, 255, 255)  # CYAN for unknown
                        name_label = "Unknown"
                else:
                    name_label = "Face Detected"
                    color = (0, 255, 0)
                
                # Draw futuristic bounding box
                thickness = 2
                cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), color, thickness)
                
                # Draw corners for cyberpunk effect
                corner_length = 20
                # Top-left corner
                cv2.line(frame, (x, y), (x + corner_length, y), color, thickness + 1)
                cv2.line(frame, (x, y), (x, y + corner_length), color, thickness + 1)
                # Top-right corner
                cv2.line(frame, (x + box_w, y), (x + box_w - corner_length, y), color, thickness + 1)
                cv2.line(frame, (x + box_w, y), (x + box_w, y + corner_length), color, thickness + 1)
                # Bottom-left corner
                cv2.line(frame, (x, y + box_h), (x + corner_length, y + box_h), color, thickness + 1)
                cv2.line(frame, (x, y + box_h), (x, y + box_h - corner_length), color, thickness + 1)
                # Bottom-right corner
                cv2.line(frame, (x + box_w, y + box_h), (x + box_w - corner_length, y + box_h), color, thickness + 1)
                cv2.line(frame, (x + box_w, y + box_h), (x + box_w, y + box_h - corner_length), color, thickness + 1)
                
                # Draw name label
                label_y = max(y - 10, 20)
                cv2.putText(frame, name_label, (x, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return None
        
        self.current_frame = buffer.tobytes()
        return self.current_frame
    
    def _recognize_face(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> tuple:
        """
        Recognize a face using DeepFace and Firebase embeddings
        Returns tuple: (name, status) where status is "new", "already_marked", or "unknown"
        """
        try:
            # Update cache if needed
            self._update_students_cache()
            
            if not self.students_cache:
                return ("Unknown", "unknown")
            
            # Extract face region with padding
            padding = 20
            h_img, w_img = frame.shape[:2]
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w_img, x + w + padding)
            y2 = min(h_img, y + h + padding)
            
            face_img = frame[y1:y2, x1:x2]
            
            if face_img.size == 0:
                return ("Unknown", "unknown")
            
            # Generate embedding using DeepFace
            embedding_objs = DeepFace.represent(
                img_path=face_img,
                model_name='Facenet512',
                enforce_detection=False
            )
            
            if not embedding_objs:
                return ("Unknown", "unknown")
            
            current_embedding = np.array(embedding_objs[0]['embedding'])
            
            # Compare with all stored embeddings using cosine similarity
            best_match = None
            best_similarity = 0.6  # Threshold for recognition
            
            for student in self.students_cache:
                stored_embedding = student['embedding']
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(current_embedding, stored_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = student
            
            if best_match:
                student_id = best_match['student_id']
                name = best_match['name']
                
                # Check if already marked in this session
                status = "already_marked" if student_id in self.attendance_marked else "new"
                
                # Add to recognized students
                self.recognized_students[student_id] = {
                    'name': name,
                    'timestamp': time.time()
                }
                
                return (name, status)
            
        except Exception as e:
            print(f"[Error] Recognition failed: {e}")
        
        return ("Unknown", "unknown")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def capture_face(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Capture a face from the current frame
        Returns (face_image, embedding) or None if no face detected
        """
        if not self.is_running or self.camera is None:
            return None
        
        success, frame = self.camera.read()
        if not success:
            return None
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        results = self.face_detection.process(rgb_frame)
        
        if not results.detections:
            return None
        
        # Get the first detected face
        detection = results.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        h, w, _ = frame.shape
        
        # Calculate bounding box with padding
        padding = 30
        x = max(0, int(bboxC.xmin * w) - padding)
        y = max(0, int(bboxC.ymin * h) - padding)
        box_w = min(w - x, int(bboxC.width * w) + 2 * padding)
        box_h = min(h - y, int(bboxC.height * h) + 2 * padding)
        
        # Extract face region
        face_img = frame[y:y + box_h, x:x + box_w]
        
        if face_img.size == 0:
            return None
        
        try:
            # Generate embedding using DeepFace
            embedding_objs = DeepFace.represent(
                img_path=face_img,
                model_name='Facenet512',
                enforce_detection=False
            )
            
            if not embedding_objs:
                return None
            
            embedding = np.array(embedding_objs[0]['embedding'])
            return (face_img, embedding)
            
        except Exception as e:
            print(f"[Error] Face capture failed: {e}")
            return None
    
    def register_student(self, name: str, student_id: str, embedding: np.ndarray) -> bool:
        """
        Register a new student to Firebase
        Returns True on success, False otherwise
        """
        try:
            student_data = {
                'name': name,
                'student_id': student_id,
                'embedding': embedding.tolist(),
                'registered_at': firestore.SERVER_TIMESTAMP
            }
            
            # Use student_id as document ID for easy lookup
            self.db.collection('students').document(student_id).set(student_data)
            
            # Invalidate cache
            self.last_cache_update = 0
            
            print(f"[Success] Registered student: {name} ({student_id})")
            return True
            
        except Exception as e:
            print(f"[Error] Failed to register student: {e}")
            return False
    
    def mark_attendance(self, student_id: str, session_info: Dict) -> bool:
        """
        Mark attendance for a student in the current session
        Returns True if attendance was marked, False if already marked or error
        """
        # Check if already marked in this session
        if student_id in self.attendance_marked:
            return False
        
        try:
            # Get student info
            student_ref = self.db.collection('students').document(student_id)
            student_doc = student_ref.get()
            
            if not student_doc.exists:
                return False
            
            student_data = student_doc.to_dict()
            
            # Create attendance record
            attendance_data = {
                'student_id': student_id,
                'name': student_data.get('name', 'Unknown'),
                'doctor_name': session_info.get('doctor_name', ''),
                'course_name': session_info.get('course_name', ''),
                'course_code': session_info.get('course_code', ''),
                'timestamp': firestore.SERVER_TIMESTAMP,
                'marked_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'lecture_date': time.strftime('%Y-%m-%d')  # Current date as string for standardized querying
            }
            
            # Add to attendance collection
            self.db.collection('attendance').add(attendance_data)
            
            # Mark as attended in this session
            self.attendance_marked.add(student_id)
            
            print(f"[Attendance] Marked for: {student_data.get('name')} ({student_id})")
            return True
            
        except Exception as e:
            print(f"[Error] Failed to mark attendance: {e}")
            return False
    
    def get_session_attendance(self) -> List[Dict]:
        """Get all attendance records for the current session"""
        result = []
        for student_id in self.attendance_marked:
            if student_id in self.recognized_students:
                info = self.recognized_students[student_id]
                result.append({
                    'student_id': student_id,
                    'name': info['name'],
                    'timestamp': info['timestamp']
                })
        return result
    
    def reset_session(self):
        """Reset the attendance session"""
        self.attendance_marked.clear()
        self.recognized_students.clear()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_camera()
        if hasattr(self, 'face_detection'):
            self.face_detection.close()
