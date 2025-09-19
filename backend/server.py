from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import aiofiles
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage
import PyPDF2
import io
import base64
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Risk Level Enum
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# Models
class ClauseAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    clause_text: str
    risk_level: RiskLevel
    risk_score: int = Field(..., ge=1, le=10)
    explanation: str
    section: Optional[str] = None

class DocumentAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    filename: str
    document_type: str
    full_document_text: Optional[str] = None
    clauses: List[ClauseAnalysis]
    summary: str
    recommendations: List[str]
    overall_risk_score: float
    created_at: datetime = Field(default_factory=lambda: datetime.now())

class DocumentAnalysisCreate(BaseModel):
    filename: str
    document_type: str

# Initialize LLM Chat
def get_llm_chat():
    return LlmChat(
        api_key=os.environ.get('EMERGENT_LLM_KEY'),
        session_id=f"legal_doc_{uuid.uuid4()}",
        system_message="""You are an expert legal document analyzer. Your job is to:
1. Identify risky clauses in legal documents
2. Assign risk scores from 1-10 (1=low risk, 10=extremely risky)
3. Classify each clause as LOW (1-3), MEDIUM (4-6), or HIGH (7-10) risk
4. Provide clear explanations in plain English for why each clause is risky
5. Summarize the entire document in simple, accessible language
6. Provide actionable recommendations to reduce legal risks

Focus on common risk factors like:
- Auto-renewal clauses
- Indemnity and liability terms
- Termination restrictions
- Hidden fees or penalties
- Exclusive dealing arrangements
- Dispute resolution limitations
- Intellectual property transfers
- Data usage and privacy terms"""
    ).with_model("gemini", "gemini-2.0-flash")

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")

async def analyze_document_with_ai(text: str, filename: str) -> DocumentAnalysis:
    """Analyze document text using AI"""
    chat = get_llm_chat()
    
    # Create analysis prompt
    analysis_prompt = f"""
    Analyze this legal document and provide a detailed risk assessment:

    DOCUMENT: {filename}
    CONTENT: {text[:10000]}...

    Please provide your analysis in the following JSON format:
    {{
        "clauses": [
            {{
                "clause_text": "actual clause text",
                "risk_level": "low|medium|high",
                "risk_score": 1-10,
                "explanation": "why this clause is risky in plain English",
                "section": "section name if identifiable"
            }}
        ],
        "summary": "plain language summary of the entire document",
        "recommendations": ["actionable recommendation 1", "actionable recommendation 2"],
        "document_type": "contract|terms_of_service|privacy_policy|loan_agreement|other"
    }}

    Focus on identifying the most important risky clauses. Limit to maximum 10 clauses.
    """
    
    try:
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        # Parse AI response
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
        
        ai_analysis = json.loads(response_text)
        
        # Convert to our models
        clauses = []
        total_risk = 0
        
        for clause_data in ai_analysis.get("clauses", []):
            clause = ClauseAnalysis(
                clause_text=clause_data["clause_text"],
                risk_level=RiskLevel(clause_data["risk_level"]),
                risk_score=clause_data["risk_score"],
                explanation=clause_data["explanation"],
                section=clause_data.get("section")
            )
            clauses.append(clause)
            total_risk += clause.risk_score
        
        # Calculate overall risk score
        overall_risk = total_risk / len(clauses) if clauses else 0
        
        document_analysis = DocumentAnalysis(
            document_id=str(uuid.uuid4()),
            filename=filename,
            document_type=ai_analysis.get("document_type", "unknown"),
            full_document_text=text,
            clauses=clauses,
            summary=ai_analysis.get("summary", ""),
            recommendations=ai_analysis.get("recommendations", []),
            overall_risk_score=round(overall_risk, 2)
        )
        
        return document_analysis
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing AI response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "AI Legal Document Assistant API"}

@api_router.post("/analyze-document", response_model=DocumentAnalysis)
async def analyze_document(file: UploadFile = File(...)):
    """Analyze uploaded legal document"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Read file content
    content = await file.read()
    
    # Extract text based on file type
    if file.filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(content)
    elif file.filename.lower().endswith('.txt'):
        text = content.decode('utf-8')
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload PDF or TXT files.")
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content found in the document")
    
    # Analyze with AI
    analysis = await analyze_document_with_ai(text, file.filename)
    
    # Store in database
    analysis_dict = analysis.dict()
    analysis_dict['created_at'] = analysis_dict['created_at'].isoformat()
    await db.document_analyses.insert_one(analysis_dict)
    
    return analysis

@api_router.get("/analyses", response_model=List[DocumentAnalysis])
async def get_analyses():
    """Get all document analyses"""
    analyses = await db.document_analyses.find().sort("created_at", -1).to_list(100)
    
    for analysis in analyses:
        if isinstance(analysis.get('created_at'), str):
            analysis['created_at'] = datetime.fromisoformat(analysis['created_at'])
    
    return [DocumentAnalysis(**analysis) for analysis in analyses]

@api_router.get("/analysis/{analysis_id}", response_model=DocumentAnalysis)
async def get_analysis(analysis_id: str):
    """Get specific document analysis"""
    analysis = await db.document_analyses.find_one({"id": analysis_id})
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if isinstance(analysis.get('created_at'), str):
        analysis['created_at'] = datetime.fromisoformat(analysis['created_at'])
    
    return DocumentAnalysis(**analysis)

@api_router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Delete document analysis"""
    result = await db.document_analyses.delete_one({"id": analysis_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"message": "Analysis deleted successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()