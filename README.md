
# 🚦 AI Traffic Violation Detection System

This project is an **AI-powered solution** designed to automatically detect, log, and report various traffic violations in real-time using standard CCTV or mobile cameras. It leverages **computer vision models** to identify violations, **OCR** to extract license plate data, and a **web backend** to manage and review evidence.

> Based on the "Zeex AI" solution concept, this system is designed to be low-cost, scalable, and a significant improvement over manual enforcement methods. [cite: 2, 4, 7]

---

## 📋 Features

### **Multi-Violation Detection**
- No Helmet Driving. [cite: 10]
- Triple Riding (detects person count on motorcycles).
- License Plate Detection and OCR.
- (Extendable to) Red Light Jumping, Mobile Use, etc. [cite: 9, 11]

### **Real-Time Processing**
- Analyzes live video streams or local video files.

### **Automatic Data Logging**
- Logs all detected events (Timestamp, Plate Number, Helmet Status, Person Count) to a local `violations_log.csv`.

### **Evidence Generation**
- Captures and saves image evidence for critical violations (e.g., "Without Helmet"). [cite: 25, 28]

### **Review Dashboard**
- A FastAPI backend receives violation data, which can be reviewed, approved, or rejected via a dashboard. [cite: 32, 34]

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **AI / Computer Vision** | **YOLOv8 (Ultralytics)** | Used for primary object detection. Two models are used: `yolov8n.pt` (for persons, motorcycles) and a custom `best.pt` (for helmet, no-helmet, plate). [cite: 23, 44] |
|  | **EasyOCR** | For optical character recognition to extract text from detected license plates. |
|  | **OpenCV** | For video stream handling, image processing, and tracking. [cite: 44] |
| **Backend** | **FastAPI** | High-performance Python framework for building the API that receives violation data from the AI script. [cite: 42] |
| **Data Output** | **CSV** | A simple `violations_log.csv` file for logging all detected motorcycle events. |
| **File Storage** | **uploads/** | Directory to store cropped image evidence of violations. |

---

## ⚙️ System Workflow

1. **Capture:** The `local_test.py` script reads a video file (or stream) frame by frame. [cite: 21]
2. **General Detection:** The `yolov8n.pt` model detects all `persons` and `motorcycles` in the frame.
3. **Violation Analysis:**
   - The system associates persons with motorcycles to get a `person_count`.
   - A cropped Region of Interest (ROI) for each motorcycle is passed to the custom `best.pt` model.
   - The custom model detects `with helmet`, `without helmet`, and `plate`.
4. **Data Extraction (OCR):**
   - If a `plate` is detected, the cropped plate image is sent to EasyOCR to extract the license plate number.
5. **Logging (CSV):**
   - A new row is appended to `violations_log.csv` with the `Timestamp`, `Plate Number`, `Helmet Status`, and `Person Count`.
6. **Event Generation (Backend):**
   - If `without helmet` is detected, the script captures image evidence and sends the full violation details (type, timestamp, evidence) to the FastAPI `backend.py` server. [cite: 27]
7. **Review:**
   - The backend saves the evidence to the `uploads/` folder and logs the event in its database (currently in-memory) with a `pending_review` status, making it available for the dashboard. [cite: 32]

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PyTorch (with CUDA support recommended)
- Git

---

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/Traffic-Violation.git
cd Traffic-Violation
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the required dependencies:**
```bash
pip install "fastapi[all]" uvicorn ultralytics opencv-python-headless requests numpy easyocr
```
*(Note: Use `opencv-python` if you need to see the display window locally instead of `opencv-python-headless`)*

4. **Place your models:**
- Download the pre-trained `yolov8n.pt` or let Ultralytics handle it.
- Place your custom trained model in the specified path, e.g., `models/best.pt`. (Update the `MODEL_CUSTOM_PATH` variable in `local_test.py` accordingly).

5. **Edit the video source:**
- Open `local_test.py` and change the `VIDEO_SOURCE` variable to the path of your test video file.

---

## ▶️ How to Run

You need to run two separate processes in two terminals.

**Terminal 1: Start the Backend Server**

This server will listen for violation reports from the AI script.

```bash
python backend.py
```

You should see:
```
Starting backend server on http://127.0.0.1:8000
```

**Terminal 2: Run the AI Detection Script**

This script will process the video, log to CSV, and send violations to the backend.

Note: To avoid a common library conflict (OMP: Error #15) between PyTorch and OpenCV, run using the KMP_DUPLICATE_LIB_OK=TRUE environment variable.

Bash
```bash
# On Linux/macOS/Git Bash
KMP_DUPLICATE_LIB_OK=TRUE python local_test.py
```

Windows Command Prompt (CMD)
```cmd
set KMP_DUPLICATE_LIB_OK=TRUE
python local_test.py
```

Windows PowerShell
```powershell
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python local_test.py
```

---

### Expected Output

Terminal 1 (Backend):
Will print a --- VIOLATION LOGGED --- message every time a "Without Helmet" violation is received.

Terminal 2 (AI Script):
Will print console output for each event logged to the CSV and each violation sent to the backend. An OpenCV window will open showing the real-time detections.

File System:
- `violations_log.csv`: This file will be created/updated with data for all processed motorcycles.
- `uploads/` (folder): This folder will fill with JPEG evidence images for "Without Helmet" violations.

Browser:
You can check the dashboard endpoint at:
```
http://127.0.0.1:8000/api/v1/dashboard/pending_violations
```
to see the JSON list of violations awaiting review.

---

## 📈 Future Scalability

- Full Dashboard: Develop the React/Flutter frontend to review, approve, and reject violations.
- Database Integration: Replace the in-memory fake_db with a robust database (e.g., PostgreSQL, MongoDB).
- Challan Integration: Connect to RTO databases for automatic e-challan generation upon approval.
- Expand Violations: Add modules for speed detection, wrong-way driving, and red-light jumping.

---

## Project Files & Structure

```
Traffic-Violation/
├── backend.py
├── local_test.py
├── requirements.txt
├── models/
│   ├── yolov8n.pt
│   └── best.pt
├── uploads/
├── violations_log.csv
└── README.md
```

---

## Sample Output

| Field | Example |
| :--- | :--- |
| Timestamp | 2025-11-07 12:45:09 |
| Plate Number | TN09AB1234 |
| Helmet Status | Without Helmet |
| Person Count | 2 |
| Evidence Path | uploads/violation_20251107_124509.jpg |

---

## Citations & References

Based on (and inspired by) multiple sources and solution concepts:
- Zeex AI Traffic Detection System and whitepapers. [cite: 2, 4, 7]
- Ultralytics YOLOv8 Documentation. [cite: 23, 44]
- EasyOCR and OpenCV usage guides. [cite: 25, 28, 44]
- FastAPI implementation references. [cite: 32, 34, 42]
- Research literature on helmet detection and multi-person counting. [cite: 9, 10, 11]

---
