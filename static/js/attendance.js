/**
 * Smart Attendance System - Frontend Logic
 * Handles countdown timer, auto-marking, and real-time log updates
 */

let pollingInterval = null;
let timerInterval = null;
let lastRecognizedCount = 0;
let sessionEnded = false;
let markedStudentsSet = new Set();

// Session data
let sessionDuration = 0; // in seconds
let sessionStartTime = 0; // Unix timestamp
let sessionEndTime = 0;

// Audio context for notifications
let audioCtx = null;

/**
 * Initialize on page load
 */
window.addEventListener('load', () => {
    // Get session data from DOM
    const sessionData = document.getElementById('sessionData');
    const duration = parseInt(sessionData.dataset.duration); // minutes
    const startTime = parseFloat(sessionData.dataset.startTime); // Unix timestamp

    sessionDuration = duration * 60; // Convert to seconds
    sessionStartTime = startTime;
    sessionEndTime = sessionStartTime + sessionDuration;

    console.log(`[Session] Duration: ${duration} minutes, Start: ${new Date(startTime * 1000)}`);

    // Start timer and polling
    startCountdownTimer();
    startPolling();
    updateAttendanceLog();
    updateStats();
});

/**
 * Cleanup when page unloads
 */
window.addEventListener('beforeunload', () => {
    stopCountdownTimer();
    stopPolling();
});

/**
 * Countdown Timer Functions
 */
function startCountdownTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(updateTimerDisplay, 1000);
}

function stopCountdownTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function updateTimerDisplay() {
    const now = Date.now() / 1000; // Current time in seconds
    const remaining = Math.max(0, sessionEndTime - now);

    const minutes = Math.floor(remaining / 60);
    const seconds = Math.floor(remaining % 60);

    const display = document.querySelector('.timer-display');
    const timerText = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    display.textContent = timerText;

    // Color coding based on time remaining
    display.classList.remove('warning', 'critical');

    if (remaining <= 0 && !sessionEnded) {
        // Session ended
        display.classList.add('critical');
        sessionEnded = true;
        endSessionAutomatically();
    } else if (remaining <= 60) {
        // Less than 1 minute - critical
        display.classList.add('critical');
    } else if (remaining <= 300) {
        // Less than 5 minutes - warning
        display.classList.add('warning');
    }
}

async function endSessionAutomatically() {
    console.log('[Session] Time expired - ending automatically');

    stopCountdownTimer();
    stopPolling();

    Swal.fire({
        icon: 'info',
        title: 'Session Ended',
        html: `
            <p>The lecture duration has expired.</p>
            <p class="text-muted">Attendance has been automatically saved.</p>
        `,
        confirmButtonText: 'Return to Gateway',
        allowOutsideClick: false
    }).then(() => {
        window.location.href = '/end_session';
    });
}

function endSessionNow() {
    Swal.fire({
        title: 'End Session Now?',
        text: "This will stop the attendance tracking",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, end it',
        cancelButtonText: 'Continue'
    }).then((result) => {
        if (result.isConfirmed) {
            sessionEnded = true;
            stopCountdownTimer();
            stopPolling();
            window.location.href = '/end_session';
        }
    });
}

/**
 * Polling Functions
 */
function startPolling() {
    pollingInterval = setInterval(async () => {
        if (!sessionEnded) {
            await updateAttendanceLog();
            await updateStats();
            await autoMarkAttendance();
        }
    }, 2000); // Poll every 2 seconds
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
 * Update attendance log (only show NEW students)
 */
async function updateAttendanceLog() {
    try {
        const response = await fetch('/api/get_recognized_students');
        const data = await response.json();

        const log = document.getElementById('attendanceLog');

        if (data.students && data.students.length > 0) {
            // Filter only new students (not yet marked)
            const newStudents = data.students.filter(s => !markedStudentsSet.has(s.student_id));

            if (newStudents.length > 0) {
                // Clear empty state on first student
                if (log.querySelector('.text-center.text-muted')) {
                    log.innerHTML = '';
                }

                // Add each new student to log
                newStudents.forEach(student => {
                    if (!document.getElementById(`log-${student.student_id}`)) {
                        const logItem = document.createElement('div');
                        logItem.className = 'log-item';
                        logItem.id = `log-${student.student_id}`;

                        const statusIcon = student.is_marked
                            ? '<i class="fas fa-check-circle" style="color: #00ff00;"></i>'
                            : '<i class="fas fa-clock" style="color: #ffd700;"></i>';

                        logItem.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="time">
                                        <i class="fas fa-clock"></i> ${student.timestamp}
                                    </div>
                                    <div class="name">
                                        <i class="fas fa-user"></i> ${student.name}
                                    </div>
                                    <div class="id">
                                        <i class="fas fa-id-badge"></i> ID: ${student.student_id}
                                    </div>
                                </div>
                                <div>
                                    ${statusIcon}
                                </div>
                            </div>
                        `;

                        // Add to top of log
                        log.insertBefore(logItem, log.firstChild);

                        // Animate entry
                        logItem.style.opacity = '0';
                        logItem.style.transform = 'translateX(-20px)';
                        setTimeout(() => {
                            logItem.style.transition = 'all 0.3s ease';
                            logItem.style.opacity = '1';
                            logItem.style.transform = 'translateX(0)';
                        }, 10);

                        // Play notification sound
                        playNotificationSound();
                    }
                });
            }

            // Track recognized count for sound notification
            if (data.students.length > lastRecognizedCount) {
                lastRecognizedCount = data.students.length;
            }
        }
    } catch (error) {
        console.error('Failed to update attendance log:', error);
    }
}

/**
 * Auto-mark attendance for recognized students
 */
async function autoMarkAttendance() {
    if (sessionEnded) return;

    try {
        const response = await fetch('/api/mark_attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success && data.marked_count > 0) {
            console.log(`[Auto-Mark] Marked ${data.marked_count} student(s)`);

            // Add marked students to set
            data.students.forEach(s => {
                markedStudentsSet.add(s.student_id);
            });

            // Update stats immediately
            await updateStats();
        }
    } catch (error) {
        console.error('Failed to auto-mark attendance:', error);
    }
}

/**
 * Update statistics
 */
async function updateStats() {
    try {
        const response = await fetch('/api/session_stats');
        const data = await response.json();

        document.getElementById('recognizedCount').textContent = data.total_recognized;
        document.getElementById('markedCount').textContent = data.total_marked;
        document.getElementById('presentCount').textContent = data.total_marked;
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

/**
 * Manual refresh
 */
async function refreshLog() {
    await updateAttendanceLog();
    await updateStats();

    // Show toast notification
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 1500
    });

    Toast.fire({
        icon: 'success',
        title: 'Log refreshed'
    });
}

/**
 * Play subtle notification sound
 */
function playNotificationSound() {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }

        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.frequency.value = 800;
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);

        oscillator.start(audioCtx.currentTime);
        oscillator.stop(audioCtx.currentTime + 0.1);
    } catch (error) {
        console.error('Failed to play notification sound:', error);
    }
}
