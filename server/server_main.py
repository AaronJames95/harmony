import os
import uuid
import shutil
import torch
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from .ai_logic import run_transcription_pipeline

app = FastAPI()

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
os.makedirs(INBOX_DIR, exist_ok=True)

@app.get("/")
def health_check():
    """Simple ping to check if server is reachable."""
    return {"status": "Harmony Muscular Server is Active"}

@app.get("/stats")
def get_server_stats():
    """
    HUD ENDPOINT: Returns GPU VRAM usage and Server Status.
    Called by the Client HUD every 2 seconds.
    """
    vram_used_gb = 0
    vram_total_gb = 24.0 # Default fallback (RTX 3090 size)
    gpu_name = "CPU Mode"
    
    if torch.cuda.is_available():
        try:
            # Returns (free_bytes, total_bytes)
            free, total = torch.cuda.mem_get_info()
            
            vram_used_gb = (total - free) / (1024**3)
            vram_total_gb = total / (1024**3)
            gpu_name = torch.cuda.get_device_name(0)
        except Exception as e:
            print(f"⚠️ GPU Stats Error: {e}")
            
    return {
        "status": "ONLINE",
        "gpu": gpu_name,
        "vram_used": round(vram_used_gb, 1),
        "vram_total": round(vram_total_gb, 1),
        # Calculate percentage for the progress bar (0-100)
        "vram_percent": int((vram_used_gb / vram_total_gb) * 100) if vram_total_gb > 0 else 0
    }

@app.post("/transcribe")
async def receive_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Ingests files (audio/video), saves them to 'inbox', 
    and triggers the AI Pipeline in the background.
    """
    # Create unique job ID
    job_id = str(uuid.uuid4())[:8]
    filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(INBOX_DIR, filename)
    
    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    print(f"📥 Received: {file.filename} (Job: {job_id})")
    
    # Trigger AI Logic (Whisper -> Ollama)
    background_tasks.add_task(run_transcription_pipeline, file_path, file.filename)
    
    return {"status": "Queued", "job_id": job_id}