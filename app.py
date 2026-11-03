import math
import os
import json
import time
import random
import warnings
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, flash, g
from dotenv import load_dotenv
import cv2
import keyboard

import utils

warnings.filterwarnings("ignore")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "exam_proctor_secret_key_2026")

DATABASE = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'exam_system.db'))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=20.0)
        db.execute("PRAGMA journal_mode=WAL;")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'STUDENT',
                exam_status TEXT DEFAULT 'not given'
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            seed_data = [
                ('Admin', 'admin@test.com', 'admin123', 'ADMIN', 'not given'),
                ('Student', 'student@test.com', '123456', 'STUDENT', 'not given')
            ]
            cursor.executemany(
                "INSERT INTO students (name, email, password, role, exam_status) VALUES (?, ?, ?, ?, ?)",
                seed_data
            )
        conn.commit()

init_db()

# Module-level Haar Cascade detector to avoid re-reading XML every frame
HAAR_PATH = os.path.join(BASE_DIR, 'Haarcascades', 'haarcascade_frontalface_default.xml')
face_detector = cv2.CascadeClassifier(HAAR_PATH) if (hasattr(cv2, 'CascadeClassifier') and os.path.exists(HAAR_PATH)) else None

def admin_required():
    user = session.get('studentInfo')
    return user is not None and str(user.get('Role', '')).upper() == 'ADMIN'

def capture_by_frames():
    if utils.cap is None or not utils.cap.isOpened():
        utils.cap = utils.open_camera()

    while True:
        with utils.camera_lock:
            if utils.cap is None or not utils.cap.isOpened():
                break
            success, frame = utils.cap.read()

        if not success or frame is None:
            time.sleep(0.05)
            continue

        if face_detector is not None:
            faces = face_detector.detectMultiScale(frame, 1.2, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Login Related
@app.route('/')
def main():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, name, email, password, role, exam_status FROM students WHERE (email=? OR name=?) AND password=?", (username, username, password))
        data = cur.fetchone()
        if data is None:
            flash('Your Email or Password is incorrect, try again.', category='error')
            return redirect(url_for('main'))
        else:
            std_id, name, email, pwd, role, exam_status = data
            student_info = {"Id": std_id, "Name": name, "Email": email, "Password": pwd, "Role": role}
            session['studentInfo'] = student_info
            utils.Student_Name = name

            if role.lower() == 'student':
                if exam_status == 'given':
                    flash('You already gave the exam', 'error')
                    return redirect(url_for('main'))
                else:
                    return redirect(url_for('rules'))
            else:
                return redirect(url_for('adminStudents'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main'))

# Student Related
@app.route('/rules')
def rules():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))
    return render_template('ExamRules.html')

@app.route('/faceInput')
def faceInput():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))
    return render_template('ExamFaceInput.html')

@app.route('/video_capture')
def video_capture():
    return Response(capture_by_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/saveFaceInput')
def saveFaceInput():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))

    student = session['studentInfo']
    frame = None
    success = False

    with utils.camera_lock:
        if utils.cap is not None and utils.cap.isOpened():
            success, frame = utils.cap.read()
            try:
                utils.cap.release()
            except Exception:
                pass
            utils.cap = None
        else:
            cam = utils.open_camera()
            success, frame = cam.read()
            cam.release()

    if not success or frame is None:
        flash('Could not capture frame from webcam. Please retry.', 'error')
        return redirect(url_for('faceInput'))

    profile_name = f"{student['Name']}_{utils.get_resultId():03}Profile.jpg"
    out_dir = os.path.join(app.static_folder, 'Profiles')
    os.makedirs(out_dir, exist_ok=True)
    full_path = os.path.join(out_dir, profile_name)
    cv2.imwrite(full_path, frame)

    session['profileName'] = profile_name
    return redirect(url_for('confirmFaceInput'))

@app.route('/confirmFaceInput')
def confirmFaceInput():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))

    with utils.camera_lock:
        if utils.cap is not None:
            try:
                utils.cap.release()
            except Exception:
                pass
            utils.cap = None

    profile = session.get('profileName', '')
    utils.fr.encode_faces()
    return render_template('ExamConfirmFaceInput.html', profile=profile)

@app.route('/systemCheck')
def systemCheck():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))
    return render_template('ExamSystemCheck.html')

@app.route('/systemCheck', methods=["POST"])
def systemCheckRoute():
    if request.method == 'POST':
        examData = request.json or {}
        output = 'exam'
        input_str = examData.get('input', '')
        if 'Not available' in input_str.split(';'):
            output = 'systemCheckError'
        return jsonify({"output": output})

@app.route('/systemCheckError')
def systemCheckError():
    return render_template('ExamSystemCheckError.html')

@app.route('/exam')
def exam():
    if 'studentInfo' not in session:
        return redirect(url_for('main'))

    student = session['studentInfo']
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT exam_status FROM students WHERE email=?", (student.get('Email', ''),))
    row = cur.fetchone()
    if row and row[0] == 'given':
        flash('You have already taken the exam.', 'error')
        return redirect(url_for('main'))

    if not utils.Globalflag:
        utils.init_exam_session()
        utils.Globalflag = True
        utils.Student_Name = student.get('Name', 'Student')
        if utils.cap is None or not utils.cap.isOpened():
            utils.cap = utils.open_camera()

        threading.Thread(target=utils.cheat_Detection1, daemon=True).start()
        threading.Thread(target=utils.cheat_Detection2, daemon=True).start()
        threading.Thread(target=utils.fr.run_recognition, daemon=True).start()
        threading.Thread(target=utils.a.record, daemon=True).start()

        try:
            keyboard.hook(utils.shortcut_handler)
        except Exception as e:
            print("Keyboard hook error:", e)

    return render_template('Exam.html')

@app.route('/exam', methods=["POST"])
def examAction():
    link = ''
    resultStatus = ''
    student = session.get('studentInfo', {"Name": "Student", "Id": 1, "Email": "student@test.com"})

    if request.method == 'POST':
        examData = request.json or {}
        user_input = str(examData.get('input', ''))

        if user_input != '':
            # 1. Flush any active violations in progress so no evidence or penalty is missed
            utils.flush_all_active_violations()

            utils.Globalflag = False
            utils.stop_keyboard_hook()
            time.sleep(0.3)
            with utils.camera_lock:
                if utils.cap is not None and utils.cap.isOpened():
                    utils.cap.release()
                    utils.cap = None
            utils.release_all_writers()
            utils.deleteTrashVideos()

            if len(utils.shorcuts) > 0:
                unique_shortcuts = list(dict.fromkeys(utils.shorcuts))
                utils.write_json({
                    "Name": f"Prohibited Shortcuts ({','.join(unique_shortcuts)}) detected.",
                    "Time": f"{len(utils.shorcuts)} Counts",
                    "Duration": '',
                    "Mark": min(15.0, 1.5 * len(utils.shorcuts)),
                    "Link": '',
                    "RId": utils.get_resultId()
                })
                utils.shorcuts = []

            trustScore = utils.get_TrustScore(utils.get_resultId())
            try:
                correct_count = float(user_input)
            except ValueError:
                correct_count = 0.0

            totalMark = math.floor(correct_count * 6.6667)

            if trustScore >= 30:
                status = "Fail(Cheating)"
                link = 'showResultFail'
            else:
                if totalMark < 50:
                    status = "Fail"
                    link = 'showResultFail'
                else:
                    status = "Pass"
                    link = 'showResultPass'

            profile_name = session.get('profileName', '')
            utils.write_json({
                "Id": utils.get_resultId(),
                "Name": student['Name'],
                "TotalMark": totalMark,
                "TrustScore": max(100 - trustScore, 0),
                "Status": status,
                "Date": time.strftime("%Y-%m-%d", time.localtime(time.time())),
                "StId": student['Id'],
                "Link": profile_name
            }, "result.json")

            db = get_db()
            cur = db.cursor()
            cur.execute("UPDATE students SET exam_status='given' WHERE email=?", (student['Email'],))
            db.commit()

            resultStatus = f"{student['Name']};{totalMark};{status};{time.strftime('%Y-%m-%d', time.localtime(time.time()))}"
        else:
            utils.Globalflag = True
            resultStatus = ''

    return jsonify({"output": resultStatus, "link": link})

@app.route('/showResultPass/<result_status>')
def showResultPass(result_status):
    return render_template('ExamResultPass.html', result_status=result_status)

@app.route('/showResultFail/<result_status>')
def showResultFail(result_status):
    return render_template('ExamResultFail.html', result_status=result_status)

# Admin Related
@app.route('/adminResults')
def adminResults():
    if not admin_required():
        flash('Admin access required.', 'error')
        return redirect(url_for('main'))
    results = utils.getResults()
    return render_template('Results.html', results=results)

@app.route('/adminResultDetails/<resultId>')
def adminResultDetails(resultId):
    if not admin_required():
        flash('Admin access required.', 'error')
        return redirect(url_for('main'))
    result_Details = utils.getResultDetails(resultId)
    return render_template('ResultDetails.html', resultDetials=result_Details)

@app.route('/adminResultDetailsVideo/<videoInfo>')
def adminResultDetailsVideo(videoInfo):
    if not admin_required():
        flash('Admin access required.', 'error')
        return redirect(url_for('main'))
    videoInfo = videoInfo.split(';')
    filename = videoInfo[0]
    resultId = videoInfo[1] if len(videoInfo) > 1 else ''

    if filename.endswith('.wav'):
        mediaPath = '/static/OutputAudios/' + filename
    else:
        mediaPath = '/static/OutputVideos/' + filename

    return render_template(
        'ResultDetailsVideo.html',
        mediaPath=mediaPath,
        filename=filename,
        resultId=resultId
    )

@app.route('/adminStudents')
def adminStudents():
    if not admin_required():
        flash('Admin access required.', 'error')
        return redirect(url_for('main'))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, email, password, role, exam_status FROM students WHERE role='STUDENT'")
    data = cur.fetchall()
    return render_template('Students.html', students=data)

@app.route('/insertStudent', methods=['POST'])
def insertStudent():
    if not admin_required():
        return redirect(url_for('main'))
    name = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    if not name or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('adminStudents'))
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO students (name, email, password, role, exam_status) VALUES (?, ?, ?, 'STUDENT', 'not given')", (name, email, password))
        db.commit()
        flash('Student added successfully.', 'success')
    except sqlite3.IntegrityError:
        flash('A student with this email already exists.', 'error')
    except Exception as e:
        flash(f'Error adding student: {e}', 'error')
    return redirect(url_for('adminStudents'))

@app.route('/deleteStudent/<string:stdId>', methods=['GET'])
def deleteStudent(stdId):
    if not admin_required():
        return redirect(url_for('main'))
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM students WHERE id=?", (stdId,))
        db.commit()
        flash("Record Has Been Deleted Successfully", "success")
    except Exception as e:
        flash(f"Error deleting student: {e}", "error")
    return redirect(url_for('adminStudents'))

@app.route('/updateStudent', methods=['POST'])
def updateStudent():
    if not admin_required():
        return redirect(url_for('main'))
    id_data = request.form.get('id', '').strip()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    if not id_data or not name or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('adminStudents'))
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            UPDATE students
            SET name=?, email=?, password=?
            WHERE id=?
        """, (name, email, password, id_data))
        db.commit()
        flash('Student updated successfully.', 'success')
    except sqlite3.IntegrityError:
        flash('Email already belongs to another user.', 'error')
    except Exception as e:
        flash(f'Error updating student: {e}', 'error')
    return redirect(url_for('adminStudents'))

if __name__ == '__main__':
    app.run(debug=True)
