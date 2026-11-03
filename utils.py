import sys
import os
import json
import shutil
import math
import random
import time
import datetime
import struct
import wave
import threading
import collections
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import mediapipe as mp
import keyboard
import pyautogui
import pygetwindow as gw
from ultralytics import YOLO

# Optional imports with safe fallbacks
try:
    import face_recognition
except ImportError:
    face_recognition = None

try:
    import pyaudio
except ImportError:
    pyaudio = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure required directories exist on launch
for _dir in [os.path.join(BASE_DIR, 'static', 'Profiles'), 
             os.path.join(BASE_DIR, 'static', 'OutputVideos'), 
             os.path.join(BASE_DIR, 'static', 'OutputAudios')]:
    os.makedirs(_dir, exist_ok=True)

# Ensure result and violation JSON files exist on launch
json_lock = threading.Lock()
result_json_path = os.path.join(BASE_DIR, 'result.json')
violation_json_path = os.path.join(BASE_DIR, 'violation.json')

if not os.path.exists(result_json_path):
    with open(result_json_path, 'w', encoding='utf-8') as f:
        json.dump([{
            "Id": 0,
            "Name": "System Initializer",
            "TotalMark": 0,
            "TrustScore": 100,
            "Status": "Pass",
            "Date": time.strftime("%Y-%m-%d", time.localtime(time.time())),
            "StId": 0,
            "Link": ""
        }], f, indent=4)

if not os.path.exists(violation_json_path):
    with open(violation_json_path, 'w', encoding='utf-8') as f:
        json.dump([], f, indent=4)

# Global Proctoring Variables
Globalflag = False
Student_Name = ''
start_time = [0, 0, 0, 0, 0]
end_time = [0, 0, 0, 0, 0]
recorded_durations = []
prev_state = ['Verified Student appeared', "Forward", "Only one person is detected", "Stay in the Test", "No Electronic Device Detected"]
flag = [False, False, False, False, False]

width = 640
height = 480
EDWidth = 640
EDHeight = 480

video = [(str(random.randint(1, 50000)) + ".mp4") for _ in range(5)]
fourcc_default = cv2.VideoWriter_fourcc(*'mp4v')
writer = [
    cv2.VideoWriter(video[0], fourcc_default, 20, (width, height)),
    cv2.VideoWriter(video[1], fourcc_default, 20, (width, height)),
    cv2.VideoWriter(video[2], fourcc_default, 20, (width, height)),
    cv2.VideoWriter(video[3], fourcc_default, 15, (1920, 1080)),
    cv2.VideoWriter(video[4], fourcc_default, 20, (EDWidth, EDHeight))
]

# MediaPipe Face Detection
mpFaceDetection = mp.solutions.face_detection
mpDraw = mp.solutions.drawing_utils
faceDetection = mpFaceDetection.FaceDetection(
    model_selection=1,
    min_detection_confidence=0.35
)

# Canonical 3D Head Pose Model for rigid solvePnP
CANONICAL_FACE_3D = np.array([
    [0.0, 0.0, 0.0],          # Nose tip (landmark 1)
    [0.0, -330.0, -65.0],     # Chin (landmark 199)
    [-225.0, 170.0, -135.0],  # Left eye outer corner (landmark 33)
    [225.0, 170.0, -135.0],   # Right eye outer corner (landmark 263)
    [-150.0, -150.0, -125.0], # Left mouth corner (landmark 61)
    [150.0, -150.0, -125.0]   # Right mouth corner (landmark 291)
], dtype=np.float64)

# Screen & Shortcuts
shorcuts = []
last_shortcut_time = 0
active_window = None
active_window_title = "Exam"
exam_window_title = active_window_title

# YOLO Model Loading with anchored path
coco_path = os.path.join(BASE_DIR, "utils", "coco.txt")
if os.path.exists(coco_path):
    try:
        with open(coco_path, "r", encoding="utf-8") as my_file:
            data = my_file.read()
        class_list = data.split("\n")
    except Exception:
        class_list = ["person", "cell phone", "remote"]
else:
    class_list = ["person", "cell phone", "remote"]

yolo_weights = os.path.join(BASE_DIR, "yolov8n.pt")
if not os.path.exists(yolo_weights):
    yolo_weights = "yolov8n.pt"
try:
    model = YOLO(yolo_weights)
except Exception as e:
    print(f"Warning: YOLOv8 model loading failed: {e}")
    model = None

EDFlag = False

# Voice Audio Configuration
TRIGGER_RMS = 15
RATE = 16000
TIMEOUT_SECS = 0.5
FRAME_SECS = 0.25
CUSHION_SECS = 1
SHORT_NORMALIZE = (1.0 / 32768.0)
FORMAT = pyaudio.paInt16 if pyaudio else 2
CHANNELS = 1
SHORT_WIDTH = 2
CHUNK = int(RATE * FRAME_SECS)
CUSHION_FRAMES = int(CUSHION_SECS / FRAME_SECS)
TIMEOUT_FRAMES = int(TIMEOUT_SECS / FRAME_SECS)
f_name_directory = BASE_DIR

# Video Capture handle
cap = None
camera_lock = threading.Lock()

def open_camera():
    c = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not c.isOpened():
        c = cv2.VideoCapture(0)
    return c

# Thread-safe and atomic JSON write
def write_json(new_data, filename='violation.json'):
    filepath = os.path.join(BASE_DIR, filename)
    with json_lock:
        file_data = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    file_data = json.load(file)
            except Exception:
                file_data = []
        file_data.append(new_data)
        temp_path = filepath + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as file:
                json.dump(file_data, file, indent=4)
            shutil.move(temp_path, filepath)
        except Exception as e:
            print(f"Error saving {filename}: {e}")

def move_file_to_output_folder(filename, folder='OutputVideos'):
    source_path = os.path.join(BASE_DIR, filename)
    destination_folder = os.path.join(BASE_DIR, 'static', folder)
    os.makedirs(destination_folder, exist_ok=True)
    destination_path = os.path.join(destination_folder, filename)

    if os.path.exists(source_path):
        try:
            shutil.move(source_path, destination_path)
            print(f"✅ Moved: {filename} to static/{folder}")
        except Exception as e:
            print(f"Error moving file {filename}: {e}")
    else:
        print(f"❌ File not found: {source_path}")

def reduceBitRate(input_file, output_file):
    try:
        shutil.copy(input_file, output_file)
    except Exception as e:
        print(f"Warning copying video {input_file}: {e}")

# Violation Recording Handlers
def faceDetectionRecording(img, text):
    global start_time, end_time, recorded_durations, prev_state, flag, writer, width, height
    if img is not None and (img.shape[1] != width or img.shape[0] != height):
        img = cv2.resize(img, (width, height))

    if text != 'Verified Student appeared' and prev_state[0] == 'Verified Student appeared':
        start_time[0] = time.time()
        writer[0].write(img)
    elif text != 'Verified Student appeared' and str(text) == prev_state[0] and (time.time() - start_time[0]) > 1:
        flag[0] = True
        writer[0].write(img)
    elif text != 'Verified Student appeared' and str(text) == prev_state[0] and (time.time() - start_time[0]) <= 1:
        flag[0] = False
        writer[0].write(img)
    else:
        if prev_state[0] != "Verified Student appeared":
            writer[0].release()
            end_time[0] = time.time()
            duration = max(1, math.ceil(end_time[0] - start_time[0]))
            outputVideo = 'FDViolation' + video[0]
            FDViolation = {
                "Name": prev_state[0],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[0])),
                "Duration": str(duration) + " seconds",
                "Mark": math.floor(2 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[0]:
                recorded_durations.append(FDViolation)
                write_json(FDViolation)
                reduceBitRate(video[0], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[0]):
                try:
                    os.remove(video[0])
                except Exception:
                    pass
            video[0] = str(random.randint(1, 50000)) + ".mp4"
            writer[0] = cv2.VideoWriter(video[0], fourcc_default, 20, (width, height))
            flag[0] = False
    prev_state[0] = text

def Head_record_duration(text, img):
    global start_time, end_time, recorded_durations, prev_state, flag, writer, width, height
    if img is not None and (img.shape[1] != width or img.shape[0] != height):
        img = cv2.resize(img, (width, height))

    if text != "Forward":
        if str(text) != prev_state[1] and prev_state[1] == "Forward":
            start_time[1] = time.time()
            writer[1].write(img)
        elif str(text) != prev_state[1] and prev_state[1] != "Forward":
            writer[1].release()
            end_time[1] = time.time()
            duration = max(1, math.ceil(end_time[1] - start_time[1]))
            outputVideo = 'HeadViolation' + video[1]
            HeadViolation = {
                "Name": prev_state[1],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[1])),
                "Duration": str(duration) + " seconds",
                "Mark": duration,
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[1]:
                recorded_durations.append(HeadViolation)
                write_json(HeadViolation)
                reduceBitRate(video[1], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[1]):
                try:
                    os.remove(video[1])
                except Exception:
                    pass
            start_time[1] = time.time()
            video[1] = str(random.randint(1, 50000)) + ".mp4"
            writer[1] = cv2.VideoWriter(video[1], fourcc_default, 20, (width, height))
            flag[1] = False
        elif str(text) == prev_state[1] and (time.time() - start_time[1]) > 3:
            flag[1] = True
            writer[1].write(img)
        elif str(text) == prev_state[1] and (time.time() - start_time[1]) <= 3:
            flag[1] = False
            writer[1].write(img)
        prev_state[1] = text
    else:
        if prev_state[1] != "Forward":
            writer[1].release()
            end_time[1] = time.time()
            duration = max(1, math.ceil(end_time[1] - start_time[1]))
            outputVideo = 'HeadViolation' + video[1]
            HeadViolation = {
                "Name": prev_state[1],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[1])),
                "Duration": str(duration) + " seconds",
                "Mark": duration,
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[1]:
                recorded_durations.append(HeadViolation)
                write_json(HeadViolation)
                reduceBitRate(video[1], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[1]):
                try:
                    os.remove(video[1])
                except Exception:
                    pass
            video[1] = str(random.randint(1, 50000)) + ".mp4"
            writer[1] = cv2.VideoWriter(video[1], fourcc_default, 20, (width, height))
            flag[1] = False
        prev_state[1] = text

def MTOP_record_duration(text, img):
    global start_time, end_time, recorded_durations, prev_state, flag, writer, width, height
    if img is not None and (img.shape[1] != width or img.shape[0] != height):
        img = cv2.resize(img, (width, height))

    if text != 'Only one person is detected' and prev_state[2] == 'Only one person is detected':
        start_time[2] = time.time()
        writer[2].write(img)
    elif text != 'Only one person is detected' and str(text) == prev_state[2] and (time.time() - start_time[2]) > 3:
        flag[2] = True
        writer[2].write(img)
    elif text != 'Only one person is detected' and str(text) == prev_state[2] and (time.time() - start_time[2]) <= 3:
        flag[2] = False
        writer[2].write(img)
    else:
        if prev_state[2] != "Only one person is detected":
            writer[2].release()
            end_time[2] = time.time()
            duration = max(1, math.ceil(end_time[2] - start_time[2]))
            outputVideo = 'MTOPViolation' + video[2]
            MTOPViolation = {
                "Name": prev_state[2],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[2])),
                "Duration": str(duration) + " seconds",
                "Mark": math.floor(1.5 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[2]:
                recorded_durations.append(MTOPViolation)
                write_json(MTOPViolation)
                reduceBitRate(video[2], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[2]):
                try:
                    os.remove(video[2])
                except Exception:
                    pass
            video[2] = str(random.randint(1, 50000)) + ".mp4"
            writer[2] = cv2.VideoWriter(video[2], fourcc_default, 20, (width, height))
            flag[2] = False
    prev_state[2] = text

def SD_record_duration(text, img):
    global start_time, end_time, prev_state, flag, writer
    if img is not None and (img.shape[1] != 1920 or img.shape[0] != 1080):
        img = cv2.resize(img, (1920, 1080))

    if text != "Stay in the Test" and prev_state[3] == "Stay in the Test":
        start_time[3] = time.time()
        writer[3].write(img)
    elif text != "Stay in the Test" and str(text) == prev_state[3] and (time.time() - start_time[3]) > 3:
        flag[3] = True
        writer[3].write(img)
    elif text != "Stay in the Test" and str(text) == prev_state[3] and (time.time() - start_time[3]) <= 3:
        flag[3] = False
        writer[3].write(img)
    else:
        if prev_state[3] != "Stay in the Test":
            writer[3].release()
            end_time[3] = time.time()
            duration = max(1, math.ceil(end_time[3] - start_time[3]))
            outputVideo = 'SDViolation' + video[3]
            SDViolation = {
                "Name": prev_state[3],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[3])),
                "Duration": str(duration) + " seconds",
                "Mark": (2 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[3]:
                recorded_durations.append(SDViolation)
                write_json(SDViolation)
                reduceBitRate(video[3], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[3]):
                try:
                    os.remove(video[3])
                except Exception:
                    pass
            video[3] = str(random.randint(1, 50000)) + ".mp4"
            writer[3] = cv2.VideoWriter(video[3], fourcc_default, 15, (1920, 1080))
            flag[3] = False
    prev_state[3] = text

def capture_screen():
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    if frame.shape[1] != 1920 or frame.shape[0] != 1080:
        frame = cv2.resize(frame, (1920, 1080))
    return frame

def EDD_record_duration(text, img):
    global start_time, end_time, prev_state, flag, writer, video, EDWidth, EDHeight
    if img is not None and (img.shape[1] != EDWidth or img.shape[0] != EDHeight):
        img = cv2.resize(img, (EDWidth, EDHeight))

    if text == "Electronic Device Detected" and prev_state[4] == "No Electronic Device Detected":
        start_time[4] = time.time()
        writer[4].write(img)
    elif text == "Electronic Device Detected" and str(text) == prev_state[4] and (time.time() - start_time[4]) > 2.0:
        flag[4] = True
        writer[4].write(img)
    elif text == "Electronic Device Detected" and str(text) == prev_state[4] and (time.time() - start_time[4]) <= 2.0:
        flag[4] = False
        writer[4].write(img)
    else:
        if prev_state[4] == "Electronic Device Detected":
            writer[4].release()
            end_time[4] = time.time()
            duration = max(1, math.ceil(end_time[4] - start_time[4]))
            outputVideo = 'EDViolation' + video[4]
            EDViolation = {
                "Name": prev_state[4],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[4])),
                "Duration": str(duration) + " seconds",
                "Mark": math.floor(1.5 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            if flag[4]:
                write_json(EDViolation)
                reduceBitRate(video[4], outputVideo)
                move_file_to_output_folder(outputVideo)
            if os.path.exists(video[4]):
                try:
                    os.remove(video[4])
                except Exception:
                    pass
            video[4] = str(random.randint(1, 50000)) + ".mp4"
            writer[4] = cv2.VideoWriter(video[4], fourcc_default, 20, (EDWidth, EDHeight))
            flag[4] = False
    prev_state[4] = text

def release_all_writers():
    global writer
    for w in writer:
        try:
            if w is not None:
                w.release()
        except Exception:
            pass

def deleteTrashVideos():
    for f in list(video):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

def init_exam_session():
    """
    Initializes a completely fresh set of video writers, random filenames,
    and state trackers before every new exam attempt.
    """
    global writer, video, flag, prev_state, start_time, end_time, shorcuts, fourcc_default
    
    release_all_writers()
    shorcuts.clear()
    
    video = [(str(random.randint(1, 50000)) + ".mp4") for _ in range(5)]
    fourcc_default = cv2.VideoWriter_fourcc(*'mp4v')
    writer = [
        cv2.VideoWriter(video[0], fourcc_default, 20, (width, height)),
        cv2.VideoWriter(video[1], fourcc_default, 20, (width, height)),
        cv2.VideoWriter(video[2], fourcc_default, 20, (width, height)),
        cv2.VideoWriter(video[3], fourcc_default, 15, (1920, 1080)),
        cv2.VideoWriter(video[4], fourcc_default, 20, (EDWidth, EDHeight))
    ]
    
    prev_state = [
        "Verified Student appeared",
        "Forward",
        "Only one person is detected",
        "Stay in the Test",
        "No Electronic Device Detected"
    ]
    flag = [False, False, False, False, False]
    now = time.time()
    start_time = [now, now, now, now, now]
    end_time = [now, now, now, now, now]

def flush_all_active_violations():
    """
    Flushes and finalizes any ongoing violations at the moment of exam submission
    so no active violation evidence is lost or discarded.
    """
    global start_time, end_time, prev_state, flag, writer, video
    now = time.time()

    # 0: Face Detection
    try:
        if prev_state[0] != "Verified Student appeared":
            if writer[0] is not None:
                writer[0].release()
            duration = max(1, math.ceil(now - start_time[0]))
            outputVideo = 'FDViolation' + video[0]
            violation = {
                "Name": prev_state[0],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[0])),
                "Duration": f"{duration} seconds",
                "Mark": math.floor(2 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            write_json(violation)
            reduceBitRate(video[0], outputVideo)
            move_file_to_output_folder(outputVideo)
            prev_state[0] = "Verified Student appeared"
    except Exception as e:
        print(f"Notice flushing face violation: {e}")

    # 1: Head Pose
    try:
        if prev_state[1] != "Forward":
            if writer[1] is not None:
                writer[1].release()
            duration = max(1, math.ceil(now - start_time[1]))
            outputVideo = 'HeadViolation' + video[1]
            violation = {
                "Name": prev_state[1],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[1])),
                "Duration": f"{duration} seconds",
                "Mark": duration,
                "Link": outputVideo,
                "RId": get_resultId()
            }
            write_json(violation)
            reduceBitRate(video[1], outputVideo)
            move_file_to_output_folder(outputVideo)
            prev_state[1] = "Forward"
    except Exception as e:
        print(f"Notice flushing head pose violation: {e}")

    # 2: Multiple Persons
    try:
        if prev_state[2] != "Only one person is detected":
            if writer[2] is not None:
                writer[2].release()
            duration = max(1, math.ceil(now - start_time[2]))
            outputVideo = 'MTOPViolation' + video[2]
            violation = {
                "Name": prev_state[2],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[2])),
                "Duration": f"{duration} seconds",
                "Mark": math.floor(1.5 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            write_json(violation)
            reduceBitRate(video[2], outputVideo)
            move_file_to_output_folder(outputVideo)
            prev_state[2] = "Only one person is detected"
    except Exception as e:
        print(f"Notice flushing MTOP violation: {e}")

    # 3: Screen Detection
    try:
        if prev_state[3] != "Stay in the Test":
            if writer[3] is not None:
                writer[3].release()
            duration = max(1, math.ceil(now - start_time[3]))
            outputVideo = 'SDViolation' + video[3]
            violation = {
                "Name": prev_state[3],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[3])),
                "Duration": f"{duration} seconds",
                "Mark": (2 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            write_json(violation)
            reduceBitRate(video[3], outputVideo)
            move_file_to_output_folder(outputVideo)
            prev_state[3] = "Stay in the Test"
    except Exception as e:
        print(f"Notice flushing screen violation: {e}")

    # 4: Electronic Device
    try:
        if prev_state[4] == "Electronic Device Detected":
            if writer[4] is not None:
                writer[4].release()
            duration = max(1, math.ceil(now - start_time[4]))
            outputVideo = 'EDViolation' + video[4]
            violation = {
                "Name": prev_state[4],
                "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time[4])),
                "Duration": f"{duration} seconds",
                "Mark": math.floor(1.5 * duration),
                "Link": outputVideo,
                "RId": get_resultId()
            }
            write_json(violation)
            reduceBitRate(video[4], outputVideo)
            move_file_to_output_folder(outputVideo)
            prev_state[4] = "No Electronic Device Detected"
    except Exception as e:
        print(f"Notice flushing device violation: {e}")

# Biometrics
def face_confidence(face_distance, face_match_threshold=0.6):
    linear_val = (1.0 - face_distance) / ((1.0 - face_match_threshold) * 2.0)
    if face_distance > face_match_threshold:
        return f"{max(0.0, round(linear_val * 100, 2))}%"
    else:
        value = (linear_val + ((1.0 - linear_val) * math.pow(max(0, (linear_val - 0.5) * 2), 0.2))) * 100
        return f"{min(100.0, round(value, 2))}%"

class FaceRecognition:
    def __init__(self):
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.known_face_encodings = []
        self.known_face_names = []
        self.process_current_frame = True
        self.encode_faces()

    def encode_faces(self):
        if face_recognition is None:
            return
        self.known_face_encodings.clear()
        self.known_face_names.clear()
        profiles_dir = os.path.join(BASE_DIR, 'static', 'Profiles')
        os.makedirs(profiles_dir, exist_ok=True)
        for image in os.listdir(profiles_dir):
            if not image.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            try:
                img_path = os.path.join(profiles_dir, image)
                face_image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(face_image)
                if len(encodings) > 0:
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_names.append(os.path.splitext(image)[0])
            except Exception as e:
                print(f"Skipping {image}: {e}")

    def run_recognition(self):
        global Globalflag, Student_Name, cap
        while Globalflag:
            if cap is None or not cap.isOpened() or face_recognition is None:
                time.sleep(0.5)
                continue

            with camera_lock:
                ret, frame = cap.read()

            if not ret or frame is None:
                time.sleep(0.1)
                continue

            text = "Verified Student disappeared"
            if len(self.known_face_encodings) > 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])
                self.face_locations = face_recognition.face_locations(rgb_small_frame)
                if len(self.face_locations) > 0:
                    self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
                    for face_encoding in self.face_encodings:
                        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                        if len(face_distances) > 0:
                            best_match_index = int(np.argmin(face_distances))
                            min_dist = face_distances[best_match_index]
                            matched_name = str(self.known_face_names[best_match_index])
                            if min_dist <= 0.58 and Student_Name.lower() in matched_name.lower():
                                text = "Verified Student appeared"

            faceDetectionRecording(frame, text)
            time.sleep(1)

# Head Movement Detection using Rigid Canonical 3D Model
def headMovmentDetection(image, face_mesh):
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = face_mesh.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    img_h, img_w, _ = image.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            face_2d = []
            # Landmark order matches CANONICAL_FACE_3D: (1, 199, 33, 263, 61, 291)
            for idx in (1, 199, 33, 263, 61, 291):
                lm = face_landmarks.landmark[idx]
                x, y = int(lm.x * img_w), int(lm.y * img_h)
                face_2d.append([x, y])

            face_2d = np.array(face_2d, dtype=np.float64)
            focal_length = 1.0 * img_w
            cam_matrix = np.array([[focal_length, 0, img_w / 2.0],
                                   [0, focal_length, img_h / 2.0],
                                   [0, 0, 1.0]], dtype=np.float64)
            dist_matrix = np.zeros((4, 1), dtype=np.float64)
            success, rot_vec, trans_vec = cv2.solvePnP(CANONICAL_FACE_3D, face_2d, cam_matrix, dist_matrix)
            if not success:
                break
            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

            x_deg = angles[0]
            y_deg = angles[1]

            textHead = 'Forward'
            if y_deg < -15:
                textHead = "Looking Left"
            elif y_deg > 15:
                textHead = "Looking Right"
            elif x_deg < -18:
                textHead = "Looking Down"
            elif x_deg > 15:
                textHead = "Looking Up"

            cv2.putText(image, textHead, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            Head_record_duration(textHead, image)
            break

# Keyboard Shortcut Detection with Debounce
def shortcut_handler(event):
    global last_shortcut_time, shorcuts
    if event.event_type == keyboard.KEY_DOWN:
        now = time.time()
        if now - last_shortcut_time < 0.6:
            return
        shortcut = ''
        if keyboard.is_pressed('ctrl') and keyboard.is_pressed('c'):
            shortcut = 'Ctrl+C'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('v'):
            shortcut = 'Ctrl+V'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('a'):
            shortcut = 'Ctrl+A'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('x'):
            shortcut = 'Ctrl+X'
        elif keyboard.is_pressed('alt') and keyboard.is_pressed('tab'):
            shortcut = 'Alt+Tab'
        elif keyboard.is_pressed('win') and keyboard.is_pressed('tab'):
            shortcut = 'Win+Tab'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('t'):
            shortcut = 'Ctrl+T'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('w'):
            shortcut = 'Ctrl+W'
        elif keyboard.is_pressed('ctrl') and keyboard.is_pressed('z'):
            shortcut = 'Ctrl+Z'
        elif keyboard.is_pressed('f12'):
            shortcut = 'F12'
        elif keyboard.is_pressed('print_screen'):
            shortcut = 'Prt Scn'

        if shortcut != "":
            last_shortcut_time = now
            shorcuts.append(shortcut)
            print("Prohibited shortcut detected:", shortcut)

def stop_keyboard_hook():
    try:
        keyboard.unhook_all()
    except Exception:
        pass

# Screen and Window Detection
def screenDetection():
    textScreen = "Stay in the Test"
    new_active_window = gw.getActiveWindow()
    frame = capture_screen()

    if new_active_window is not None and getattr(new_active_window, 'title', None):
        current_title = new_active_window.title.lower()
        valid_browsers = ["chrome", "firefox", "edge", "brave", "opera"]
        is_browser = any(b in current_title for b in valid_browsers)
        if is_browser and "exam" in current_title:
            textScreen = "Stay in the Test"
        else:
            textScreen = "Move away from the Test"
    else:
        textScreen = "Move away from the Test"

    SD_record_duration(textScreen, frame)

# Electronic Device Detection
def electronicDevicesDetection(frame):
    global model, EDFlag
    person_count = 0
    if model is not None:
        try:
            detect_params = model.predict(source=[frame], conf=0.45, save=False, verbose=False)
            for result in detect_params:
                boxes = result.boxes.cpu().numpy()
                for box in boxes:
                    detected_obj = result.names[int(box.cls[0])]
                    if detected_obj == 'person':
                        person_count += 1
                    if detected_obj in ['cell phone', 'remote']:
                        EDFlag = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, detected_obj, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        except Exception as e:
            print("YOLO detection error:", e)

    if person_count > 1:
        textMTOP = "More than one person is detected"
    else:
        textMTOP = "Only one person is detected"

    MTOP_record_duration(textMTOP, frame)

    if EDFlag:
        textED = 'Electronic Device Detected'
    else:
        textED = "No Electronic Device Detected"

    EDD_record_duration(textED, frame)
    EDFlag = False

# Audio Recording
class Recorder:
    @staticmethod
    def rms(frame):
        if not frame:
            return 0.0
        count = len(frame) // SHORT_WIDTH
        if count == 0:
            return 0.0
        format = "%dh" % count
        shorts = struct.unpack(format, frame[:count * SHORT_WIDTH])
        sum_squares = sum((s * SHORT_NORMALIZE) ** 2 for s in shorts)
        return math.sqrt(sum_squares / count) * 1000

    def __init__(self):
        self.p = None
        self.stream = None
        self.quiet = collections.deque(maxlen=CUSHION_FRAMES)
        self.timeout = 0
        self.initialized = False

    def init_audio(self):
        if self.initialized and self.stream is not None:
            return True
        if pyaudio is None:
            return False
        try:
            self.p = pyaudio.PyAudio()
            if self.p.get_device_count() == 0:
                return False
            self.stream = self.p.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      output=False,
                                      frames_per_buffer=CHUNK)
            self.initialized = True
            return True
        except Exception as e:
            print(f"Warning: Audio device could not be opened: {e}")
            return False

    def record(self):
        global Globalflag
        if not self.init_audio():
            print("Microphone not available, skipping audio proctoring.")
            return

        self.quiet.clear()
        sound = []
        begin_time = None
        try:
            while Globalflag:
                try:
                    data = self.stream.read(CHUNK, exception_on_overflow=False)
                except Exception:
                    time.sleep(0.1)
                    continue

                if self.inSound(data):
                    sound.append(data)
                    if begin_time is None:
                        begin_time = datetime.datetime.now()
                else:
                    if len(sound) > 0 and begin_time is not None:
                        duration = max(1, math.floor((datetime.datetime.now() - begin_time).total_seconds()))
                        self.write(sound, begin_time, duration)
                        sound.clear()
                        begin_time = None
                    else:
                        self.quiet.append(data)
                time.sleep(0.01)
        except Exception as e:
            print("Error in audio recording loop:", e)
        finally:
            if len(sound) > 0 and begin_time is not None:
                try:
                    duration = max(1, math.floor((datetime.datetime.now() - begin_time).total_seconds()))
                    self.write(sound, begin_time, duration)
                    sound.clear()
                except Exception as ex:
                    print("Error flushing active audio buffer:", ex)
            self.close()

    def inSound(self, data):
        rms_val = self.rms(data)
        curr = time.time()
        if rms_val > TRIGGER_RMS:
            self.timeout = curr + TIMEOUT_SECS
            return True
        if curr < self.timeout:
            return True
        self.timeout = 0
        return False

    def write(self, sound, begin_time, duration):
        try:
            recording = b''.join(list(self.quiet) + sound)
            filename = f"{random.randint(1, 50000)}VoiceViolation"
            out_dir = os.path.join(BASE_DIR, 'static', 'OutputAudios')
            os.makedirs(out_dir, exist_ok=True)
            pathname = os.path.join(out_dir, f'{filename}.wav')
            with wave.open(pathname, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                sample_width = self.p.get_sample_size(FORMAT) if self.p else SHORT_WIDTH
                wf.setsampwidth(sample_width)
                wf.setframerate(RATE)
                wf.writeframes(recording)

            voiceViolation = {
                "Name": "Common Noise is detected.",
                "Time": begin_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Duration": str(duration) + " seconds",
                "Mark": duration,
                "Link": f'{filename}.wav',
                "RId": get_resultId()
            }
            write_json(voiceViolation)
            print(f"[+] Saved audio violation: {pathname}")
        except Exception as e:
            print("Error saving audio file:", e)

    def close(self):
        try:
            if self.stream is not None:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            if self.p is not None:
                self.p.terminate()
                self.p = None
        except Exception:
            pass
        self.initialized = False

# Cheat Detection Worker Loops
def cheat_Detection1():
    deleteTrashVideos()
    global Globalflag
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    while Globalflag:
        if cap is None or not cap.isOpened():
            time.sleep(0.5)
            continue
        with camera_lock:
            success, image = cap.read()
        if not success or image is None:
            time.sleep(0.1)
            continue
        headMovmentDetection(image, face_mesh)
        time.sleep(0.08)
    deleteTrashVideos()

def cheat_Detection2():
    try:
        global Globalflag
        deleteTrashVideos()
        screen_timer = 0
        yolo_timer = 0
        while Globalflag:
            if cap is None or not cap.isOpened():
                time.sleep(0.5)
                continue
            with camera_lock:
                success, image = cap.read()
            if not success or image is None:
                time.sleep(0.1)
                continue

            now = time.time()
            # Run screen detection every 1.5 seconds to reduce CPU load
            if now - screen_timer > 1.5:
                screenDetection()
                screen_timer = now

            # Throttle YOLO to every 0.5s to prevent CPU overload
            if now - yolo_timer > 0.5:
                electronicDevicesDetection(image.copy())
                yolo_timer = now

            time.sleep(0.08)
        deleteTrashVideos()
    except Exception as e:
        print("Error in cheat_Detection2:", e)

# Result & Query Helpers
def get_resultId():
    with json_lock:
        if not os.path.exists(result_json_path):
            return 1
        try:
            with open(result_json_path, 'r', encoding='utf-8') as file:
                file_data = json.load(file)
                if not file_data:
                    return 1
                file_data.sort(key=lambda x: x.get("Id", 0))
                return file_data[-1].get('Id', 0) + 1
        except Exception:
            return 1

def get_TrustScore(Rid):
    with json_lock:
        if not os.path.exists(violation_json_path):
            return 0
        try:
            with open(violation_json_path, 'r', encoding='utf-8') as file:
                file_data = json.load(file)
                try:
                    target_id = int(Rid)
                except (ValueError, TypeError):
                    target_id = Rid
                filtered_data = [item for item in file_data if item.get("RId") == target_id]
                return sum(item.get("Mark", 0) for item in filtered_data)
        except Exception:
            return 0

def getResults():
    with json_lock:
        if not os.path.exists(result_json_path):
            return []
        try:
            with open(result_json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception:
            return []

def getResultDetails(rid):
    with json_lock:
        result_data = []
        violation_data = []
        if os.path.exists(result_json_path):
            try:
                with open(result_json_path, 'r', encoding='utf-8') as file:
                    result_data = json.load(file)
            except Exception:
                pass
        if os.path.exists(violation_json_path):
            try:
                with open(violation_json_path, 'r', encoding='utf-8') as file:
                    violation_data = json.load(file)
            except Exception:
                pass
        try:
            target_id = int(rid)
        except (ValueError, TypeError):
            target_id = 0
        filtered_result = [item for item in result_data if item.get("Id") == target_id]
        filtered_violations = [item for item in violation_data if item.get("RId") == target_id]
        return {
            "Result": filtered_result,
            "Violation": filtered_violations
        }

# Initialized objects
a = Recorder()
fr = FaceRecognition()
