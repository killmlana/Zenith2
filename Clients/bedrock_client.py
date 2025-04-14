import json
import boto3

CLAUDE_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
claude_client = boto3.client('bedrock-runtime', region_name='us-west-2')


def query_claude(user_query, context, claude_client):
    prompt = f"""
You are an AI teacher helping students.
Please answer the following question using the provided context from academic books, add in information.
If the answer cannot be found in the context, please state that clearly.

### Context:
{context}

### User Question:
{user_query}

### Response:
"""
    
    response = claude_client.invoke_model(
        modelId=CLAUDE_MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "temperature": 0,
            "system": "You are an AI research assistant that helps users retrieve information from academic papers. Respond with accurate information and always cite your sources.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )
    
    return json.loads(response['body'].read())['content'][0]['text']