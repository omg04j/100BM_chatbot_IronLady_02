"""
Database models and setup for feedback storage
Using SQLAlchemy with SQLite (can easily switch to PostgreSQL for production)
"""
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL (use PostgreSQL in production)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feedback.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()

# Feedback Model
class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    message_id = Column(String, index=True, nullable=False)  # Unique ID for each message
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(String, nullable=False)  # 'positive' or 'negative'
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_comment = Column(Text, nullable=True)  # Optional user comment
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "question": self.question,
            "answer": self.answer,
            "rating": self.rating,
            "timestamp": self.timestamp.isoformat(),
            "user_comment": self.user_comment
        }

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()