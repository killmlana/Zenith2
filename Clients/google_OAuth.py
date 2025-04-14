import os
from typing import Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
import boto3
import requests
from pathlib import Path
import json
from opensearch_client import OpenSearchClient
import uvicorn
from starlette.middleware.sessions import SessionMiddleware
import bedrock_client

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.add_middleware(
    SessionMiddleware,
    secret_key="abladabbka",  
    session_cookie="session_cookie"
)

CLIENT_CONFIG = {
    "web": {
        "client_id": "841658005536-e7u5dmgb0b4dgvhd14edmsvn77q5rsib.apps.googleusercontent.com",
        "project_id": "zenith-456803",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": "",
        "redirect_uris": ["http://localhost:8000/auth/callback"]
    }
}

# Google OAuth Configuration
CLIENT_SECRET_FILE = 'client_secret.json'
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly"
]
REDIRECT_URI = 'http://localhost:8000/auth/callback'
TOKEN_FILE = 'token.json'

AWS_REGION = 'us-west-2'
OPENSEARCH_ENDPOINT = "8geb4aspg24cbllfp4ob.us-west-2.aoss.amazonaws.com"
BEDROCK_CLIENT = boto3.client('bedrock-runtime', region_name=AWS_REGION)
OPENSEARCH_INDEX = "modules"
OPENSEARCH_EMBEDDING_DIMENSION = 1536 

flow = Flow.from_client_secrets_file(
    CLIENT_SECRET_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        return Credentials.from_authorized_user_file(TOKEN_FILE)
    return None

def save_credentials(creds):
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

@app.get("/auth")
async def auth_init():
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"auth_url": auth_url}

@app.get("/login")
async def login(request: Request):
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=request.url_for("auth_callback")
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    request.session["oauth_state"] = state 
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str, state: str):

    stored_state = request.session.get("oauth_state")
    
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    

    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=request.url_for("auth_callback"),
        state=state  
    )
    
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(400, f"Token fetch failed: {str(e)}")
    

    del request.session["oauth_state"]
    

    save_credentials(flow.credentials)
    return {"status": "Success"}

def get_google_headers():
    creds = get_credentials()
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
            save_credentials(creds)
        else:
            raise HTTPException(401, "Requires authentication")
    return {'Authorization': f'Bearer {creds.token}'}


@app.get("/api/classes")
def get_classes():
    response = requests.get(
        'https://classroom.googleapis.com/v1/courses',
        headers=get_google_headers()
    )
    return response.json()

@app.get("/api/{class_id}/assignments")
def get_assignments(class_id: str):
    response = requests.get(
        f'https://classroom.googleapis.com/v1/courses/{class_id}/courseWork',
        headers=get_google_headers()
    )
    return response.json()

@app.get("/api/{class_id}/modules")
def get_modules(class_id: str):
    response = requests.get(
        f'https://classroom.googleapis.com/v1/courses/{class_id}/courseWorkMaterials',
        headers=get_google_headers()
    )
    materials = response.json().get('courseWorkMaterial', [])
    
    for material in materials:
        process_material(class_id, material)
    
    return materials

def process_material(class_id: str, material: Dict):
    base_path = Path(f"data/{class_id}/{material['id']}")
    base_path.mkdir(parents=True, exist_ok=True)
    
    for attachment in material.get('materials', []):
        if 'driveFile' in attachment:
            file_meta = attachment['driveFile']['driveFile']
            download_drive_file(file_meta['id'], base_path / file_meta['title'])

def download_drive_file(file_id: str, path: Path):
    response = requests.get(
        f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media',
        headers=get_google_headers(),
        stream=True
    )
    with open(path, 'wb') as f:
        for chunk in response.iter_content(1024):
            f.write(chunk)

def generate_embeddings(text: str) -> List[float]:
    response = BEDROCK_CLIENT.invoke_model(
        body=json.dumps({"inputText": text}),
        modelId='amazon.titan-embed-text-v1',
        accept='application/json',
        contentType='application/json'
    )
    return json.loads(response['body'].read())['embedding']


def process_files_for_ingestion():
    for root, _, files in os.walk('data'):
        for file in files:
            if file.endswith('.txt'):
                path = Path(root) / file
                with open(path) as f:
                    text = f.read()
                metadata = {
                    'file_name': file
                }
                OpenSearchClient.index_document(str(path), text, metadata)

@app.post("/api/chat")
def academic_chat(query: str):
    """query_embedding = generate_embeddings(query)
    body = {
        'size': 5,
        'query': {
            'knn': {
                'embedding': {
                    'vector': query_embedding,
                    'k': 5
                }
            }
        }
    }"""
    """results = OpenSearchClient.search('modules', body)"""
    """context = ' '.join([hit['_source']['text'] for hit in results['hits']['hits']])"""

    context = "topics related to anything, sample context so full libery to makeup stuff"
    
    response = bedrock_client.query_claude(query, context, boto3.client('bedrock-runtime', region_name='us-west-2'))
    
    return {"content": response}


if __name__ == "__main__":
    process_files_for_ingestion()
    uvicorn.run(app, host="localhost", port=8090)