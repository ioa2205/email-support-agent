import logging
import time
import json
from database import get_db_connection
import gmail_service
import processing_service
from google.oauth2.credentials import Credentials
import os
import psycopg2.extras

def main():
    """Main loop to fetch and process emails."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("agent.log"), 
            logging.StreamHandler()         
        ]
    )
    logging.info("Starting email listener...")

    # Load Google Client ID and Secret for token refreshing
    with open('client_secret.json', 'r') as f:
        secrets = json.load(f)['web']
        os.environ['GOOGLE_CLIENT_ID'] = secrets['client_id']
        os.environ['GOOGLE_CLIENT_SECRET'] = secrets['client_secret']

    while True:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cur.execute("SELECT * FROM connected_accounts;")
            accounts = cur.fetchall()
            
            if not accounts:
                print("No connected accounts found. Please run app.py to connect an account.")
                time.sleep(60)
                continue

            for account in accounts:
                print(f"\nChecking account: {account['user_email']}")
                
                try:
                    # Manually create credentials object from DB data
                    creds_info = {
                        'token': account['access_token'],
                        'refresh_token': account['refresh_token'],
                        'token_uri': 'https://oauth2.googleapis.com/token',
                        'client_id': secrets['client_id'],
                        'client_secret': secrets['client_secret'],
                        'scopes': gmail_service.SCOPES
                    }
                    
                    creds = Credentials.from_authorized_user_info(creds_info)
                    
                    # Refresh if expired and update DB
                    if creds.expired and creds.refresh_token:
                        from google.auth.transport.requests import Request
                        print("Refreshing token...")
                        creds.refresh(Request())
                        # Save the updated credentials back to the database
                        cur.execute(
                            """
                            UPDATE connected_accounts SET access_token = %s, token_expiry = %s
                            WHERE user_email = %s
                            """,
                            (creds.token, creds.expiry, account['user_email'])
                        )
                        conn.commit()
                        print("Token refreshed and saved.")


                    service = gmail_service.build('gmail', 'v1', credentials=creds)
                    unread_messages = gmail_service.fetch_unread_emails(service)
                    
                    if not unread_messages:
                        print("No new emails.")
                    else:
                        print(f"Found {len(unread_messages)} new email(s).")
                        for message_summary in unread_messages:
                            # Pass a dictionary-like object for the account
                            processing_service.process_email(dict(account), message_summary)

                except Exception as e:
                    print(f"An error occurred while processing account {account['user_email']}: {e}")
            
            cur.close()
            
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Database error: {error}")
        finally:
            if conn is not None:
                conn.close()
        
        print("\nWaiting for 30 seconds before next check...")
        time.sleep(30)

if __name__ == '__main__':
    main()