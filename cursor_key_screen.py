import flet as ft
import time
from datetime import datetime
import csv
import threading

def main(page: ft.Page):
    page.title = "High-Speed Heartbeat Logger"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.START
    
    # 1. Setup the UI Components
    # Using a ListView for high-performance scrolling of text chunks
    log_display = ft.ListView(
        expand=True, 
        spacing=0, 
        auto_scroll=True,
        padding=10
    )

    # Status indicator (The heartbeat visual)
    status_text = ft.Text("System Active", color=ft.colors.GREEN_400)

    # Add to page
    page.add(
        ft.Row([ft.Icon(ft.icons.REORDER), ft.Text("Real-Time Data Stream", weight="bold")]),
        ft.Divider(),
        ft.Container(
            content=log_display,
            border=ft.border.all(1, ft.colors.WHITE24),
            border_radius=10,
            expand=True,
        ),
        status_text
    )

    # 2. Setup Persistent Logging
    filename = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    f = open(filename, 'w', newline='', buffering=1)
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Unix_Time", "Content"])

    def on_close(e):
        f.close()
        print("Log saved. Closing...")

    page.on_close = on_close

    # 3. The Listener Logic
    def continuous_listener():
        while True:
            # --- REPLACE THIS WITH YOUR MICROSOFT SPEECH CALL ---
            check_time = time.time()
            readable_time = datetime.fromtimestamp(check_time).strftime('%H:%M:%S.%f')[:-3]
            
            # Simulated data every 3 seconds for testing
            if int(check_time) % 3 == 0:
                text_data = "Heartbeat pulse detected..."
            else:
                text_data = ""
            # ----------------------------------------------------

            if text_data:
                # Log to CSV
                writer.writerow([readable_time, check_time, text_data])
                
                # Update UI immediately
                log_display.controls.append(
                    ft.Text(f"[{readable_time}] {text_data}", font_family="Consolas")
                )
                
                # Batch update the page (Flet handles the high-speed rendering)
                page.update()

            time.sleep(0.1) # Check frequency

    # Start the thread
    thread = threading.Thread(target=continuous_listener, daemon=True)
    thread.start()

def run():
    ft.app(target=main)