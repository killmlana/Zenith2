import sqlite3
import json

def extract_emails_from_db(db_path='emails.db', output_path='emails.json'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, sender, subject, date FROM events")
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ SQLite Error: {e}")
        conn.close()
        return []

    emails = []
    for row in rows:
        email = {
            "Sender": row[1],
            "Subject": row[2],
            "Date": row[3],
            "Snippet": row[2],  # fallback to subject as snippet
            "Message_body": ""   # message body will be filled by Claude
        }
        emails.append(email)

    conn.close()

    with open(output_path, 'w') as f:
        json.dump(emails, f, indent=2)

    print(f"✅ Extracted {len(emails)} emails and saved to {output_path}")
    return emails

if __name__ == "__main__":
    extract_emails_from_db()
