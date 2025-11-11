import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

// Import your logo
import ironLadyLogo from './iron_lady_logo.png';

// API Configuration
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Suggested questions
const SUGGESTED_QUESTIONS = [
  { emoji: "💊", text: "I am a doctor, how can I apply 4T principles?" },
  { emoji: "👥", text: "As an HR leader, what is the capability matrix?" },
  { emoji: "📋", text: "How to create a board member persona?" },
  { emoji: "💻", text: "As a tech executive, what is the success story framework?" },
  { emoji: "🗓️", text: "what is my 2025 batch schedule?" }
];

function App() {
  // Session ID
  const [sessionId] = useState(() => {
    let id = localStorage.getItem('chatSessionId');
    if (!id) {
      id = 'session-' + Date.now();
      localStorage.setItem('chatSessionId', id);
    }
    return id;
  });

  // Chat state
  const [messages, setMessages] = useState([]);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  
  // Feedback state - track which messages have been rated
  const [feedbackGiven, setFeedbackGiven] = useState({});

  // Submit feedback to backend
  const submitFeedback = async (messageId, question, answer, rating) => {
    try {
      const response = await fetch(`${API_URL}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          question: question,
          answer: answer,
          rating: rating
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      const data = await response.json();
      console.log('Feedback submitted:', data);
      
      // Mark this message as rated
      setFeedbackGiven(prev => ({
        ...prev,
        [messageId]: rating
      }));

    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  // Handle feedback button click
  const handleFeedback = (messageIndex, rating) => {
    const messageId = `msg-${sessionId}-${messageIndex}`;
    
    // Get the question and answer for this message
    const question = messages[messageIndex - 1]?.content || '';
    const answer = messages[messageIndex]?.content || '';
    
    submitFeedback(messageId, question, answer, rating);
  };

  // Send message with streaming
  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const question = input.trim();
    setInput('');

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: question }]);

    // Start streaming
    setIsStreaming(true);
    setStreamingContent('');

    try {
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          session_id: sessionId,
          conversation_history: conversationHistory
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let completeAnswer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.chunk) {
                completeAnswer += data.chunk;
                setStreamingContent(completeAnswer);
              } else if (data.done) {
                setConversationHistory(prev => [
                  ...prev,
                  { question, answer: completeAnswer, timestamp: new Date().toISOString() }
                ]);
                
                setMessages(prev => [...prev, { role: 'assistant', content: completeAnswer }]);
                setStreamingContent('');
                setIsStreaming(false);
              } else if (data.error) {
                throw new Error(data.error);
              }
            } catch (parseError) {
              console.error('JSON parse error:', parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${error.message}` }]);
      setStreamingContent('');
      setIsStreaming(false);
    }
  };

  // Clear chat
  const handleClearChat = () => {
    setMessages([]);
    setFeedbackGiven({});
  };

  // Clear memory
  const handleClearMemory = () => {
    setConversationHistory([]);
  };

  // Handle suggested question click
  const handleSuggestionClick = (questionText) => {
    setInput(questionText);
  };

  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <div className="logo-container">
          <img src={ironLadyLogo} alt="Iron Lady Logo" className="logo-img" />
        </div>
        <div className="header-text">
          <h1>100BM AI Assistant</h1>
          <p>Iron Lady Leadership Program</p>
        </div>
      </div>

      {/* Memory Status */}
      {conversationHistory.length > 0 && (
        <div className="memory-status">
          🧠 <strong>Memory Active:</strong> Remembering {conversationHistory.length} conversation(s)
        </div>
      )}

      {/* Suggested Questions */}
      {messages.length === 0 && !isStreaming && (
        <>
          <div className="suggestions-header">
            <span className="bulb-icon">💡</span> Try these questions:
          </div>
          <div className="suggestions-buttons">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button 
                key={i} 
                className="suggestion-btn"
                onClick={() => handleSuggestionClick(q.text)}
              >
                <span className="suggestion-emoji">{q.emoji}</span> {q.text}
              </button>
            ))}
          </div>
        </>
      )}

      {/* Chat Container */}
      <div className="chat-container">
        {/* Welcome message */}
        {messages.length === 0 && !isStreaming && (
          <div className="message-box welcome-box">
            <div className="message-label">🤖 Assistant</div>
            <div className="welcome-title">👋 Welcome to 100BM AI Chat!</div>
            <div className="welcome-text">
              I'm your intelligent assistant for the <strong>Iron Lady Leadership Program</strong>. Tell me your profession for personalized advice!
            </div>
            <div className="badges">
              <span className="badge pink">🎯 Profile-Aware</span>
              <span className="badge orange">📚 100BM Content</span>
              <span className="badge red">⚡ Real-Time</span>
              <span className="badge green">🧠 Memory Enabled</span>
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div key={i} className={`message-box ${msg.role}-box`}>
            <div className="message-label">
              {msg.role === 'user' ? '👤 You' : '🤖 Assistant'}
            </div>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
            
            {/* Feedback buttons for assistant messages only */}
            {msg.role === 'assistant' && (
              <div className="feedback-buttons">
                <button
                  className={`feedback-btn thumbs-up ${feedbackGiven[`msg-${sessionId}-${i}`] === 'positive' ? 'active' : ''}`}
                  onClick={() => handleFeedback(i, 'positive')}
                  disabled={feedbackGiven[`msg-${sessionId}-${i}`]}
                  title="Helpful response"
                >
                  👍
                </button>
                <button
                  className={`feedback-btn thumbs-down ${feedbackGiven[`msg-${sessionId}-${i}`] === 'negative' ? 'active' : ''}`}
                  onClick={() => handleFeedback(i, 'negative')}
                  disabled={feedbackGiven[`msg-${sessionId}-${i}`]}
                  title="Not helpful"
                >
                  👎
                </button>
              </div>
            )}
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <div className="message-box assistant-box">
            <div className="message-label">🤖 Assistant</div>
            <div className="message-content typing">
              <ReactMarkdown>{streamingContent}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="input-section">
        <input
          type="text"
          className="message-input"
          placeholder="Ask a question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isStreaming}
        />
        <div className="action-buttons">
          <button 
            className="action-btn send-btn"
            onClick={handleSend} 
            disabled={isStreaming || !input.trim()}
          >
            ↗️ Send
          </button>
          <button 
            className="action-btn clear-btn"
            onClick={handleClearChat} 
            disabled={isStreaming}
          >
            🗑️ Clear Chat
          </button>
          <button 
            className="action-btn memory-btn"
            onClick={handleClearMemory} 
            disabled={isStreaming}
          >
            🧠 Clear Memory
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;