# [🎓 AI Smart Attendance & Course Management System](https://github.com/SamiAwawda/Face-Attendance-System)
### *Cyberpunk Edition*

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-BlazeFace-00C4CC?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev/)

---

## 🚀 Project Overview

A cutting-edge **Real-Time Face Recognition Attendance System** designed to eliminate manual attendance processes in universities. Built with AI-powered face detection and recognition, this system features a futuristic **Dark/Neon Cyberpunk UI** and comprehensive course management capabilities.

**The Problem:** Traditional attendance systems are time-consuming, prone to proxy attendance fraud, and lack analytics.

**The Solution:** Leverage Google MediaPipe for blazing-fast face detection and DeepFace (Facenet512) for high-accuracy recognition, combined with Firebase Firestore for scalable cloud storage and a sleek admin/professor dual-portal architecture.

---

## ✨ Key Features

### 🎯 Real-Time Face Detection & Recognition
- **High FPS Performance:** Powered by Google MediaPipe (BlazeFace) for instant face detection
- **Advanced Recognition:** DeepFace with Facenet512 model using cosine similarity (0.6 threshold)
- **Smart Color-Coded Feedback:**
  - 🟢 **GREEN** → New student detected
  - 🟡 **GOLD** → Already marked (prevents duplicates)
  - 🔵 **CYAN** → Unknown face

### 🔐 Secure Admin Dashboard
- **Password-Protected Portal** for IT/Admin staff
- **Student Management:** Add, view, and delete students with face embeddings
- **Course Management:** Create courses with capacity, start dates, and lecture counts
- **Statistics Overview:** Total students, courses, and attendance sessions

### 📊 Professor Analytics Portal
- **Course-Based Login:** Dropdown selection + unique course passwords
- **Live Analytics Dashboard:**
  - Current week calculation (auto-computed from start date)
  - Total capacity vs. present/absent students
  - Attendance rate percentages
- **Historical Data:** Week-by-week attendance records with visual progress bars
- **Seamless Navigation:** Stats dashboard → Start session → View final results

### 🧠 Smart Anti-Spoofing Logic
- **Duplicate Prevention:** Students marked only once per session (using sets)
- **Auto-Absentee Calculation:** `Absent = Capacity - Present`
- **Session Timer:** Countdown timer with auto-end at 00:00
- **Live Attendance Log:** Real-time scrolling feed (only new students displayed)

### 🎨 Cyberpunk UI/UX
- **Dark Mode Theme** with neon cyan/magenta accents
- **Animated Elements:** Glow effects, scanlines, hover animations
- **Responsive Design:** Bootstrap 5 with custom CSS
- **SweetAlert2 Notifications** for elegant user feedback

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.8+, Flask 2.0+ |
| **Face Detection** | Google MediaPipe (BlazeFace) |
| **Face Recognition** | DeepFace (Facenet512 Model) |
| **Database** | Firebase Firestore (NoSQL Cloud) |
| **Frontend** | HTML5, Bootstrap 5, Jinja2 Templates |
| **Styling** | Custom CSS (Cyberpunk Theme), FontAwesome Icons |
| **Notifications** | SweetAlert2 |
| **Video Streaming** | MJPEG (Motion JPEG) |

---

## 📦 Installation Guide

### Prerequisites
- Python 3.8 or higher
- Firebase Project with Firestore enabled
- Webcam/Camera for face capture

### Step 1: Clone Repository
```bash
git clone https://github.com/SamiAwawda/Face-Attendance-System.git
cd Face-Attendance-System
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Firebase
1. Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Enable **Firestore Database**
3. Download your service account key JSON file
4. Rename it to `firebase_config.json` and place in project root

```json
// firebase_config.json structure
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  // ... other fields
}
```

### Step 5: Run the Application
```bash
python app.py
```

The server will start at `http://localhost:5000`

---

## 🎮 Usage Workflow

### For Administrators:
1. Navigate to `http://localhost:5000`
2. Click **"Admin Portal"**
3. Enter password: `admin123` (change in `app.py`)
4. **Manage Students:** Add/delete students with face capture
5. **Manage Courses:** Create courses with:
   - Course name & code
   - Doctor/professor name
   - Course password
   - Start date & total lectures
   - Total enrolled students (capacity)

### For Professors:
1. Navigate to `http://localhost:5000`
2. Click **"Professor Portal"**
3. Select your course from dropdown
4. Enter course password
5. **View Analytics:** See current week, attendance stats, historical data
6. Click **"Start New Session"**
7. **Live Recognition:** System detects and marks students automatically
8. Click **"End Session"** → Redirected to stats with final results

---

## 📸 Screenshots

### Gateway Page
<!-- ![Gateway Screenshot](./screenshots/gateway.png) -->
*Dual-portal entry point with cyberpunk theme*

### Admin Dashboard
<!-- ![Admin Dashboard](./screenshots/admin_dashboard.png) -->
*Student and course management with tabbed interface*

### Course Analytics
<!-- ![Course Stats](./screenshots/course_stats.png) -->
*Professor dashboard showing week-by-week attendance history*

### Live Attendance
<!-- ![Attendance Page](./screenshots/attendance.png) -->
*Real-time face recognition with color-coded detection*

---

## 🗂️ Project Structure

```
ai-attendance-system/
├── app.py                      # Main Flask application
├── camera_engine.py            # Face detection & recognition engine
├── templates/
│   ├── layout.html            # Base template with cyberpunk CSS
│   ├── index.html             # Gateway page
│   ├── admin_login.html       # Admin authentication
│   ├── admin_dashboard.html   # Admin management panel
│   ├── doctor_login.html      # Professor course selection
│   ├── course_stats.html      # Analytics dashboard
│   ├── attendance.html        # Live recognition page
│   └── register.html          # Student registration
├── static/
│   └── js/
│       └── attendance.js      # Frontend timer & auto-marking logic
├── firebase_config.json       # Firebase credentials (not in repo)
├── requirements.txt           # Python dependencies
├── setup.sh                   # Automated setup script
└── README.md                  # This file
```

---

## 🔒 Security Notes

> **⚠️ IMPORTANT:** This system uses plain-text passwords for course authentication as a proof-of-concept. For production deployment:
> - Implement proper password hashing (bcrypt)
> - Use environment variables for secrets
> - Enable Firebase security rules
> - Add HTTPS/SSL certificates
> - Implement session timeouts

---

## 🎯 Future Enhancements

- [ ] Export attendance reports to CSV/Excel
- [ ] Email notifications for low attendance
- [ ] Mobile app integration
- [ ] Multi-camera support for large classrooms
- [ ] Advanced anti-spoofing (liveness detection)
- [ ] Student portal for checking personal attendance
- [ ] Integration with university LMS systems

---

## 📊 Database Schema

### Collections Structure

**Students Collection:**
```json
{
  "student_id": "12345",
  "name": "John Doe",
  "embedding": [512 floats],  // Facenet512 vector
  "registered_at": Timestamp
}
```

**Courses Collection:**
```json
{
  "course_code": "CS401",
  "course_name": "Computer Vision",
  "doctor_name": "Dr. Smith",
  "password": "course_password",
  "start_date": Timestamp,
  "total_lectures": 14,
  "class_capacity": 50,
  "created_at": Timestamp
}
```

**Attendance Collection:**
```json
{
  "student_id": "12345",
  "name": "John Doe",
  "course_code": "CS401",
  "course_name": "Computer Vision",
  "doctor_name": "Dr. Smith",
  "timestamp": Timestamp,
  "marked_at": "2025-11-27 23:30:00"
}
```

---

## 🧪 Testing

### Manual Testing Checklist
- [ ] Admin login with correct/incorrect password
- [ ] Create course with all fields
- [ ] Delete course with confirmation
- [ ] Register student with face capture
- [ ] Delete student from database
- [ ] Doctor login with course selection
- [ ] View analytics and historical data
- [ ] Start attendance session
- [ ] Verify color-coded detection (green/gold)
- [ ] End session and view final stats
- [ ] Countdown timer reaches 00:00

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Sami Awawda**
- GitHub: [@SamiAwawda](https://github.com/SamiAwawda)

---

## 🙏 Acknowledgments

- **Google MediaPipe** for high-performance face detection
- **DeepFace** for state-of-the-art face recognition
- **Firebase** for scalable cloud infrastructure
- **Bootstrap** for responsive UI components
- **SweetAlert2** for beautiful notifications

---

## 📈 Project Stats

![GitHub repo size](https://img.shields.io/github/repo-size/SamiAwawda/Face-Attendance-System)
![GitHub stars](https://img.shields.io/github/stars/SamiAwawda/Face-Attendance-System?style=social)
![GitHub forks](https://img.shields.io/github/forks/SamiAwawda/Face-Attendance-System?style=social)

---

<div align="center">

### ⭐ Star this repo if you found it helpful!

**Developed with 💙 by Sami Awawda | Powered by MediaPipe & DeepFace**

</div>
