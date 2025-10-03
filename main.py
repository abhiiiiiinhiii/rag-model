import os
import csv
import logging
import pandas as pd
import redis
import yaml
from datetime import datetime
from typing import Union, Dict, AsyncGenerator, List, Optional
from io import StringIO
from fastapi import FastAPI, HTTPException, Depends, status, Body, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rag_pipeline import WMSChatbot
from user_db import users_db, pwd_context
from langchain_core.messages import BaseMessage
# Load environment variables from your .env file
load_dotenv()

# --- Security and Authentication Setup ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_dev_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Configuration Loading ---
# Load client configurations from YAML
try:
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    CLIENT_CONFIG = config.get('clients', {})
except FileNotFoundError:
    print("Error: config.yaml not found. Please ensure it exists.")
    CLIENT_CONFIG = {}

# Securely load tier keys from environment variables
free_key = os.getenv("GOOGLE_API_KEY_FREE")
paid_key = os.getenv("GOOGLE_API_KEY_PAID")

if not free_key or not paid_key:
    print("Warning: GOOGLE_API_KEY_FREE or GOOGLE_API_KEY_PAID not found in environment variables.")
    TIER_KEYS = {}
else:
    TIER_KEYS = {
        "google": {
            "free": free_key,
            "paid": paid_key
        }
    }

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Logging Setup ---
LOG_FILE = 'chat_history.csv'
LOG_HEADERS = ['Timestamp', 'ClientID', 'Query', 'Answer']
CONFIDENCE_THRESHOLD = 85

ACTIVITY_LOG_FILE = 'activity_log.csv'
ACTIVITY_LOG_HEADERS = ['Timestamp', 'User', 'Action', 'Description']

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

def log_admin_activity(user: 'User', action: str, description: str):
    """Writes an entry to the admin activity log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, user.full_name, action, description]
    file_exists = os.path.isfile(ACTIVITY_LOG_FILE)
    try:
        with open(ACTIVITY_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(ACTIVITY_LOG_HEADERS)
            writer.writerow(row)
    except Exception as e:
        logging.error(f"Failed to log admin activity: {e}")

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    session_id: str
    client_id: str
    user_id: str

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

class IngestFAQRequest(BaseModel):
    faq_directory: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    full_name: str
    role: str

class FAQ(BaseModel):
    id: str
    question: str
    answer: str

class FAQCreate(BaseModel):
    question: str
    answer: str

class KBDocument(BaseModel):
    id: str
    filename: str
    client: str

class KBDocumentContent(BaseModel):
    id: str
    content: str
    metadata: dict

class KBDocumentUpdate(BaseModel):
    new_content: str

class Message(BaseModel):
    sender: str
    text: str
    type: str = "text"

class ConversationHistory(BaseModel):
    messages: List[Message]
class HistoryItem(BaseModel):
    session_id: str
    title: str
    timestamp: datetime

class HistoryListResponse(BaseModel):
    chats: List[HistoryItem]
    has_more: bool

# --- Utility Functions for Auth ---
def get_user(db, username: str):
    if username in db:
        return db[username]

def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username)
    if user is None:
        raise credentials_exception
    return User(**user)

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

# --- Core API Endpoints ---
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
            full_answer_parts = []
            try:
                async for chunk in wms_bot.ask_stream(
                    query=req.query,
                    client_id=req.client_id,
                    session_id=req.session_id,
                    user_id=req.user_id,
                    llm=llm,
                    decomposition_llm=decomposition_llm
                ):
                    full_answer_parts.append(chunk)
                    yield chunk
            finally:
                final_answer = "".join(full_answer_parts)
                if final_answer:
                    log_conversation(req.client_id, req.query, final_answer)
        
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
        response_data = wms_bot.ask_error_solution(query=formatted_query, llm=llm)
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/ingest_faqs", response_model=IngestResponse, summary="Ingest FAQs from CSV (Admin Only)")
async def ingest_faqs(req: IngestFAQRequest):
    try:
        wms_bot.ingest_faqs_from_csv(req.faq_directory)
        return {"message": f"FAQ ingestion from '{req.faq_directory}' complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API ENDPOINTS FOR CONTROL PANEL ---

# --- Auth Endpoints ---
@app.post("/token", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(users_db, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User, tags=["Auth"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# --- Frontend Serving Endpoint ---
@app.get("/admin", response_class=HTMLResponse, tags=["Frontend"])
def get_admin_panel():
    try:
        with open("control.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Control panel HTML file not found.")
    
@app.get("/history/user/{user_id}", response_model=HistoryListResponse, tags=["Chat"])
def get_user_history(user_id: str, page: int = 1, size: int = 5):
    """Retrieves a paginated list of chat sessions for a given user."""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        r = redis.from_url(redis_url)

        user_history_key = f"user_sessions:{user_id}"
        start = (page - 1) * size
        end = start + size - 1

        # Get a "page" of session IDs from the user's list
        session_ids = [sid.decode('utf-8') for sid in r.lrange(user_history_key, start, end)]

        # Check if there are more pages
        total_sessions = r.llen(user_history_key)
        has_more = total_sessions > (end + 1)

        chats = []
        for sid in session_ids:
            history = wms_bot.get_session_history(sid)
            if history.messages:
                # Use the first user message as the title
                first_human_message = next((msg for msg in history.messages if msg.type == 'human'), None)
                title = first_human_message.content if first_human_message else "Chat"
                # Get timestamp from the first message
                timestamp = history.messages[0].additional_kwargs.get('timestamp', datetime.now())
                chats.append(HistoryItem(session_id=sid, title=title, timestamp=timestamp))

        return HistoryListResponse(chats=chats, has_more=has_more)

    except Exception as e:
        logging.error(f"Error retrieving history list for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve history list.")
    
@app.get("/history/{session_id}", response_model=ConversationHistory, tags=["Chat"])
def get_chat_history(session_id: str):
    """Retrieves the full message history for a given session_id from Redis."""
    try:
        # Use the existing function from rag_pipeline to get history object
        history = wms_bot.get_session_history(session_id)

        # Convert LangChain message objects to our simple Message model
        formatted_messages = []
        for msg in history.messages:
            sender = "unknown"
            if msg.type == 'human':
                sender = "user"
            elif msg.type == 'ai':
                sender = "bot"

            formatted_messages.append(Message(sender=sender, text=msg.content))

        return ConversationHistory(messages=formatted_messages)
    except Exception as e:
        logging.error(f"Error retrieving history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat history.")
    
# --- Admin CRUD Endpoints (with Activity Logging) ---
@app.get("/admin/kb_documents", response_model=List[KBDocument], tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def get_all_kb_documents():
    return wms_bot.get_all_kb_documents()

@app.get("/admin/kb_documents/{doc_source:path}", response_model=KBDocumentContent, tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def get_kb_document(doc_source: str):
    doc = wms_bot.get_kb_document_content(doc_source)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@app.put("/admin/kb_documents/{doc_source:path}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def update_kb_document(doc_source: str, payload: KBDocumentUpdate, current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["Administrator", "Editor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        wms_bot.update_kb_document(doc_source, payload.new_content)
        log_admin_activity(current_user, "Updated Document", f"Edited the content of '{doc_source}'")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/admin/kb_documents/{doc_source:path}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_kb_document(doc_source: str, current_user: User = Depends(get_current_active_user)):
    if current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized")
    wms_bot.delete_kb_document(doc_source)
    log_admin_activity(current_user, "Deleted Document", f"Removed the document '{doc_source}'")

@app.get("/admin/faqs", response_model=List[FAQ], tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def get_all_faqs():
    return wms_bot.get_all_faqs()

@app.post("/admin/faqs", response_model=FAQ, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def add_faq(faq: FAQCreate, current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["Administrator", "Editor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    new_faq = wms_bot.add_single_faq(faq.question, faq.answer)
    log_admin_activity(current_user, "Added FAQ", f"Created new FAQ with question: '{faq.question[:50]}...'")
    return new_faq

@app.put("/admin/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def update_faq(faq_id: str, faq: FAQCreate, current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["Administrator", "Editor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    wms_bot.update_faq(faq_id, faq.question, faq.answer)
    log_admin_activity(current_user, "Updated FAQ", f"Edited FAQ ID: {faq_id}")

@app.delete("/admin/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_faq(faq_id: str, current_user: User = Depends(get_current_active_user)):
    if current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized")
    wms_bot.delete_faq(faq_id)
    log_admin_activity(current_user, "Deleted FAQ", f"Removed FAQ ID: {faq_id}")

@app.post("/admin/faqs/upload_csv", tags=["Admin"])
async def upload_faqs_csv(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["Administrator", "Editor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    try:
        contents = await file.read()
        buffer = StringIO(contents.decode('utf-8-sig'))
        csv_reader = csv.DictReader(buffer)
        if 'question' not in csv_reader.fieldnames or 'answer' not in csv_reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV must have 'question' and 'answer' columns.")
        
        imported_count = 0
        skipped_count = 0
        for row in csv_reader:
            question, answer = row.get('question'), row.get('answer')
            if question and answer:
                if not wms_bot.faq_question_exists(question):
                    wms_bot.add_single_faq(question, answer)
                    imported_count += 1
                else:
                    skipped_count += 1
        
        log_admin_activity(current_user, "Imported FAQs", f"Imported {imported_count} new, skipped {skipped_count} duplicate FAQs from '{file.filename}'")
        return {"message": f"Import complete. Added: {imported_count}. Skipped duplicates: {skipped_count}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# --- Analytics and Log Endpoints ---
@app.get("/admin/analytics", tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def get_analytics():
    try:
        kb_docs_count = len(wms_bot.get_all_kb_documents())
        faqs_count = len(wms_bot.get_all_faqs())
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            return {"totalInteractions": 0, "unanswered": 0, "kbDocs": kb_docs_count, "faqs": faqs_count, "usage": {"labels": [], "data": []}, "unansweredList": []}
        
        df = pd.read_csv(LOG_FILE, on_bad_lines='skip')
        if df.empty:
            return {"totalInteractions": 0, "unanswered": 0, "kbDocs": kb_docs_count, "faqs": faqs_count, "usage": {"labels": [], "data": []}, "unansweredList": []}
            
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df_filtered = df[~df['Query'].str.startswith('PROACTIVE_', na=False)]
        total_interactions = len(df_filtered)
        unanswered_string = "I don't have that information right now"
        unanswered_df = df_filtered[df_filtered['Answer'].str.contains(unanswered_string, na=False)]
        unanswered_count = len(unanswered_df)
        
        # --- MODIFICATION: Get last 10 unanswered questions instead of top 5 frequent ---
        unanswered_list = unanswered_df.sort_values(by='Timestamp', ascending=False).head(10)['Query'].tolist()

        df_filtered['Date'] = df_filtered['Timestamp'].dt.date
        today = pd.to_datetime('today').date()
        last_7_days = pd.date_range(start=today - pd.Timedelta(days=6), end=today)
        usage_counts = df_filtered['Date'].value_counts().reindex(last_7_days.date, fill_value=0).sort_index()
        usage_data = {"labels": [d.strftime('%a') for d in usage_counts.index], "data": usage_counts.values.tolist()}
        
        return {"totalInteractions": total_interactions, "unanswered": unanswered_count, "kbDocs": kb_docs_count, "faqs": faqs_count, "usage": usage_data, "unansweredList": unanswered_list}
    except Exception as e:
        logging.error(f"Error processing analytics: {e}")
        return {"totalInteractions": "Error", "unanswered": "Error", "kbDocs": "Error", "faqs": "Error", "usage": {"labels": [], "data": []}, "unansweredList": ["Error reading log file"]}

# --- NEW: Endpoint for exporting unanswered questions ---
@app.get("/admin/export_unanswered", tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def export_unanswered_questions(start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None)):
    if not os.path.exists(LOG_FILE):
        raise HTTPException(status_code=404, detail="Log file not found.")

    try:
        df = pd.read_csv(LOG_FILE, on_bad_lines='skip')
        if df.empty:
            return StreamingResponse(StringIO(""), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=unanswered_questions.csv"})
        
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        unanswered_string = "I don't have that information right now"
        unanswered_df = df[df['Answer'].str.contains(unanswered_string, na=False)].copy()

        if start_date:
            unanswered_df = unanswered_df[unanswered_df['Timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            unanswered_df = unanswered_df[unanswered_df['Timestamp'] <= pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)]
        
        output = StringIO()
        unanswered_df[['Timestamp', 'ClientID', 'Query']].to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=unanswered_questions_{start_date}_to_{end_date}.csv"})

    except Exception as e:
        logging.error(f"Error exporting unanswered questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data.")


@app.get("/admin/activity_log", tags=["Admin"], dependencies=[Depends(get_current_active_user)])
def get_activity_log():
    if not os.path.exists(ACTIVITY_LOG_FILE):
        return []
    try:
        with open(ACTIVITY_LOG_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logs = list(reader)
            # Reverse to show most recent first and limit to the last 50 entries
            return logs[::-1][:50]
    except Exception as e:
        logging.error(f"Could not read activity log: {e}")
        return [{"User": "System", "Action": "Error", "Description": f"Could not read activity log: {e}"}]

