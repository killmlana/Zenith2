import json

CLAUDE_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"

def query_claude(user_query, context, claude_client):
    prompt = f"""
You are an AI assistant that reads raw student email metadata and extracts meaningful event-related messages such as reminders, assignments, or campus invitations.

For each relevant email, return a structured JSON object with the following format strictly:

    "title": "String",
    "event-name": "String",
    "event-date": "Date",
    "message-body": "String",
    "email-date": "Date",
    "registration-link": "Hyperlink",
    "registration-fees": "String"

Ignore irrelevant emails like login alerts or codes. Your goal is to format the useful ones for a calendar and event feed.

Do not include any commentary or any words at all before or after the json object in your response.

You can shorten the titles or headings of the events to summarize the key points.

Return a JSON array of such objects only — no commentary, no markdown.

EMAILS:
{json.dumps(context, indent=2)}

### Response:
"""

    try:
        response = claude_client.invoke_model(
            modelId=CLAUDE_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0.3,
                "system": "",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )

        text = json.loads(response['body'].read())['content'][0]['text']
        print("✅ Claude responded successfully.")
        return text

    except Exception as e:
        print(f"❌ Error from Claude: {e}")
        return "[]"
