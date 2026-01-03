import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
# Ensure ai_logic is in the same folder or properly accessible
from .ai_logic import run_transcription_pipeline

# THIS IS THE MISSING LINE
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
os.makedirs(INBOX_DIR, exist_ok=True)

@app.get("/")
def health_check():
    return {"status": "Harmony Muscular Server is Active"}

@app.post("/transcribe")
async def receive_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())[:8]
    filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(INBOX_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    print(f"📥 Received: {file.filename} (Job: {job_id})")
    background_tasks.add_task(run_transcription_pipeline, file_path, file.filename)
    
    return {"status": "Queued", "job_id": job_id}