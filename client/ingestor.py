import csv
import time
import os
import threading
import webbrowser
from datetime import datetime

class Ingestor:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.last_len = 0
        self.log_name = os.path.join(self.log_dir, f"ingest_{int(time.time())}.csv")
        self.buffer = ""
        self.timer = None
        
        # Initialize CSV headers
        with open(self.log_name, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Time", "Unix", "Text"])

    def ingest(self, full_text):
        """
        Main entry point called by the Overlay Signal.
        """
        current_len = len(full_text)
        
        if current_len > self.last_len:
            # Capture only the newly added characters
            new_data = full_text[self.last_len:]
            self.buffer += new_data
            self.last_len = current_len

            # Reset the 'speech pause' timer (0.3s)
            if self.timer:
                self.timer.cancel()
            
            self.timer = threading.Timer(0.3, self.flush_buffer)
            self.timer.start()

        elif current_len < self.last_len:
            # Handles manual deletions in the text box
            self.last_len = current_len

    def flush_buffer(self):
        """
        Triggered when you pause speaking. 
        Logs to CSV and checks for 'Shema' commands.
        """
        text_to_save = self.buffer.strip()
        if text_to_save:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # 1. Log to CSV
            with open(self.log_name, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([ts, time.time(), text_to_save])
            
            # 2. Print to console for debugging
            print(f"[{ts}] Logged: {text_to_save}")
            
            # 3. Process Voice Commands
            self.process_commands(text_to_save)
            
        self.buffer = "" # Reset for next chunk

    def process_commands(self, text):
        """
        The Switch Statement for your 'Shema' voice macros.
        """
        clean_text = text.lower()
        
        if "shema" in clean_text:
            print("✨ Trigger Detected: Shema")
            
            # Switch Logic
            if "shema gemini" in clean_text:
                print("🚀 Opening Gemini...")
                webbrowser.open("https://gemini.google.com/app")
                #self.gemini_prompt
                
            elif "shema shabbat" in clean_text:
                print("⚖️ Command: Emet (Verification)")
                # Logic for Emet can go here

            elif "emet" in clean_text:
                print("⚖️ Command: Emet (Verification)")
                # Logic for Emet can go here
                
            elif "shuv" in clean_text:
                print("🔄 Command: Shuv (Rewind/Summarize)")
                # Logic for Summarization can go here
                
            elif "clear" in clean_text:
                print("🧹 Command: Clear HUD")
                # This would typically emit a signal back to the UI

                def process_voice_commands(self, text):
                    phrase = text.lower()
                    if "shema" in phrase:
                        # The switch statement for commands
                        if "gemini" in phrase:
                            import webbrowser
                            webbrowser.open("https://gemini.google.com/app")
                        elif "emet" in phrase:
                            print("Action: Fact-checking last statement...")
                        elif "shuv" in phrase:
                            self.trigger_rewind_summary()