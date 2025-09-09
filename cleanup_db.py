from database import get_db_connection
import os

# This ensures it connects to the right DB (localhost)
os.environ['DB_HOST'] = 'localhost' 

def clean_accounts():
    """Forcefully deletes all rows from the connected_accounts table."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("--> STEP A: Connecting to the database to clear accounts...")
        
        # This command deletes all data from the table.
        cur.execute("DELETE FROM connected_accounts;")
        
        conn.commit()
        
        # Verify the deletion
        cur.execute("SELECT COUNT(*) FROM connected_accounts;")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("--> SUCCESS: The connected_accounts table is now empty.")
        else:
            print(f"--> ERROR: Cleanup failed. {count} rows still exist.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"--> An error occurred during cleanup: {e}")
        print("    Please ensure your database is running and tables exist (run database.py first).")

if __name__ == '__main__':
    clean_accounts()