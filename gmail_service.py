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

def fetch_unread_emails(service):
    """Fetches a list of unread email messages."""
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = results.get('messages', [])
    return messages

def get_email_details(service, message_id):
    """
    Gets the full details of a single email, with robust body parsing for
    multipart messages.
    """
    msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    
    payload = msg['payload']
    headers = payload.get('headers', [])
    
    email_data = {
        'id': msg['id'],
        'threadId': msg['threadId'],
        'snippet': msg.get('snippet'),
        'from': next((h['value'] for h in headers if h['name'].lower() == 'from'), 'N/A'),
        'to': next((h['value'] for h in headers if h['name'].lower() == 'to'), 'N/A'),
        'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'N/A'),
        'in_reply_to': next((h['value'] for h in headers if h['name'].lower() == 'in-reply-to'), None),
        'body': ''
    }

    def find_body_parts(parts):
        """Recursively search for the email body in multipart messages."""
        body = ''
        for part in parts:
            if part.get('body') and part['body'].get('data'):
                # Prioritize plain text over HTML
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')

            if 'parts' in part:
                sub_body = find_body_parts(part['parts'])
                if sub_body:
                    return sub_body
        return body
    if 'parts' in payload:
        email_data['body'] = find_body_parts(payload['parts'])
    elif 'body' in payload and 'data' in payload['body']:
        data = payload['body']['data']
        email_data['body'] = base64.urlsafe_b64decode(data).decode('utf-8')

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