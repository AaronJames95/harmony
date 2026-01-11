import sqlite3
import time
import os
from datetime import datetime

class DatabaseService:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Creates necessary tables if they don't exist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS text_logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, unix_time REAL, text_chunk TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS command_logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, command_type TEXT, raw_text TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS temp_capture 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, text_fragment TEXT)''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Database Init Error: {e}")

    def log_command(self, session_id, command_id, raw_text):
        """Records a voice command."""
        try:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            conn = self._get_connection()
            conn.cursor().execute(
                "INSERT INTO command_logs (session_id, timestamp, command_type, raw_text) VALUES (?, ?, ?, ?)", 
                (session_id, ts, command_id, raw_text)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ DB Log Command Error: {e}")

    def log_text_chunk(self, session_id, text):
        """Records a standard dictation chunk."""
        try:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            unix = time.time()
            conn = self._get_connection()
            conn.cursor().execute(
                "INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)", 
                (session_id, ts, unix, text)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ DB Log Text Error: {e}")

    def save_temp_fragment(self, text):
        """Saves a fragment during Deep State mode."""
        try:
            conn = self._get_connection()
            conn.cursor().execute("INSERT INTO temp_capture (text_fragment) VALUES (?)", (text,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ DB Backup Failed: {e}")

    def clear_temp_fragments(self):
        """Wipes the Deep State buffer."""
        try:
            conn = self._get_connection()
            conn.cursor().execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ DB Clear Temp Error: {e}")

    def get_and_clear_temp_fragments(self):
        """Retrieves all Deep State fragments and clears the table."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT text_fragment FROM temp_capture ORDER BY id ASC")
            fragments = [row[0] for row in cursor.fetchall()]
            
            # Atomic clear after read
            cursor.execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
            return fragments
        except Exception as e:
            print(f"❌ DB Retrieve Failed: {e}")
            return []

    def export_history_to_file(self, output_dir):
        """Exports all logs to a human-readable text file."""
        output_path = os.path.join(output_dir, "human_readable_history.txt")
        try:
            conn = self._get_connection()
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
                        date_str = datetime.fromtimestamp(sess_id).strftime('%Y-%m-%d %H:%M:%S')
                        f.write(f"\n{'='*40}\n SESSION: {date_str}\n{'='*40}\n")
                        current_session = sess_id
                    
                    if entry_type == 'SPEECH':
                        f.write(f"[{ts}] {content}\n")
                    else:
                        f.write(f"[{ts}] ✨ ACTION: {content}\n")
            return output_path
        except Exception as e:
            print(f"❌ Export Failed: {e}")
            return None