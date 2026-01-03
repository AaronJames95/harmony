import pandas as pd
import sqlite3
import os
import glob
import re

# Since you are running this INSIDE the logs folder:
DB_PATH = "harmony_main.db"
CSV_PATTERN = "ingest_*.csv"

def get_session_id(filename):
    """Extracts the unix timestamp from the filename."""
    match = re.search(r"ingest_(\d+)", filename)
    return int(match.group(1)) if match else 0

def migrate():
    # 1. Verify DB exists in this current folder
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found! Make sure '{DB_PATH}' is in this folder.")
        # Optional: create it if missing
        # return 
        
    # 2. Find CSVs in this current folder
    csv_files = glob.glob(CSV_PATTERN)
    
    if not csv_files:
        print(f"❓ Still no CSV files found. Current directory is: {os.getcwd()}")
        print(f"Files actually present: {os.listdir('.')}")
        return

    print(f"Found {len(csv_files)} files to process...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                print(f"Empty file skipped: {file_path}")
                continue

            session_id = get_session_id(file_path)
            
            # Detect Cumulative vs Incremental
            is_cumulative = False
            if len(df) > 1:
                first_row = str(df.iloc[0]['Text'])
                second_row = str(df.iloc[1]['Text'])
                if second_row.startswith(first_row) and len(second_row) > len(first_row):
                    is_cumulative = True

            if is_cumulative:
                print(f"📦 {file_path}: Cumulative. Taking final row.")
                row = df.iloc[-1]
                cursor.execute(
                    "INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)",
                    (session_id, row['Time'], row['Unix'], row['Text'])
                )
            else:
                print(f"📥 {file_path}: Incremental. Importing {len(df)} rows.")
                for _, row in df.iterrows():
                    cursor.execute(
                        "INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)",
                        (session_id, row['Time'], row['Unix'], row['Text'])
                    )
            
            conn.commit()
        except Exception as e:
            print(f"⚠️ Failed to process {file_path}: {e}")

    conn.close()
    print("\n✅ Migration complete.")

if __name__ == "__main__":
    migrate()