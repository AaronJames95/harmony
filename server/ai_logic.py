import whisper
import torch
import gc
import os
import time
import requests
import json
from .notifier import deliver_transcript

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3" 

SYSTEM_PROMPT = """
You are an expert assistant analyzing an audio transcript.
Note: The audio might be a meeting, a voice note, or a music/worship practice session containing lyrics.

Your Goal:
1. Identify the *type* of session (e.g., "Music Practice", "Meeting", "Personal Note").
2. Provide a concise bulleted summary of the content.
3. If the text is mostly song lyrics, just list the songs played.
4. Extract any specific Action Items or Tasks mentioned.
"""
# ---------------------

def purge_vram(model_obj=None):
    if model_obj:
        del model_obj
    torch.cuda.empty_cache()
    gc.collect()
    print("🧹 VRAM Purged (Whisper).")

def call_ollama(prompt, unload=False):
    """
    Sends a prompt to Ollama.
    :param unload: If True, forces Ollama to free VRAM immediately after this response.
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 4096
            }
        }
        
        # ⚡ KEY CHANGE: Control memory persistence
        if unload:
            payload["keep_alive"] = 0 
        
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        print(f"❌ Ollama Error: {e}")
        return None

def summarize_with_ollama(full_text):
    print(f"🦙 Sending to Ollama ({OLLAMA_MODEL})...")
    
    # 1. SHORT FILES (No Chunking)
    if len(full_text.split()) < 50:
        # Unload immediately since we are done
        return call_ollama(f"Summarize this briefly:\n{full_text}", unload=True)

    # 2. LONG FILES (Map-Reduce)
    chunk_size = 12000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    if len(chunks) == 1:
        # Fits in one go -> Unload immediately
        return call_ollama(f"{SYSTEM_PROMPT}\n\nTRANSCRIPT:\n{full_text}", unload=True)
    
    # Process multiple chunks
    print(f"📄 Splitting into {len(chunks)} parts for analysis...")
    partial_summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"   ...Processing Part {i+1}/{len(chunks)}")
        # Keep model loaded between chunks for speed (unload=False)
        summary = call_ollama(f"Summarize this segment of a transcript:\n\n{chunk}", unload=False)
        if summary:
            partial_summaries.append(summary)

    # Final consolidation
    print("🔗 Combining summaries...")
    master_summary = "\n".join(partial_summaries)
    
    # ⚡ FINAL STEP: Unload immediately because the job is done
    return call_ollama(f"{SYSTEM_PROMPT}\n\nHere are summaries of the different parts of the recording. Combine them into one coherent report:\n\n{master_summary}", unload=True)

def run_transcription_pipeline(file_path, original_name):
    try:
        # --- PHASE 1: TRANSCRIPTION ---
        print(f"🧠 Loading Whisper for: {original_name}")
        model = whisper.load_model("medium") 
        
        # Force English to stop Welsh hallucinations
        result = model.transcribe(file_path, language="en", condition_on_previous_text=False)
        full_text = result['text']
        segments = result['segments']
        
        # Purge Whisper
        purge_vram(model)

        # --- PHASE 2: OLLAMA SUMMARIZATION ---
        # (Inside this function, we handle the keep_alive logic)
        summary = summarize_with_ollama(full_text)
        
        if not summary:
            summary = "Summary unavailable (Ollama connection failed)."

        # --- PHASE 3: OUTPUT ---
        md_output = f"#transcript #ai_gen\n\n"
        md_output += f"# {original_name}\n\n"
        md_output += f"### 🦙 AI Summary\n{summary}\n\n"
        md_output += "---\n\n"
        md_output += "### ⏱️ Timestamped Transcript\n"
        for segment in segments:
            start = time.strftime('%H:%M:%S', time.gmtime(segment['start']))
            md_output += f"**[{start}]** {segment['text']}  \n"

        deliver_transcript(md_output, original_name)

    except Exception as e:
        print(f"❌ AI Pipeline Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)