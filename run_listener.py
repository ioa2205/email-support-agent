import logging
import time
import json
from database import get_db_connection
import gmail_service
import processing_service
from google.oauth2.credentials import Credentials
import os
import psycopg2.extras
import traceback
from security import encrypt_token_to_str, decrypt_token_from_str

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
                logging.info("No connected accounts found. Please run app.py to connect an account.")
                time.sleep(60)
                continue

            for account in accounts:
                logging.info(f"\nChecking account: {account['user_email']}")
                
                try:
                    # Manually create credentials object from DB data
                    decrypted_access_token = decrypt_token_from_str(account['access_token'])
                    decrypted_refresh_token = decrypt_token_from_str(account['refresh_token'])
                    creds_info = {
                        'token': decrypted_access_token,
                        'refresh_token': decrypted_refresh_token,
                        'token_uri': 'https://oauth2.googleapis.com/token',
                        'client_id': secrets['client_id'],
                        'client_secret': secrets['client_secret'],
                        'scopes': gmail_service.SCOPES
                    }
                    
                    creds = Credentials.from_authorized_user_info(creds_info)
                    
                    # Refresh if expired and update DB
                    if creds.expired and creds.refresh_token:
                        from google.auth.transport.requests import Request
                        logging.info("Refreshing token...")
                        creds.refresh(Request())
                        # Save the updated credentials back to the database

                        encrypted_new_token = encrypt_token_to_str(creds.token)

                        cur.execute(
                            """
                            UPDATE connected_accounts SET access_token = %s, token_expiry = %s
                            WHERE user_email = %s
                            """,
                            (encrypted_new_token, creds.expiry, account['user_email'])
                        )
                        conn.commit()
                        logging.info("Token refreshed and saved.")


                    service = gmail_service.build('gmail', 'v1', credentials=creds)
                    unread_messages = gmail_service.fetch_unread_emails(service)
                    
                    if not unread_messages:
                        logging.info("No new emails.")
                    else:
                        logging.info(f"Found {len(unread_messages)} new email(s).")
                        for message_summary in unread_messages:
                            # Pass a dictionary-like object for the account
                            processing_service.process_email(dict(account), message_summary)

                except Exception as e:
                    logging.error(f"An error occurred while processing account {account['user_email']}:")
                    logging.error(traceback.format_exc())

            cur.close()
            
        except (Exception, psycopg2.DatabaseError) as error:
            logging.error(f"Database error: {error}")
        finally:
            if conn is not None:
                conn.close()

        logging.info("Waiting for 30 seconds before next check...")
        time.sleep(30)

if __name__ == '__main__':
    main()