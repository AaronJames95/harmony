import sqlite3
import os
from datetime import datetime

def export_history_to_text(db_path, log_dir):
    """Reconstructs the database history into a human-readable text file."""
    output_path = os.path.join(log_dir, "human_readable_history.txt")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Sort everything chronologically across all sessions
        cursor.execute("SELECT session_id, timestamp, text_chunk FROM text_logs ORDER BY unix_time ASC")
        rows = cursor.fetchall()
        conn.close()

        with open(output_path, "w", encoding="utf-8") as f:
            current_session = None
            for sess_id, ts, text in rows:
                # Visually separate different sessions
                if sess_id != current_session:
                    readable_date = datetime.fromtimestamp(sess_id).strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"\n--- SESSION START: {readable_date} (ID: {sess_id}) ---\n")
                    current_session = sess_id
                f.write(f"[{ts}] {text}\n")
        
        print(f"📄 Manual Sync Complete: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False