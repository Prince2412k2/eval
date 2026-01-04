import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Moon, Sun, Send, FileText, ChevronDown } from 'lucide-react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  sources?: Source[];
  timestamp?: Date;
}

interface Citation {
  document_name: string;
  document_id: string;
  document_url?: string;
  page_number: number;
  section?: string;
  text_span: string;
  claim_text: string;
  citation_type: string;
}

interface Source {
  name: string;
  url: string;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: input,
          conversation_id: conversationId
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';
      let finalData: any = null;

      // Add empty assistant message that we'll update
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '',
        timestamp: new Date()
      }]);

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'stream') {
              assistantMessage += data.data;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  role: 'assistant',
                  content: assistantMessage,
                  timestamp: new Date()
                };
                return newMessages;
              });
            } else if (data.type === 'final') {
              finalData = data;
              if (data.conversation_id && !conversationId) {
                setConversationId(data.conversation_id);
              }
            }
          }
        }
      }

      // Update final message with citations and sources
      if (finalData) {
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            role: 'assistant',
            content: finalData.data,
            citations: finalData.citations,
            sources: finalData.sources,
            timestamp: new Date()
          };
          return newMessages;
        });
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, an error occurred. Please try again.',
          timestamp: new Date()
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <Bot className="bot-icon" size={28} />
            <h1 className="app-title">Policy Assistant</h1>
          </div>
          <div className="header-actions">
            <p className="app-subtitle">Ask questions about your policy documents</p>
            <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle theme">
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="chat-container">
        <div className="messages-wrapper">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <h2>Start a conversation</h2>
              <p>Ask any question about your policy documents</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`message-wrapper ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-container">
                  {message.role === 'assistant' && (
                    <div className="message-avatar assistant-avatar">
                      <Bot size={16} />
                    </div>
                  )}

                  <div className="message-bubble-wrapper">
                    <div className="message-header">
                      <span className="message-sender">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </span>
                      {message.timestamp && (
                        <span className="message-time">
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>

                    <div className={`message-bubble ${message.role}`}>
                      <div className="message-content">
                        {message.role === 'assistant' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        ) : (
                          message.content
                        )}
                      </div>

                      {/* Citations */}
                      {message.citations && message.citations.length > 0 && (
                        <details className="citations-dropdown">
                          <summary className="citations-toggle">
                            <FileText size={14} />
                            {message.citations.length} {message.citations.length === 1 ? 'citation' : 'citations'}
                            <ChevronDown size={14} className="chevron" />
                          </summary>
                          <div className="citations-content">
                            {message.citations.map((citation, idx) => (
                              <div key={idx} className="citation-item">
                                <div className="citation-badge">{idx + 1}</div>
                                <div className="citation-details">
                                  {citation.document_url ? (
                                    <a
                                      href={`${citation.document_url}#page=${citation.page_number}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="citation-doc-link"
                                    >
                                      {citation.document_name} • Page {citation.page_number}
                                    </a>
                                  ) : (
                                    <div className="citation-doc">
                                      {citation.document_name} • Page {citation.page_number}
                                    </div>
                                  )}
                                  <div className="citation-text">"{citation.text_span}"</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}

                      {/* Sources */}
                      {message.sources && message.sources.length > 0 && (
                        <div className="sources">
                          {message.sources.map((source, idx) => (
                            <a
                              key={idx}
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="source-link"
                            >
                              📄 {source.name}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {message.role === 'user' && (
                    <div className="message-avatar user-avatar">
                      <User size={16} />
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="input-container">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="input-field"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-button"
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? <div className="loading-spinner" /> : <Send size={18} />}
          </button>
        </form>
      </footer>
    </div>
  );
}

export default App;
