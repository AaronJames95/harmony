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

def release_vram(model_obj):
    """
    Nuclear option to force PyTorch to release VRAM back to the OS
    so Ollama can use it.
    """
    print("🧹 Starting VRAM Purge...")

    # 1. Delete the model from Python memory
    del model_obj

    # 2. Force Python Garbage Collection
    gc.collect()

    # 3. Force PyTorch to release cached memory to the OS
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

    print("✨ VRAM Released to OS.")

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
    
    if len(full_text.split()) < 50:
        return call_ollama(f"Summarize this briefly:\n{full_text}", unload=True)

    chunk_size = 12000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    if len(chunks) == 1:
        return call_ollama(f"{SYSTEM_PROMPT}\n\nTRANSCRIPT:\n{full_text}", unload=True)
    
    print(f"📄 Splitting into {len(chunks)} parts for analysis...")
    partial_summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"   ...Processing Part {i+1}/{len(chunks)}")
        # Keep loaded for speed
        summary = call_ollama(f"Summarize this segment of a transcript:\n\n{chunk}", unload=False)
        if summary:
            partial_summaries.append(summary)

    print("🔗 Combining summaries...")
    master_summary = "\n".join(partial_summaries)
    
    # Final cleanup: Unload immediately
    return call_ollama(f"{SYSTEM_PROMPT}\n\nHere are summaries of the different parts of the recording. Combine them into one coherent report:\n\n{master_summary}", unload=True)

def run_transcription_pipeline(file_path, original_name):
    try:
        # --- PHASE 1: TRANSCRIPTION ---
        print(f"🧠 Loading Whisper for: {original_name}")
        model = whisper.load_model("medium") 
        
        result = model.transcribe(file_path, language="en", condition_on_previous_text=False)
        full_text = result['text']
        segments = result['segments']
        
        # --- NUCLEAR VRAM CLEANUP ---
        # This replaces your old 'del model' and 'purge_vram()' lines
        release_vram(model) 
        model = None # Double safety to ensure the variable is dead

        # --- PHASE 2: OLLAMA SUMMARIZATION ---
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