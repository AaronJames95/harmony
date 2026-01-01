import tkinter as tk
from tkinter import scrolledtext
import queue
import threading
import time
from datetime import datetime
import csv

class PrecisionLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Heartbeat & Text Log")
        self.text_queue = queue.Queue()
        
        # UI Setup
        self.text_area = scrolledtext.ScrolledText(root, height=20, width=80, font=("Consolas", 10))
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # FIX: Open file handle once for the life of the app
        self.filename = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.f = open(self.filename, 'w', newline='', buffering=1)
        self.writer = csv.writer(self.f)
        self.writer.writerow(["Timestamp", "Unix_Time", "Content_Length", "Content"])

        self.update_ui_loop()

    def update_ui_loop(self):
        # FIX: Drain the entire queue every 10ms to prevent "lagging" behind
        while not self.text_queue.empty():
            try:
                packet = self.text_queue.get_nowait()
                raw_time = packet['time']
                readable_time = datetime.fromtimestamp(raw_time).strftime('%H:%M:%S.%f')[:-3]
                content = packet['text']

                # Fast write
                self.writer.writerow([readable_time, raw_time, len(content), content])

                if content.strip():
                    #self.text_area.insert(tk.END, f"[{readable_time}] Data: {content}\n")
                    self.text_area.see(tk.END)
                    pass
            except queue.Empty:
                break
        
        self.root.after(10, self.update_ui_loop)

    def on_closing(self):
        """Important: Closes the file properly so data isn't lost."""
        self.f.close()
        self.root.destroy()

def continuous_listener(q):
    """Your data source. Replace the logic inside with your Whisper code."""
    while True:
        check_time = time.time()
        
        # Example logic: Only sends text every 5 seconds
        if int(check_time) % 5 == 0:
            text_data = "Heartbeat pulse detected."
        else:
            text_data = ""

        q.put({"text": text_data, "time": check_time})
        
        # Frequency of the heartbeat check
        time.sleep(.1) 

def run():
    root = tk.Tk()
    app = PrecisionLoggerApp(root)
    
    # Ensures the file closes when you click the 'X'
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the background thread
    threading.Thread(target=continuous_listener, args=(app.text_queue,), daemon=True).start()
    
    root.mainloop()

if __name__ == "__main__":
    run()