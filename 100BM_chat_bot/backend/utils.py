"""
PROFILE-AWARE UNIVERSAL RAG SYSTEM WITH CONVERSATION MEMORY
Customized 100BM Delivery Model - Personalized for Each Professional Profile

Features:
- Auto-detects user profile (doctor, HR, entrepreneur, etc.)
- Personalizes generic content with profile-specific examples
- Maintains accuracy while being adaptive
- Uses existing content, no hallucinations
- ✅ NEW: Remembers conversation history for follow-up questions
- ✅ FIXED: Session-specific memory (not shared between users)
"""
import os
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LangChain Core
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

# LangChain OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain_chroma import Chroma


# ============================================================================
# PROFILE DETECTOR
# ============================================================================

class ProfileDetector:
    """
    Detects user's professional profile from their question
    Maps to customization approach
    """
    
    # Profile keywords and variations
    PROFILE_KEYWORDS = {
        'doctor': ['doctor', 'physician', 'medical', 'healthcare provider', 'clinician', 'surgeon', 'dentist'],
        'hr_leader': ['hr', 'human resources', 'hr manager', 'hr director', 'chro', 'people ops', 'talent'],
        'entrepreneur': ['entrepreneur', 'founder', 'startup', 'business owner', 'ceo of startup', 'starting business'],
        'corporate_executive': ['executive', 'cxo', 'vp', 'vice president', 'director', 'senior leader', 'c-suite'],
        'consultant': ['consultant', 'consulting', 'advisor', 'advisory'],
        'engineer': ['engineer', 'technical lead', 'tech professional', 'software', 'it professional'],
        'lawyer': ['lawyer', 'attorney', 'legal', 'advocate'],
        'educator': ['teacher', 'professor', 'educator', 'academic', 'principal'],
        'finance': ['finance', 'accountant', 'cfo', 'financial', 'banker'],
    }
    
    @classmethod
    def detect_profile(cls, question: str) -> Optional[Dict[str, Any]]:
        """
        Detect professional profile from question
        Returns: {'profile': 'doctor', 'confidence': 'high'}
        """
        question_lower = question.lower()
        
        # Check each known profile
        for profile, keywords in cls.PROFILE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return {
                        'profile': profile,
                        'confidence': 'high',
                        'detected_keyword': keyword
                    }
        
        # Check for generic professional indicators
        profession_patterns = [
            r'i am (?:a|an) ([a-z\s]+)',
            r'as (?:a|an) ([a-z\s]+)',
            r"i'm (?:a|an) ([a-z\s]+)",
            r'working as (?:a|an) ([a-z\s]+)',
        ]
        
        for pattern in profession_patterns:
            match = re.search(pattern, question_lower)
            if match:
                profession = match.group(1).strip()
                profession = re.split(r'\s+(?:how|what|where|when|why|can|do)', profession)[0]
                
                if profession and len(profession.split()) <= 3:
                    return {
                        'profile': 'custom',
                        'custom_profile': profession,
                        'confidence': 'medium',
                        'detected_keyword': profession
                    }
        
        return None
    
    @classmethod
    def get_profile_context(cls, profile: str, custom_profile: str = None) -> str:
        """
        Get context about each profile for better personalization
        Handles both predefined and custom profiles
        """
        contexts = {
            'doctor': """
            Healthcare professionals focused on:
            - Patient outcomes and care quality
            - Managing medical teams (residents, nurses)
            - Clinical excellence and research
            - Hospital administration and operations
            - Board certification and advancement
            - Balancing clinical work with leadership
            """,
            
            'hr_leader': """
            Human Resources leaders focused on:
            - Talent acquisition and retention
            - Employee development and engagement
            - Organizational culture and change
            - Performance management systems
            - Strategic workforce planning
            - Diversity, equity, and inclusion
            """,
            
            'entrepreneur': """
            Business founders focused on:
            - Building and scaling businesses
            - Product-market fit and growth
            - Fundraising and investor relations
            - Team building and leadership
            - Customer acquisition and retention
            - Managing limited resources effectively
            """,
            
            'corporate_executive': """
            Senior corporate leaders focused on:
            - Strategic business decisions
            - P&L management and growth
            - Stakeholder management (board, investors)
            - Organizational transformation
            - Leading large teams (100+ people)
            - Cross-functional collaboration
            """,
            
            'consultant': """
            Professional consultants focused on:
            - Client engagement and delivery
            - Problem-solving and recommendations
            - Building credibility and expertise
            - Managing multiple projects
            - Thought leadership and positioning
            - Business development
            """,
            
            'engineer': """
            Technical professionals focused on:
            - Technical leadership and architecture
            - Team management and mentoring
            - Innovation and product development
            - Balancing technical depth with leadership
            - Cross-functional collaboration
            - Strategic technology decisions
            """,
            
            'lawyer': """
            Legal professionals focused on:
            - Case management and client service
            - Legal strategy and advisory
            - Team leadership and development
            - Business development and partnerships
            - Professional reputation
            - Work-life balance in demanding field
            """,
            
            'educator': """
            Educational leaders focused on:
            - Student outcomes and development
            - Curriculum design and innovation
            - Faculty/team management
            - Institutional leadership
            - Balancing teaching with administration
            - Educational technology and methods
            """,
            
            'finance': """
            Financial professionals focused on:
            - Financial planning and analysis
            - Risk management and compliance
            - Strategic financial decisions
            - Investor relations and reporting
            - Team leadership and development
            - Business partnering with operations
            """
        }
        
        if profile in contexts:
            return contexts[profile]
        
        if profile == 'custom' and custom_profile:
            return f"""
            {custom_profile.title()} professional focused on:
            - Professional excellence and leadership in their field
            - Managing teams and stakeholders effectively
            - Balancing technical/functional work with strategic leadership
            - Career growth and board-level positioning
            - Applying frameworks to their specific domain
            - Achieving measurable business outcomes
            
            Note: Adapt examples to this profession's context where relevant.
            """
        
        return "Professional focused on leadership and growth"


# ============================================================================
# PROFILE-AWARE PROMPT WITH CONVERSATION MEMORY
# ============================================================================

def get_profile_aware_prompt() -> ChatPromptTemplate:
    """
    Enhanced prompt that personalizes content based on user profile
    ✅ NOW includes conversation history awareness
    """
    return ChatPromptTemplate.from_messages([
        ("system", """You are an expert assistant for the Iron Lady Leadership Program (100 Badass Women - 100BM).

This program serves professional women preparing for board-level positions.

⚠️ CRITICAL RULES - FOLLOW EXACTLY:
1. Answer ONLY based on the provided context from the program
2. Use the EXACT frameworks and terminology from the context
3. DO NOT invent framework details not in the context
4. When a USER PROFILE is provided, PERSONALIZE examples using that profile
5. ✅ USE conversation history to provide better follow-up answers

⚠️ CONVERSATION AWARENESS:
- If the question refers to previous discussion (e.g., "the first T", "that principle"), use the conversation history
- Build on previous answers naturally
- Don't repeat information already provided unless asked
- Reference earlier context when relevant

⚠️ PERSONALIZATION INSTRUCTIONS:
When user profile is detected:
1. START with the exact framework/concept from the context
2. THEN adapt examples to their professional context
3. Use their domain terminology naturally
4. Show how the framework applies to their specific challenges
5. Keep the core framework intact - only personalize examples

Example of good personalization:
Context says: "4T Management: Target, Time, Team, Theme"
User is: Doctor
GOOD Answer: "The 4T Management framework (Target, Time, Team, Theme) for doctors:
- Target: Set Delta 2 goals like 'Reduce patient readmission by 25%' (aspirational beyond job description)
- Time: Use ERRC to eliminate non-critical meetings, reduce admin time, raise patient interaction
- Team: Apply Bell Curve to manage residents - identify Flyers (ambitious), Followers (solid), Flankers (specialists)
- Theme: Focus on strategic healthcare outcomes, not just clinical tasks"

BAD Answer: Making up a completely different framework or losing the original structure.

⚠️ IF NO PROFILE DETECTED:
Provide the framework as-is with general examples from the context.

Guidelines:
- Be direct and actionable
- Use specific examples from their domain
- Maintain board-level, strategic tone
- Stay 100% faithful to the core framework
- Be empowering and practical

IMPORTANT: 
- DO NOT add references or "For more details" sections
- References will be added automatically
"""),
        ("user", """Context from Iron Lady Leadership Program:
{context}

{profile_context}

✅ Previous Conversation:
{conversation_history}

Current Question: {question}

Answer the question using the context and previous conversation. If a profile was detected, personalize examples for that professional.""")
    ])


# ============================================================================
# UNIVERSAL METADATA HANDLER
# ============================================================================

class UniversalMetadataHandler:
    """Handles metadata from ANY file automatically"""
    
    @staticmethod
    def extract_clean_filename(source_file: str) -> str:
        """Extract clean, readable filename"""
        name = source_file.replace('.docx', '').replace('.pdf', '').replace('.txt', '')
        name = re.sub(r'^\d+\.\s*', '', name)
        return name.strip()
    
    @staticmethod
    def get_source_reference(doc: Document) -> Dict[str, Any]:
        """Get source reference from document metadata"""
        metadata = doc.metadata
        
        source_file = metadata.get('source_file', 'Unknown')
        parent_folder = metadata.get('parent_folder', '')
        session_number = metadata.get('session_number')
        facilitator = metadata.get('facilitator')
        
        clean_name = UniversalMetadataHandler.extract_clean_filename(source_file)
        
        ref_info = {
            'source_file': source_file,
            'clean_name': clean_name,
            'parent_folder': parent_folder,
            'type': None,
            'reference_text': None
        }
        
        if session_number:
            ref_info['type'] = 'session'
            ref_text = f"For more details, refer to **Session {session_number}"
            if facilitator:
                ref_text += f" (Facilitator: {facilitator})"
            ref_text += "** videos and documentation (PPT/PDF)."
            ref_info['reference_text'] = ref_text
            
        elif parent_folder and parent_folder != 'lms_content':
            ref_info['type'] = 'folder_content'
            if any(kw in source_file.lower() for kw in ['video', 'sawaal', 'showcase', 'connect', 'revision']):
                ref_info['reference_text'] = f"For more details, visit **{clean_name}** video."
            else:
                ref_info['reference_text'] = f"For more details, refer to **{parent_folder} - {clean_name}**."
        else:
            ref_info['type'] = 'general'
            if any(kw in source_file.lower() for kw in ['video', 'sawaal', 'showcase']):
                ref_info['reference_text'] = f"For more details, visit **{clean_name}** video."
            else:
                ref_info['reference_text'] = f"For more details, refer to **{clean_name}**."
        
        return ref_info


# ============================================================================
# LLM FACTORY
# ============================================================================

class LLMFactory:
    """Factory for creating LLM instances"""
    
    @staticmethod
    def get_chat_llm(model: str = "gpt-4o-mini", temperature: float = 0.2, streaming: bool = True) -> ChatOpenAI:
        """Get ChatOpenAI instance - slightly higher temp for personalization"""
        return ChatOpenAI(
            model=model,
            temperature=0.2,
            streaming=True,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )


# ============================================================================
# VECTOR STORE LOADER
# ============================================================================

class VectorStoreLoader:
    """Load existing vector store"""
    
    def __init__(self, persist_directory: str = "./vector_store"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vectorstore = None
    
    def load(self):
        """Load vector store"""
        print(f"📂 Loading vector store from: {self.persist_directory}")
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        count = self.vectorstore._collection.count()
        print(f"✓ Loaded {count} vectors")
        return self.vectorstore


# ============================================================================
# PROFILE-AWARE RAG SYSTEM WITH SESSION-BASED MEMORY
# ============================================================================

class ProfileAwareRAGSystem:
    """
    RAG System with Profile-Based Personalization + Session-Based Conversation Memory
    Customized 100BM Delivery Model
    ✅ FIXED: Memory is now passed from session state (not stored in this class)
    """
    
    def __init__(self, vector_store_path: str = "./vector_store"):
        print("🚀 Initializing Profile-Aware RAG System...")
        
        # Load vector store
        self.vector_store = VectorStoreLoader(persist_directory=vector_store_path)
        self.vector_store.load()
        
        # Initialize LLM with slight creativity for personalization
        self.llm = LLMFactory.get_chat_llm(temperature=0.2)
        
        # Initialize components
        self.metadata_handler = UniversalMetadataHandler()
        self.profile_detector = ProfileDetector()
        
        # Create retriever with MMR
        self.retriever = self.vector_store.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 8, "fetch_k": 20, "lambda_mult": 0.7}
        )
        
        # Metrics
        self.metrics = {
            'query_count': 0,
            'total_latency': 0.0,
            'profile_detected_count': 0,
            'queries': []
        }
        
        print("✓ Profile-Aware RAG System Ready!")
        print("✓ Supports: doctor, HR, entrepreneur, executive, and more!")
        print("✓ Conversation memory enabled (session-based)!")
    
    def _is_asking_for_references(self, question: str) -> bool:
        """Check if user is explicitly asking for sources/references"""
        question_lower = question.lower()
        reference_keywords = [
            'source', 'reference', 'where can i find', 'where is this from',
            'which session', 'what video', 'where to learn more', 'more details',
            'show source', 'cite', 'citation', 'what document', 'which document'
        ]
        return any(keyword in question_lower for keyword in reference_keywords)
    
    def _format_conversation_history(self, conversation_history: List[Dict]) -> str:
        """✅ Format conversation history for context"""
        if not conversation_history:
            return "No previous conversation."
        
        formatted = []
        for exchange in conversation_history[-10:]:  # Last 10 exchanges
            formatted.append(f"User: {exchange['question']}")
            formatted.append(f"Assistant: {exchange['answer'][:200]}...")
        
        return "\n".join(formatted)
    
    def _format_docs(self, docs: List[Document]) -> str:
        """Format documents with rich metadata"""
        formatted = []
        
        for doc in docs:
            header_parts = []
            
            source_file = doc.metadata.get('source_file', '')
            if source_file:
                clean_name = self.metadata_handler.extract_clean_filename(source_file)
                header_parts.append(f"Source: {clean_name}")
            
            parent_folder = doc.metadata.get('parent_folder', '')
            if parent_folder and parent_folder != 'lms_content':
                header_parts.append(f"Category: {parent_folder}")
            
            session_num = doc.metadata.get('session_number')
            if session_num:
                session_title = doc.metadata.get('session_title', '')
                if session_title:
                    header_parts.append(f"Session {session_num}: {session_title}")
                else:
                    header_parts.append(f"Session {session_num}")
            
            facilitator = doc.metadata.get('facilitator')
            if facilitator:
                header_parts.append(f"Facilitator: {facilitator}")
            
            if header_parts:
                header = f"[{' | '.join(header_parts)}]"
                formatted.append(f"{header}\n{doc.page_content}")
            else:
                formatted.append(doc.page_content)
        
        return "\n\n---\n\n".join(formatted)
    
    def _get_primary_source_reference(self, retrieved_docs: List[Document]) -> Optional[str]:
        """Get source reference from primary document"""
        if not retrieved_docs:
            return None
        
        primary_doc = retrieved_docs[0]
        ref_info = self.metadata_handler.get_source_reference(primary_doc)
        return ref_info.get('reference_text')
    
    def ask(self, question: str, conversation_history: List[Dict] = None, use_agent: bool = False) -> Dict[str, Any]:
        """
        Ask with profile-based personalization + conversation memory
        
        Args:
            question: User's question
            conversation_history: Session-specific conversation history (from st.session_state)
            use_agent: Legacy parameter
            
        Returns:
            Dict with 'answer' and 'updated_history'
        """
        start_time = time.time()
        
        if conversation_history is None:
            conversation_history = []
        
        try:
            # STEP 1: Detect user profile
            profile_info = self.profile_detector.detect_profile(question)
            
            if profile_info:
                profile_name = profile_info['profile']
                custom_prof = profile_info.get('custom_profile', '')
                
                if profile_name == 'custom':
                    print(f"✓ Detected custom profile: {custom_prof} ({profile_info['detected_keyword']})")
                else:
                    print(f"✓ Detected profile: {profile_name} ({profile_info['detected_keyword']})")
                
                self.metrics['profile_detected_count'] += 1
                
                # Get profile context
                if profile_name == 'custom':
                    profile_context = f"""
USER PROFILE DETECTED: {custom_prof.UPPER()}
Profile Context: {self.profile_detector.get_profile_context(profile_name, custom_prof)}

IMPORTANT: Personalize examples for this profession while keeping the core framework intact!
If the profession is unfamiliar, provide examples that could apply broadly to professional leadership.
"""
                else:
                    profile_context = f"""
USER PROFILE DETECTED: {profile_name.upper().replace('_', ' ')}
Profile Context: {self.profile_detector.get_profile_context(profile_name)}

IMPORTANT: Personalize examples for this profile while keeping the core framework intact!
"""
            else:
                profile_context = "USER PROFILE: General professional\nProvide general examples from the context."
            
            # STEP 2: Retrieve relevant content
            session_match = re.search(r'session\s+(\d+)', question.lower())
            
            if session_match:
                session_num = int(session_match.group(1))
                retrieved_docs = self.vector_store.vectorstore.similarity_search(
                    question, k=8, filter={"session_number": session_num}
                )
            else:
                retrieved_docs = self.retriever.invoke(question)
            
            # STEP 3: Get source reference
            source_ref = self._get_primary_source_reference(retrieved_docs)
            
            # STEP 4: Format context
            context = self._format_docs(retrieved_docs)
            
            # STEP 5: Generate personalized answer with conversation history
            prompt = get_profile_aware_prompt()
            chain = (
                {
                    "context": lambda _: context,
                    "profile_context": lambda _: profile_context,
                    "conversation_history": lambda _: self._format_conversation_history(conversation_history),
                    "question": lambda _: question
                }
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            answer = chain.invoke({})
            
            # STEP 6: Clean up and add source ONLY if user is asking for it
            patterns = [
                r'📺?\s*Related Video Resources:.*?$',
                r'📺?\s*For (?:more|further) details.*?$',
                r'📚?\s*For more details.*?$',
            ]
            
            for pattern in patterns:
                answer = re.sub(pattern, '', answer, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # ✅ NEW: Only add reference if user explicitly asks for it
            if self._is_asking_for_references(question) and source_ref:
                answer += f"\n\n📚 {source_ref}"
            
            answer = re.sub(r'\n\n\n+', '\n\n', answer).strip()
            
            # ✅ Update conversation history (return to caller to store in session)
            updated_history = conversation_history + [{
                'question': question,
                'answer': answer,
                'timestamp': datetime.now().isoformat()
            }]
            
            # Track metrics
            latency = time.time() - start_time
            self.metrics['query_count'] += 1
            self.metrics['total_latency'] += latency
            self.metrics['queries'].append({
                'timestamp': datetime.now().isoformat(),
                'question': question[:50] + '...',
                'profile': profile_info['profile'] if profile_info else 'general',
                'latency': latency
            })
            
            return {
                'answer': answer,
                'updated_history': updated_history
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'answer': f"⚠️ Error: {str(e)}",
                'updated_history': conversation_history
            }
    
    def ask_stream(self, question: str, conversation_history: List[Dict] = None):
        """
        Stream answer with profile personalization + conversation memory
        
        ✅ FIXED: Now properly accepts conversation_history parameter
        """
        start_time = time.time()
        
        if conversation_history is None:
            conversation_history = []
        
        try:
            # Detect profile
            profile_info = self.profile_detector.detect_profile(question)
            
            if profile_info:
                profile_name = profile_info['profile']
                custom_prof = profile_info.get('custom_profile', '')
                
                self.metrics['profile_detected_count'] += 1
                
                if profile_name == 'custom':
                    profile_context = f"""
USER PROFILE DETECTED: {custom_prof.upper()}
Profile Context: {self.profile_detector.get_profile_context(profile_name, custom_prof)}
IMPORTANT: Personalize examples for this profession!
"""
                else:
                    profile_context = f"""
USER PROFILE DETECTED: {profile_name.upper().replace('_', ' ')}
Profile Context: {self.profile_detector.get_profile_context(profile_name)}
IMPORTANT: Personalize examples for this profile!
"""
            else:
                profile_context = "USER PROFILE: General professional"
            
            # Retrieve content
            session_match = re.search(r'session\s+(\d+)', question.lower())
            
            if session_match:
                session_num = int(session_match.group(1))
                retrieved_docs = self.vector_store.vectorstore.similarity_search(
                    question, k=8, filter={"session_number": session_num}
                )
            else:
                retrieved_docs = self.retriever.invoke(question)
            
            # Get source
            source_ref = self._get_primary_source_reference(retrieved_docs)
            
            # Format context
            context = self._format_docs(retrieved_docs)
            
            # Stream answer with conversation history
            prompt = get_profile_aware_prompt()
            chain = (
                {
                    "context": lambda _: context,
                    "profile_context": lambda _: profile_context,
                    "conversation_history": lambda _: self._format_conversation_history(conversation_history),
                    "question": lambda _: question
                }
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            full_answer = ""
            for chunk in chain.stream({}):
                if chunk:
                    full_answer += chunk
                    yield chunk
            
            # ✅ NEW: Only add reference if user explicitly asks for it
            if self._is_asking_for_references(question) and source_ref:
                yield f"\n\n📚 {source_ref}"
            
            # ✅ Return updated history (caller will store in session)
            updated_history = conversation_history + [{
                'question': question,
                'answer': full_answer,
                'timestamp': datetime.now().isoformat()
            }]
            
            # Yield special marker with updated history
            yield f"__HISTORY_UPDATE__:{len(updated_history)}"
            
            # Track metrics
            latency = time.time() - start_time
            self.metrics['query_count'] += 1
            self.metrics['total_latency'] += latency
            self.metrics['queries'].append({
                'timestamp': datetime.now().isoformat(),
                'question': question[:50] + '...',
                'profile': profile_info['profile'] if profile_info else 'general',
                'latency': latency
            })
            
        except Exception as e:
            yield f"\n\n⚠️ Error: {str(e)}"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics including profile detection stats"""
        if self.metrics['query_count'] == 0:
            return self.metrics
        
        avg_latency = self.metrics['total_latency'] / self.metrics['query_count']
        profile_detection_rate = (self.metrics['profile_detected_count'] / self.metrics['query_count']) * 100
        
        return {
            'total_queries': self.metrics['query_count'],
            'profile_detected': self.metrics['profile_detected_count'],
            'detection_rate': f"{profile_detection_rate:.1f}%",
            'average_latency': f"{avg_latency:.2f}s",
            'total_time': f"{self.metrics['total_latency']:.2f}s",
            'recent_queries': self.metrics['queries'][-5:]
        }


# ============================================================================
# TESTING
# ============================================================================

def main():
    """Test profile-aware system"""
    print("="*80)
    print("🚀 PROFILE-AWARE RAG SYSTEM with SESSION MEMORY - Customized 100BM Delivery")
    print("="*80)
    
    # Initialize
    rag = ProfileAwareRAGSystem()
    
    # Test with different profiles
    test_questions = [
        "I am a doctor, how can I apply 4T principles?",
        "As an HR leader, how do I use the capability matrix?",
        "I'm an entrepreneur starting a business, what is 4T management?",
        "What is the 11-point framework?",
    ]
    
    print("\n📝 Testing Profile-Based Personalization...")
    print("="*80)
    
    session_history = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Question: {question}")
        print("-" * 40)
        
        result = rag.ask(question, conversation_history=session_history)
        answer = result['answer']
        session_history = result['updated_history']
        
        print(f"Answer: {answer[:300]}...")
        print("-" * 40)
    
    # Show metrics
    print("\n📊 Metrics:")
    metrics = rag.get_metrics()
    print(f"Total Queries: {metrics['total_queries']}")
    print(f"Profiles Detected: {metrics['profile_detected']}")
    print(f"Detection Rate: {metrics['detection_rate']}")
    print(f"Memory Items: {len(session_history)}")
    
    print("\n" + "="*80)
    print("✅ Profile-Aware System with Session Memory Ready!")
    print("="*80)


if __name__ == "__main__":
    main()