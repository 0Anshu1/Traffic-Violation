# Save this as run_video.py
import cv2
from ultralytics import YOLO
import requests # Need to install: pip install requests
import datetime
import json
import time

# --- Helper Functions ---

def send_to_backend(violation_list):
    """
    Sends a list of violation events to the backend.
    """
    backend_url = "http://127.0.0.1:8000/api/v1/log_violation/"
    
    for violation in violation_list:
        try:
            # 1. Prepare the JSON data
            # Pydantic model from backend.py:
            # { "violation_type": "...", "timestamp": "...", "gps": "...", "camera_id": "..." }
            event_data = {
                "violation_type": violation["type"],
                "timestamp": violation["timestamp"],
                "gps": violation["gps"],
                "camera_id": "local_cam_01"
            }
            
            # 2. Prepare the evidence image
            # Encode the OpenCV image (numpy array) to JPEG format in memory
            _, img_encoded = cv2.imencode(".jpg", violation["evidence"])
            
            # Create the multipart/form-data payload
            files = {
                # 'event_data_str' must match the Form name in FastAPI
                'event_data_str': (None, json.dumps(event_data), 'application/json'), 
                
                # 'evidence_file' must match the File name in FastAPI
                'evidence_file': (f"{violation['timestamp']}.jpg", img_encoded.tobytes(), 'image/jpeg')
            }
            
            # 3. Send the POST request
            response = requests.post(backend_url, files=files)
            
            if response.status_code == 200:
                print(f"Successfully sent violation: {violation['type']}")
            else:
                print(f"Error sending violation: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Failed to connect or send data to backend: {e}")

def capture_evidence(frame, box):
    # Simple function to crop the violation area
    x1, y1, x2, y2 = map(int, box)
    return frame[y1:y2, x1:x2]

# --- Main Processing ---

# 1. Load the AI Model
model = YOLO('yolov8n.pt') 

# 2. Capture Video Stream
# !! IMPORTANT: Change this to the path of your video file !!
video_source = "path/to/your/video.mp4" 
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print(f"Error: Could not open video file {video_source}")
    exit()

print("Processing video... Press 'q' to quit.")

# 3. Process Frames
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 4. AI Detection & Tracking
    results = model.track(frame, persist=True, classes=[2, 3]) # Class 2=car, 3=motorcycle
    
    annotated_frame = frame.copy()
    if results[0].boxes:
        annotated_frame = results[0].plot()

    # 5. Rule Engine & Violation Logic
    violations = []
    
    # This is a VERY simple demo rule.
    # It flags any motorcycle (class 3) it sees.
    if results[0].boxes.id is not None:
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        boxes = results[0].boxes.xyxy.cpu().tolist()

        for box, cls_id in zip(boxes, class_ids):
            if cls_id == 3: # 3 = motorcycle in COCO dataset
                # 6. Event Generation
                evidence_img = capture_evidence(frame, box)
                violations.append({
                    "type": "demo_motorcycle_detected",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "gps": "12.9716,77.5946", # Example GPS
                    "evidence": evidence_img
                })
                print("Violation detected!")
    
    # 7. Send Violations to Backend
    if violations:
        send_to_backend(violations)
        # Add a small delay to avoid overwhelming the backend in a demo
        time.sleep(1) 

    # Display the feed
    cv2.imshow("Local Video Test", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Video processing finished.")