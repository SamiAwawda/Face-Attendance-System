# Face Attendance System

A high-performance face attendance system built with **MediaPipe** (BlazeFace) for face detection and **DeepFace** (Facenet512) for face recognition. Features a modern cyberpunk-themed dark UI with real-time processing.

## 🚀 Features

- **Ultra-Fast Face Detection**: MediaPipe BlazeFace for real-time performance
- **High-Accuracy Recognition**: DeepFace with Facenet512 model
- **Real-Time Attendance Tracking**: Live recognition and logging
- **Modern UI**: Cyberpunk dark theme with neon accents
- **Firebase Integration**: Cloud-based student database
- **Session Management**: Multi-session support with deduplication
- **Split-Screen Interface**: Simultaneous camera and form/log views

## 📋 Prerequisites

- Python 3.8 or higher
- Webcam
- Firebase project with Firestore enabled

## 🛠️ Installation

### 1. Clone or Create Project Directory

```bash
cd /home/sami/new
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Firebase Configuration

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Enable Firestore Database
4. Go to Project Settings → Service Accounts
5. Click "Generate New Private Key"
6. Save the downloaded JSON file as `firebase_config.json` in the project root

**Important**: The `firebase_config.json` file should be in the same directory as `app.py`.

## 🎯 Usage

### 1. Start the Application

```bash
python app.py
```

The server will start at `http://localhost:5000`

### 2. Workflow

#### Step 1: Class Setup (Landing Page)
- Navigate to `http://localhost:5000`
- Enter:
  - Doctor Name
  - Course Name
  - Course Code
- Click "Start Session"

#### Step 2: Dashboard
- Choose between:
  - **Register New Student**: Enroll students with face capture
  - **Start Attendance**: Begin real-time recognition

#### Step 3: Registration
- Position student's face in camera frame
- Wait for green detection box
- Fill in:
  - Student Name
  - Student ID
- Click "Capture Face & Register"
- Face embedding is saved to Firebase

#### Step 4: Attendance
- Students appear in front of camera
- System automatically recognizes faces
- Live log updates in real-time
- Click "Mark All Attendance" to save to Firebase
- Each student marked only once per session

## 📁 Project Structure

```
/home/sami/new/
├── app.py                  # Flask application
├── camera_engine.py        # MediaPipe + DeepFace logic
├── requirements.txt        # Python dependencies
├── firebase_config.json    # Firebase credentials (not included)
├── templates/
│   ├── layout.html         # Base template
│   ├── setup.html          # Class setup page
│   ├── dashboard.html      # Navigation hub
│   ├── register.html       # Registration page
│   └── attendance.html     # Attendance tracking
└── README.md              # This file
```

## 🔧 Configuration

### Camera Settings
Edit `camera_engine.py` to adjust camera resolution and FPS:

```python
self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
self.camera.set(cv2.CAP_PROP_FPS, 30)
```

### Recognition Threshold
Adjust similarity threshold in `camera_engine.py`:

```python
best_similarity = 0.6  # Higher = stricter matching (0.0 - 1.0)
```

### Performance Optimization
Adjust frame skipping for better performance:

```python
self.frame_skip = 2  # Process every Nth frame (higher = faster but less accurate)
```

## 🎨 UI Customization

The cyberpunk theme can be customized in `templates/layout.html`:

```css
:root {
    --neon-cyan: #00ffff;
    --neon-magenta: #ff00ff;
    --neon-blue: #0099ff;
    --neon-green: #00ff00;
    --dark-bg: #0a0a0f;
    --card-bg: #1a1a2e;
}
```

## 🔍 Troubleshooting

### Camera Not Working
- Check camera permissions
- Ensure no other application is using the camera
- Try changing camera index in `camera_engine.py`: `cv2.VideoCapture(1)`

### Firebase Errors
- Verify `firebase_config.json` is in the correct location
- Check Firestore rules allow read/write access
- Ensure Firebase Admin SDK is properly installed

### Slow Performance
- Increase `frame_skip` value
- Lower camera resolution
- Ensure GPU support for TensorFlow (optional)

### No Face Detected
- Ensure good lighting
- Move closer to camera
- Adjust `min_detection_confidence` in `camera_engine.py`

## 📊 Database Structure

### Firestore Collections

**students** collection:
```json
{
  "student_id": "12345",
  "name": "John Doe",
  "embedding": [0.123, 0.456, ...],  // 512-dimensional vector
  "registered_at": "2025-01-01T12:00:00Z"
}
```

**attendance** collection:
```json
{
  "student_id": "12345",
  "name": "John Doe",
  "doctor_name": "Dr. Smith",
  "course_name": "Computer Vision",
  "course_code": "CS401",
  "timestamp": "2025-01-01T14:30:00Z",
  "marked_at": "2025-01-01 14:30:00"
}
```

## 🚦 Technology Stack

- **Backend**: Flask 3.0
- **Face Detection**: MediaPipe (BlazeFace)
- **Face Recognition**: DeepFace (Facenet512)
- **Database**: Firebase Firestore
- **Frontend**: Bootstrap 5, FontAwesome, SweetAlert2
- **Styling**: Custom cyberpunk dark theme

## 📝 License

This project is provided as-is for educational and commercial use.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## 📧 Support

For issues or questions, please check the troubleshooting section or create an issue in the repository.

---

**Built with ❤️ using MediaPipe and DeepFace**
