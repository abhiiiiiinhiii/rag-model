import os
import csv
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Union, Dict, AsyncGenerator
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import StreamingResponse
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rag_pipeline import WMSChatbot
import yaml
try:
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    TIER_KEYS = config.get('tier_keys', {})
    CLIENT_CONFIG = config.get('clients', {})
except FileNotFoundError:
    print("Error: config.yaml not found. Please ensure it exists.")
    TIER_KEYS = {}
    CLIENT_CONFIG = {}

# Load environment variables from your .env file
load_dotenv()

# --- App Initialization ---
app = FastAPI(title="WMS Multi-Tenant Chatbot API")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/resources", StaticFiles(directory="resources"), name="resources")

print("Initializing embedding model and WMSChatbot instance...")

embedding_api_key = os.getenv("GOOGLE_API_KEY_EMBEDDING")
if not embedding_api_key:
    raise ValueError("GOOGLE_API_KEY_EMBEDDING not found in .env file.")

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=embedding_api_key
)

wms_bot = WMSChatbot(embedding_model=embedding_model)
print("Startup complete. Chatbot is ready.")

@app.on_event("startup")
async def startup_event():
    print("FastAPI application startup ready.")
wms_domain = "https://uatreham.holisollogistics.com" 

app.add_middleware(
    CORSMiddleware,
    allow_origins=[wms_domain],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Logging Setup ---
LOG_FILE = 'chat_history.csv'
LOG_HEADERS = ['Timestamp', 'ClientID', 'Query', 'Answer']
CONFIDENCE_THRESHOLD = 85

def log_conversation(client_id: str, query: str, answer: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, client_id, query, answer]
    file_exists = os.path.isfile(LOG_FILE)
    try:
        with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            if not file_exists:
                writer.writerow(LOG_HEADERS)
            writer.writerow(row)
    except Exception as e:
        logging.error(f"Failed to log conversation: {e}")

# @app.get("/", response_class=HTMLResponse, include_in_schema=False)
# async def read_root():
#     with open("index.html") as f:
#         return HTMLResponse(content=f.read(), status_code=200)
    
# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    session_id: str
    client_id: str

class ChatResponse(BaseModel):
    answer: str

class IngestResponse(BaseModel):
    message: str
    
class ErrorAnalysisRequest(BaseModel):
    endpoint: str
    status_code: int
    error_body: Union[Dict, str]
    client_id: str
    session_id: str

# NEW: Pydantic model for the FAQ ingestion request, now a directory
class IngestFAQRequest(BaseModel):
    faq_directory: str

@app.post("/chat", summary="Chat with bot")
async def chat_with_bot(req: ChatRequest):
    client_id = req.client_id
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required.")

    client_info = CLIENT_CONFIG.get(client_id)
    if not client_info:
        raise HTTPException(status_code=404, detail=f"Configuration for client '{client_id}' not found.")

    tier = client_info.get("tier", "free")
    service = client_info.get("service", "google")
    api_key = TIER_KEYS.get(service, {}).get(tier)
    if not api_key:
        raise HTTPException(status_code=500, detail=f"API key for service '{service}' and tier '{tier}' is not configured.")

    try:
        llm, decomposition_llm = wms_bot._get_llms_for_key(api_key)

        async def stream_generator() -> AsyncGenerator[str, None]:
            log_conversation(req.client_id, req.query, "-> Streaming response started")
            async for chunk in wms_bot.ask_stream(
                query=req.query,
                client_id=req.client_id,
                session_id=req.session_id,
                llm=llm,
                decomposition_llm=decomposition_llm
            ):
                yield chunk
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
        
    except Exception as e:
        logging.error(f"Error for client '{client_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.post("/errors/analyze", response_model=ChatResponse, summary="Proactively analyze a client-side error")
async def analyze_client_error(req: ErrorAnalysisRequest):
    client_id = req.client_id
    client_info = CLIENT_CONFIG.get(client_id)
    if not client_info:
        logging.warning(f"Error analysis request for unknown client '{client_id}'")
        return {"answer": ""}

    tier = client_info.get("tier", "paid")
    service = client_info.get("service", "google")
    api_key = TIER_KEYS.get(service, {}).get(tier)
    if not api_key:
        logging.error(f"Missing API key for error analysis for client {client_id}")
        return {"answer": ""}

    formatted_query = (
        f"A user received an HTTP {req.status_code} error from the API endpoint '{req.endpoint}'. "
        f"The error message was: {req.error_body}. "
        f"What is the cause and how can the user solve this?"
    )

    try:
        llm, _ = wms_bot._get_llms_for_key(api_key)
        
        response_data = wms_bot.ask_error_solution(
            query=formatted_query,
            llm=llm,
        )
        
        answer = response_data.get("answer", "")
        confidence = response_data.get("confidence_score", 0)

        no_info_string = "I don't have enough information"
        
        if confidence >= CONFIDENCE_THRESHOLD and no_info_string not in answer:
            log_conversation(req.client_id, f"PROACTIVE_SUCCESS (C:{confidence})", answer)
            return {"answer": answer}
        else:
            log_conversation(req.client_id, f"PROACTIVE_REJECT (C:{confidence} | No Info)", answer)
            return {"answer": ""}

    except Exception as e:
        logging.error(f"Error during proactive analysis for client '{req.client_id}': {e}", exc_info=True)
        return {"answer": ""}
    
@app.post("/admin/ingest/{source_folder}", response_model=IngestResponse, summary="Ingest docs (Admin Only)")
async def ingest_from_folder(source_folder: str):
    try:
        stats = wms_bot.ingest_documents(source_folder=source_folder)
        return {"message": f"Ingestion from '{source_folder}' complete. Added/Updated: {stats['added_or_updated']}. Deleted: {stats['deleted']}."}
    except Exception as e:
        logging.error(f"Ingestion failed for folder '{source_folder}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Admin endpoint to ingest FAQs
@app.post("/admin/ingest_faqs", response_model=IngestResponse, summary="Ingest FAQs from CSV (Admin Only)")
async def ingest_faqs(req: IngestFAQRequest):
    try:
        wms_bot.ingest_faqs_from_csv(req.faq_directory)
        return {"message": f"FAQ ingestion from '{req.faq_directory}' complete."}
    except Exception as e:
        logging.error(f"FAQ ingestion failed for '{req.faq_directory}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

