"""
Simple FastAPI Backend - Direct conversion from Streamlit
Uses your existing utils.py without modifications
NOW WITH FEEDBACK SYSTEM
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Import your existing RAG system
from utils import ProfileAwareRAGSystem

# Import database
from database import init_db, get_db, Feedback

# Simple request/response models
class ChatRequest(BaseModel):
    question: str
    session_id: str
    conversation_history: List[Dict] = []

class ChatResponse(BaseModel):
    answer: str
    updated_history: List[Dict]

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    question: str
    answer: str
    rating: str  # 'positive' or 'negative'
    user_comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    success: bool
    message: str
    feedback_id: int

# Initialize FastAPI
app = FastAPI(title="100BM AI Assistant API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:3001",
        "https://your-frontend-app.onrender.com",  # Production (update after deploying frontend)
        os.getenv("FRONTEND_URL", "http://localhost:3000")  # From environment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your RAG system (same as Streamlit)
rag_system = None

@app.on_event("startup")
async def startup():
    global rag_system
    print("🚀 Initializing RAG System...")
    rag_system = ProfileAwareRAGSystem(vector_store_path="./vector_store")
    print("✅ RAG System Ready!")
    
    # Initialize database
    print("🗄️ Initializing Database...")
    init_db()
    print("✅ Database Ready!")

@app.get("/")
async def root():
    return {"message": "100BM AI Assistant API", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "rag_loaded": rag_system is not None}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    try:
        # Call your existing ask method
        result = rag_system.ask(
            question=request.question,
            conversation_history=request.conversation_history
        )
        
        return ChatResponse(
            answer=result['answer'],
            updated_history=result['updated_history']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    from sse_starlette.sse import EventSourceResponse
    
    async def event_generator():
        try:
            full_answer = ""
            
            # Stream from your existing ask_stream method
            for chunk in rag_system.ask_stream(
                question=request.question,
                conversation_history=request.conversation_history
            ):
                # Handle special markers
                if chunk.startswith("__HISTORY_UPDATE__:"):
                    continue
                
                full_answer += chunk
                
                # Send as Server-Sent Events
                yield {
                    "event": "message",
                    "data": json.dumps({"chunk": chunk})
                }
                await asyncio.sleep(0.01)
            
            # Send completion
            yield {
                "event": "done",
                "data": json.dumps({"done": True, "full_answer": full_answer})
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())

# ===== FEEDBACK ENDPOINTS =====

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit user feedback for a message"""
    try:
        # Validate rating
        if feedback.rating not in ['positive', 'negative']:
            raise HTTPException(
                status_code=400, 
                detail="Rating must be 'positive' or 'negative'"
            )
        
        # Create feedback entry
        db_feedback = Feedback(
            session_id=feedback.session_id,
            message_id=feedback.message_id,
            question=feedback.question,
            answer=feedback.answer,
            rating=feedback.rating,
            user_comment=feedback.user_comment
        )
        
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully",
            feedback_id=db_feedback.id
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """Get feedback statistics"""
    try:
        total_feedback = db.query(Feedback).count()
        positive_count = db.query(Feedback).filter(Feedback.rating == 'positive').count()
        negative_count = db.query(Feedback).filter(Feedback.rating == 'negative').count()
        
        return {
            "total_feedback": total_feedback,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_percentage": round((positive_count / total_feedback * 100) if total_feedback > 0 else 0, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/recent")
async def get_recent_feedback(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent feedback entries"""
    try:
        feedback_list = db.query(Feedback)\
            .order_by(Feedback.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return {
            "feedback": [f.to_dict() for f in feedback_list]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/session/{session_id}")
async def get_session_feedback(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get all feedback for a specific session"""
    try:
        feedback_list = db.query(Feedback)\
            .filter(Feedback.session_id == session_id)\
            .order_by(Feedback.timestamp.desc())\
            .all()
        
        return {
            "session_id": session_id,
            "feedback_count": len(feedback_list),
            "feedback": [f.to_dict() for f in feedback_list]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🚀 Starting 100BM AI Assistant Backend")
    print("="*60)
    print("Backend: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)