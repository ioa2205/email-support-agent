import base64
import os
import re
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_credentials(account):
    """Refreshes credentials if necessary."""
    creds = Credentials(
        token=account['access_token'],
        refresh_token=account['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'), # You would get this from client_secret.json
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
    )
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # TODO: Here you should update the new credentials in your database
    return creds

def get_gmail_service(account):
    """Returns an authorized Gmail service instance."""
    creds = get_credentials(account)
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_unread_emails(service):
    """Fetches a list of unread email messages."""
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = results.get('messages', [])
    return messages

def get_email_details(service, message_id):
    """Gets the full details of a single email."""
    msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    
    payload = msg['payload']
    headers = payload['headers']
    
    email_data = {
        'id': msg['id'],
        'threadId': msg['threadId'],
        'snippet': msg['snippet'],
        'from': next(h['value'] for h in headers if h['name'] == 'From'),
        'to': next(h['value'] for h in headers if h['name'] == 'To'),
        'subject': next(h['value'] for h in headers if h['name'] == 'Subject'),
        'in_reply_to': next((h['value'] for h in headers if h['name'] == 'In-Reply-To'), None)
    }

    # Decode the body
    if 'parts' in payload:
        part = payload['parts'][0]
        if part['mimeType'] == 'text/plain':
            data = part['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            email_data['body'] = body
    else:
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8')
        email_data['body'] = body

    return email_data

def send_reply(service, to, subject, body, thread_id):
    """Sends a reply email."""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    
    create_message = {
        'raw': base64.urlsafe_b64encode(message.as_bytes()).decode(),
        'threadId': thread_id
    }
    
    sent_message = service.users().messages().send(userId='me', body=create_message).execute()
    print(f"Sent reply message ID: {sent_message['id']}")

def mark_as_read(service, message_id):
    """Marks an email as read by removing the UNREAD label."""
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    print(f"Marked message {message_id} as read.")

def clean_email_body(raw_body):
    """A simple function to clean email content."""
    body = re.sub(r'<[^>]+>', '', raw_body)
    body = re.sub(r'On.*wrote:', '', body, flags=re.DOTALL)
    body = '\n'.join([line for line in body.split('\n') if not line.strip().startswith('>')])
    return body.strip()