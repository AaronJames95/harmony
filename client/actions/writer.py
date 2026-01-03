import sqlite3
import os
from datetime import datetime

def export_history_to_text(db_path, log_dir):
    """Reconstructs history including both text logs and triggered actions."""
    output_path = os.path.join(log_dir, "human_readable_history.txt")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # We pull from both tables. 
        # For 'text_logs', type is 'SPEECH'. 
        # For 'command_logs', type is 'ACTION'.
        query = '''
            SELECT session_id, timestamp, text_chunk as content, 'SPEECH' as entry_type, unix_time
            FROM text_logs
            UNION ALL
            SELECT session_id, timestamp, command_type as content, 'ACTION' as entry_type, session_id as unix_time
            FROM command_logs
            ORDER BY unix_time ASC, timestamp ASC
        '''
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        with open(output_path, "w", encoding="utf-8") as f:
            current_session = None
            for sess_id, ts, content, entry_type, _ in rows:
                # Header for new sessions
                if sess_id != current_session:
                    readable_date = datetime.fromtimestamp(sess_id).strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"\n{'='*60}\n")
                    f.write(f" SESSION START: {readable_date} (ID: {sess_id})\n")
                    f.write(f"{'='*60}\n")
                    current_session = sess_id
                
                # Format differently based on whether it's speech or a command
                if entry_type == 'SPEECH':
                    f.write(f"[{ts}] {content}\n")
                else:
                    # Visual highlight for commands
                    f.write(f"[{ts}] ✨ ACTION TRIGGERED: {content.upper()}\n")
        
        print(f"📄 Full Audit Log Exported: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False