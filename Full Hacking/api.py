from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from prompt import query_claude
from extraction import extract_emails_from_db
from claude_auth import claude_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to ["http://localhost"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/extract-events")
async def extract_events():
    try:
        # Option A: Load from file
        with open('emails.json', 'r') as f:
            emails = json.load(f)

        # Option B: Or extract fresh from DB
        # emails = extract_emails_from_db()

        result = query_claude("extract events", emails, claude_client)
        return {"status": "success", "events": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
