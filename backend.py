# Save this as backend.py (UPDATED VERSION)
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import uvicorn
import shutil
import os
import json # <-- Import json

# --- Conceptual Database ---
fake_db = []
# ---------------------------

os.makedirs("uploads", exist_ok=True)
app = FastAPI()

# Pydantic model for the event data
class ViolationEvent(BaseModel):
    violation_type: str
    timestamp: str
    gps: str
    camera_id: str

@app.post("/api/v1/log_violation/")
async def log_violation(
    # This is the key change:
    # We now expect a string from a form field named 'event_data_str'
    event_data_str: str = Form(...), 
    evidence_file: UploadFile = File(...)
):
    try:
        # Parse the JSON string back into our Pydantic model
        event_data = ViolationEvent.model_validate_json(event_data_str)
    except Exception as e:
        # If parsing fails, it's a bad request
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")

    # 1. Save the evidence file
    # Use a unique filename based on timestamp + original name
    safe_filename = f"{event_data.timestamp.replace(':', '-')}_{evidence_file.filename}"
    evidence_path = f"uploads/{safe_filename}"
    
    with open(evidence_path, "wb") as buffer:
        shutil.copyfileobj(evidence_file.file, buffer)
    
    # 2. Log to our fake database
    event_id = len(fake_db) + 1
    new_event = {
        "id": event_id,
        "data": event_data.model_dump(), # Convert Pydantic model to dict
        "evidence_path": evidence_path,
        "status": "pending_review"
    }
    fake_db.append(new_event)
    
    print(f"--- VIOLATION LOGGED ---")
    print(f"ID: {event_id}, Type: {event_data.violation_type}")
    print(f"Evidence saved to: {evidence_path}")
    print("-------------------------")
    
    return {"status": "success", "event_id": event_id}

@app.get("/api/v1/dashboard/pending_violations")
def get_pending_violations():
    pending = [event for event in fake_db if event["status"] == "pending_review"]
    return {"violations": pending}

if __name__ == "__main__":
    print("Starting backend server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)