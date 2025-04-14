import os
import sqlite3
import base64
import json

from extraction import extract_emails_from_db
from prompt import query_claude
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from claude_auth import claude_client
from datetime import datetime 

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=8080, prompt='consent')
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def setup_db():
    conn = sqlite3.connect('emails.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            date TEXT,
            classification TEXT
        )
    ''')
    conn.commit()
    return conn

def fetch_and_store_emails(service, db_conn):
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    cursor = db_conn.cursor()

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        snippet = msg_data.get('snippet', '')

        subject = sender = date = message_body = ''

        for h in headers:
            if h['name'] == 'Subject':
                subject = h['value']
            elif h['name'] == 'From':
                sender = h['value']
            elif h['name'] == 'Date':
                date = h['value']

        parts = msg_data.get('payload', {}).get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data', '')
                try:
                    message_body = base64.urlsafe_b64decode(data.encode()).decode(errors='ignore')
                except:
                    message_body = ''
                break

        cursor.execute('''
            INSERT OR IGNORE INTO events (id, subject, sender, date, classification)
            VALUES (?, ?, ?, ?, ?)
        ''', (msg['id'], subject, sender, date, ''))
        db_conn.commit()

    print(f"✅ {len(messages)} emails processed and stored.")

def sync_to_calendar(service, events):
    calendar = build('calendar', 'v3', credentials=service._http.credentials)

    for event in events:
        subject = event.get("Subject") or event.get("title")
        date = event.get("Date") or event.get("event-date")
        message = event.get("Message_body") or event.get("message-body")

        if not subject or not date or not message:
            print(f"⚠️ Skipping malformed event: {event}")
            continue

        try:
            date_obj = datetime.strptime(" ".join(date.split(" ")[1:4]), "%d %b %Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except Exception:
            formatted_date = date

        try:
            calendar.events().insert(
                calendarId='primary',
                body={
                    'summary': subject,
                    'description': message,
                    'start': {'date': formatted_date},
                    'end': {'date': formatted_date}
                }
            ).execute()
            print(f"✅ Synced to calendar: {subject}")
        except HttpError as error:
            print(f"❌ Calendar sync failed for {subject}: {error}")

def main():
    service = authenticate_gmail()
    conn = setup_db()

    fetch_and_store_emails(service, conn)
    emails = extract_emails_from_db()

    events_text = query_claude("extract events", emails, claude_client)
    print("Claude responded with the following events:\n")
    print(events_text)

    try:
        events = json.loads(events_text)
        sync_to_calendar(service, events)
    except json.JSONDecodeError:
        print("❌ Claude returned invalid JSON")
        return

    with open("events.json", "w") as f:
        json.dump(events, f, indent=2)

    print("✅ Events saved to events.json")
    conn.close()
    print("✅ All done!")

if __name__ == '__main__':
    main()
