# Save this as local_test.py (HEAVILY UPDATED)
import cv2
from ultralytics import YOLO
import requests
import datetime
import json
import time
import os
import csv
import easyocr
import numpy as np

# --- CONFIGURATION ---
# Path to your custom model
MODEL_CUSTOM_PATH = r"O:/Traffic-Violation/Helmet-Number-Plate-Detector\best.pt"
MODEL_GENERAL_PATH = 'yolov8n.pt'
VIDEO_SOURCE = "test_videos/22.mp4" # !! CHANGE THIS !!

# CSV file setup
CSV_FILE_NAME = 'violations_log.csv'
CSV_HEADER = ['Timestamp', 'Plate Number', 'Helmet Status', 'Person Count']

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/api/v1/log_violation/"

# Initialize EasyOCR reader
try:
    reader = easyocr.Reader(['en'], gpu=True) # Use gpu=True if you have a CUDA-enabled GPU
except:
    print("EasyOCR failed to load with GPU, falling back to CPU.")
    reader = easyocr.Reader(['en'], gpu=False)

# --- CSV HELPER FUNCTIONS ---
def init_csv():
    """Creates the CSV file with a header if it doesn't exist."""
    if not os.path.exists(CSV_FILE_NAME):
        with open(CSV_FILE_NAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            print(f"Created {CSV_FILE_NAME} with header.")

def log_to_csv(data_row):
    """Appends a single row of data to the CSV file."""
    try:
        with open(CSV_FILE_NAME, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(data_row)
    except Exception as e:
        print(f"Error writing to CSV: {e}")

# --- OCR HELPER FUNCTION ---
def extract_plate_text(plate_image):
    """Uses EasyOCR to extract text from a cropped plate image."""
    try:
        # Read text
        results = reader.readtext(plate_image)
        
        # Filter results - combine text and filter out low-confidence
        plate_text = ""
        for (bbox, text, prob) in results:
            if prob > 0.4: # Confidence threshold
                plate_text += text.strip() + " "
        
        # Basic cleanup
        plate_text = plate_text.strip().upper().replace(" ", "")
        return plate_text if plate_text else "Not Read"
        
    except Exception as e:
        print(f"OCR Error: {e}")
        return "OCR Error"

# --- BACKEND HELPER FUNCTIONS ---
def send_to_backend(violation_list):
    """Sends a list of violation events to the backend."""
    for violation in violation_list:
        try:
            event_data = {
                "violation_type": violation["type"],
                "timestamp": violation["timestamp"],
                "gps": violation["gps"],
                "camera_id": "local_cam_01"
            }
            
            _, img_encoded = cv2.imencode(".jpg", violation["evidence"])
            
            files = {
                'event_data_str': (None, json.dumps(event_data), 'application/json'), 
                'evidence_file': (f"{violation['timestamp']}.jpg", img_encoded.tobytes(), 'image/jpeg')
            }
            
            response = requests.post(BACKEND_URL, files=files)
            
            if response.status_code == 200:
                print(f"Successfully sent violation to backend: {violation['type']}")
            else:
                print(f"Error sending to backend: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Failed to connect or send data to backend: {e}")

def capture_evidence(frame, box):
    """Crops the bounding box area from the frame."""
    x1, y1, x2, y2 = map(int, box)
    # Add some padding
    y1_pad = max(0, y1 - 20)
    y2_pad = min(frame.shape[0], y2 + 20)
    x1_pad = max(0, x1 - 20)
    x2_pad = min(frame.shape[1], x2 + 20)
    return frame[y1_pad:y2_pad, x1_pad:x2_pad]

# --- MAIN PROCESSING ---

def main():
    # 1. Initialize CSV
    init_csv()

    # 2. Load AI Models
    print("Loading models...")
    # Model for general objects (person, motorcycle)
    model_general = YOLO(MODEL_GENERAL_PATH)
    # Your custom model (plate, with helmet, without helmet)
    model_custom = YOLO(MODEL_CUSTOM_PATH)
    # Get custom class names
    custom_names = model_custom.names
    print(f"Custom model classes: {custom_names}")

    # 3. Capture Video Stream
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"Error: Could not open video file {VIDEO_SOURCE}")
        return

    print("Processing video... Press 'q' to quit.")
    
    frame_count = 0
    
    # 4. Process Frames
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # To avoid processing every single frame, you can skip some
        frame_count += 1
        if frame_count % 3 != 0: # Process every 3rd frame
            continue

        annotated_frame = frame.copy()
        violations_to_send_backend = []

        # --- STEP A: Run General Model (Persons and Motorcycles) ---
        # Classes: 0=person, 3=motorcycle (in standard COCO)
        general_results = model_general.track(frame, classes=[0, 3], persist=True, tracker="bytetrack.yaml")

        person_boxes = []
        motorcycle_boxes = []
        
        if general_results[0].boxes.id is not None:
            boxes = general_results[0].boxes.xyxy.cpu().numpy()
            track_ids = general_results[0].boxes.id.int().cpu().tolist()
            class_ids = general_results[0].boxes.cls.int().cpu().tolist()

            for box, track_id, cls_id in zip(boxes, track_ids, class_ids):
                if cls_id == 0: # Person
                    person_boxes.append(box)
                elif cls_id == 3: # Motorcycle
                    motorcycle_boxes.append((box, track_id))

        # --- STEP B: Process Each Motorcycle ---
        for m_box, m_track_id in motorcycle_boxes:
            x1, y1, x2, y2 = map(int, m_box)
            
            # 1. Count persons on this motorcycle
            person_count = 0
            for p_box in person_boxes:
                # Check if the person's center is within the motorcycle's box
                px_center = (p_box[0] + p_box[2]) / 2
                py_center = (p_box[1] + p_box[3]) / 2
                if x1 < px_center < x2 and y1 < py_center < y2:
                    person_count += 1

            # 2. Crop motorcycle region for custom model
            motorcycle_roi = frame[y1:y2, x1:x2]
            if motorcycle_roi.size == 0:
                continue

            # --- STEP C: Run Custom Model on Motorcycle ROI ---
            custom_results = model_custom(motorcycle_roi, verbose=False)

            helmet_status = "Unknown"
            plate_number = "Not Detected"
            
            for res in custom_results:
                for box in res.boxes:
                    cls_id = int(box.cls[0])
                    class_name = custom_names[cls_id]
                    
                    if class_name == 'without helmet':
                        helmet_status = "Without Helmet"
                    elif class_name == 'with helmet' and helmet_status != 'Without Helmet':
                        helmet_status = "With Helmet"
                    
                    elif class_name == 'plate':
                        # Crop the plate from the ROI
                        px1, py1, px2, py2 = map(int, box.xyxy[0])
                        plate_crop = motorcycle_roi[py1:py2, px1:px2]
                        if plate_crop.size > 0:
                            plate_number = extract_plate_text(plate_crop)

            # --- STEP D: Log to CSV ---
            # Log if we have a clear helmet status
            if helmet_status != "Unknown":
                timestamp = datetime.datetime.now().isoformat()
                log_data = [timestamp, plate_number, helmet_status, person_count]
                print(f"Logging to CSV: {log_data}")
                log_to_csv(log_data)
                
                # --- STEP E: Send Violation to Backend ---
                if helmet_status == "Without Helmet":
                    evidence_img = capture_evidence(frame, m_box)
                    violations_to_send_backend.append({
                        "type": f"Without Helmet (Persons: {person_count}, Plate: {plate_number})",
                        "timestamp": timestamp,
                        "gps": "12.9716,77.5946", # Example GPS
                        "evidence": evidence_img
                    })

            # Draw annotations (optional)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated_frame, f"ID: {m_track_id} P: {person_count} H: {helmet_status} L: {plate_number}", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Send all detected violations for this frame at once
        if violations_to_send_backend:
            send_to_backend(violations_to_send_backend)

        # Display the feed
        cv2.imshow("Local Video Test", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Video processing finished.")

if __name__ == "__main__":
    main()