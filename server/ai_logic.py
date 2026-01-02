import whisper, torch, gc, os, time
from .notifier import deliver_transcript

def run_transcription_pipeline(file_path, original_name):
    try:
        # Load model only when the muscle is needed
        model = whisper.load_model("medium") 
        result = model.transcribe(file_path)
        
        # Build Markdown with precise timestamps
        md = f"# {original_name}\n\n"
        for s in result['segments']:
            ts = time.strftime('%H:%M:%S', time.gmtime(s['start']))
            md += f"**[{ts}]** {s['text']}  \n"

        deliver_transcript(md, original_name)
        
        # --- PREVENT MEMORY LEAKS ---
        del model
        torch.cuda.empty_cache() # Purge VRAM
        gc.collect()             # Purge System RAM
        
    finally:
        if os.path.exists(file_path): os.remove(file_path)