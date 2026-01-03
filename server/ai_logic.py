import whisper
import torch
import gc
import os
import time
from .notifier import deliver_transcript # This is what triggered the error

def run_transcription_pipeline(file_path, original_name):
    try:
        print(f"🧠 Loading AI Model for: {original_name}")
        model = whisper.load_model("medium") 
        result = model.transcribe(file_path)
        
        # Format the text
        md_output = f"# Transcript: {original_name}\n\n"
        for segment in result['segments']:
            start = time.strftime('%H:%M:%S', time.gmtime(segment['start']))
            md_output += f"**[{start}]** {segment['text']}  \n"

        # Deliver the result via the notifier
        deliver_transcript(md_output, original_name)
        
        # --- VRAM PURGE ---
        del model
        torch.cuda.empty_cache()
        gc.collect()
        print("🧹 VRAM Purged.")

    except Exception as e:
        print(f"❌ AI Pipeline Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)