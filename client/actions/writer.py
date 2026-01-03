import sqlite3
import os
from datetime import datetime

def export_history_to_text(ingestor):
    db_path = ingestor.db_path
    log_dir = ingestor.log_dir
    output_path = os.path.join(log_dir, "human_readable_history.txt")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

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
                if sess_id != current_session:
                    readable_date = datetime.fromtimestamp(sess_id).strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"\n{'='*40}\n SESSION: {readable_date}\n{'='*40}\n")
                    current_session = sess_id
                
                if entry_type == 'SPEECH':
                    f.write(f"[{ts}] {content}\n")
                else:
                    f.write(f"[{ts}] ✨ ACTION: {content.upper()}\n")
        
        print(f"📄 Log exported to: {output_path}")
    except Exception as e:
        print(f"❌ Export failed: {e}")