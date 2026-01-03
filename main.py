import platform
import subprocess
import sys
import os

def start_server():
    print("🧠 Starting Muscular AI Server...")
    env = os.environ.copy()
    # Forces Python to use ONLY the Mamba environment libraries
    env["PYTHONNOUSERSITE"] = "1" 
    
    cmd = [sys.executable, "-m", "uvicorn", "server.server_main:app", "--host", "0.0.0.0", "--port", "8000"]
    subprocess.run(cmd, env=env)

def start_client():
    """Launches the HUD HUD on Windows."""
    print("🖥️ Starting Harmony HUD Client...")
    # Points to your existing client main
    client_main = os.path.join("client", "main.py")
    subprocess.run([sys.executable, client_main])

if __name__ == "__main__":
    current_os = platform.system()
    
    if current_os == "Linux":
        start_server()
    elif current_os == "Windows":
        start_client()
    else:
        print(f"❌ OS {current_os} not supported.")