# Save this as backend.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import uvicorn
import shutil
import os
from typing import List

# --- Conceptual Database ---
# Using a simple list as an in-memory "database" for testing
fake_db = []
# ---------------------------

# Ensure an 'uploads' directory exists
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
    # FastAPI can't parse JSON and a File from the same 'Form'
    # So we must receive the JSON data as a string and parse it.
    event_data_str: str = Form(...),
    evidence_file: UploadFile = File(...)
):
    try:
        # Parse the JSON string back into our Pydantic model
        event_data = ViolationEvent.model_validate_json(event_data_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")

    # 1. Save the evidence file
    evidence_path = f"uploads/{evidence_file.filename}"
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
    """
    Fetches all events from the DB that have status 'pending_review'.
    """
    pending = [event for event in fake_db if event["status"] == "pending_review"]
    return {"violations": pending}

if __name__ == "__main__":
    print("Starting backend server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)