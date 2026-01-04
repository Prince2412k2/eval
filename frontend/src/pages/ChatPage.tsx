import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Send, FileText, ChevronDown, Plus, MessageSquare, Trash2, Moon, Sun, Menu, X } from 'lucide-react';
import { useDarkMode } from '../contexts/DarkModeContext';

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

interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

const STORAGE_KEY = 'chat_conversations';
const ACTIVE_CONVERSATION_KEY = 'active_conversation_id';

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isDarkMode, toggleDarkMode } = useDarkMode();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadConversations();
    const activeId = localStorage.getItem(ACTIVE_CONVERSATION_KEY);
    if (activeId) {
      loadConversation(activeId);
    }
  }, []);

  const loadConversations = async () => {
    try {
      const storedIds = localStorage.getItem(STORAGE_KEY);
      if (!storedIds) {
        setConversations([]);
        return;
      }

      const ids: string[] = JSON.parse(storedIds);
      const conversationPromises = ids.map(async (id) => {
        try {
          const response = await fetch(`http://localhost:8000/api/conversations/${id}`);
          if (response.ok) {
            const data = await response.json();
            return {
              id: data.id,
              title: data.title || getConversationTitle(data.messages),
              created_at: data.created_at,
              updated_at: data.updated_at,
              message_count: data.messages?.length || 0
            };
          }
          return null;
        } catch (error) {
          console.error(`Failed to load conversation ${id}:`, error);
          return null;
        }
      });

      const loadedConversations = (await Promise.all(conversationPromises))
        .filter((c): c is ConversationSummary => c !== null)
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

      setConversations(loadedConversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      setConversations([]);
    }
  };

  const getConversationTitle = (messages: any[]): string => {
    if (!messages || messages.length === 0) return 'New Chat';
    const firstUserMessage = messages.find(m => m.role === 'user');
    if (firstUserMessage) {
      return firstUserMessage.content.slice(0, 50) + (firstUserMessage.content.length > 50 ? '...' : '');
    }
    return 'New Chat';
  };

  const loadConversation = async (id: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/conversations/${id}`);
      if (response.ok) {
        const data = await response.json();
        setConversationId(id);
        localStorage.setItem(ACTIVE_CONVERSATION_KEY, id);

        const loadedMessages: Message[] = data.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          citations: msg.citations,
          sources: msg.sources,
          timestamp: new Date(msg.created_at)
        }));

        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const saveConversationId = (id: string) => {
    const storedIds = localStorage.getItem(STORAGE_KEY);
    const ids: string[] = storedIds ? JSON.parse(storedIds) : [];

    if (!ids.includes(id)) {
      ids.unshift(id);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
      loadConversations();
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      const response = await fetch(`http://localhost:8000/api/conversations/${id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        const storedIds = localStorage.getItem(STORAGE_KEY);
        if (storedIds) {
          const ids: string[] = JSON.parse(storedIds);
          const newIds = ids.filter(cId => cId !== id);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newIds));
        }

        if (conversationId === id) {
          startNewChat();
        }

        loadConversations();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
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
              if (data.conversation_id) {
                const newConvId = data.conversation_id;
                setConversationId(newConvId);
                localStorage.setItem(ACTIVE_CONVERSATION_KEY, newConvId);
                saveConversationId(newConvId);
              }
            }
          }
        }
      }

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
    <div className="flex h-screen bg-[var(--color-bg-primary)]">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col transition-all duration-300 ease-in-out overflow-hidden shrink-0`}>
        <div className="p-4 border-b border-[var(--color-border)]">
          <button 
            onClick={startNewChat} 
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium text-sm mb-3"
          >
            <Plus size={18} />
            New Chat
          </button>
          <div className="flex gap-2">
            <button 
              onClick={toggleDarkMode} 
              className="flex-1 p-2.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors flex items-center justify-center"
              aria-label="Toggle theme"
            >
              {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button 
              onClick={() => setSidebarOpen(false)} 
              className="flex-1 p-2.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors flex items-center justify-center"
              aria-label="Collapse sidebar"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 scrollbar-none [&::-webkit-scrollbar]:hidden">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-tertiary)] px-4">
              <MessageSquare size={40} opacity={0.3} className="mb-3" />
              <p className="text-sm text-center">No conversations yet</p>
            </div>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                className={`p-3 mb-2 rounded-lg cursor-pointer transition-all flex items-start justify-between group ${
                  conversationId === conv.id 
                    ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' 
                    : 'hover:bg-[var(--color-bg-hover)] border border-transparent'
                }`}
                onClick={() => loadConversation(conv.id)}
              >
                <div className="flex-1 min-w-0 pr-2">
                  <div className="text-sm font-medium text-[var(--color-text-primary)] truncate mb-1">
                    {conv.title || 'New Chat'}
                  </div>
                  <div className="text-xs text-[var(--color-text-tertiary)]">
                    {conv.message_count} {conv.message_count === 1 ? 'message' : 'messages'}
                  </div>
                </div>
                <button
                  className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all shrink-0"
                  onClick={(e) => deleteConversation(conv.id, e)}
                  title="Delete conversation"
                >
                  <Trash2 size={14} className="text-red-600 dark:text-red-400" />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Toggle Button */}
      {!sidebarOpen && (
        <button
          className="fixed top-4 left-4 z-50 p-3 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg shadow-lg hover:bg-[var(--color-bg-hover)] hover:scale-105 transition-all"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
        >
          <Menu size={20} />
        </button>
      )}

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-none [&::-webkit-scrollbar]:hidden">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="text-6xl mb-6">💬</div>
              <h2 className="text-3xl font-bold text-[var(--color-text-primary)] mb-3">How can I help you today?</h2>
              <p className="text-base text-[var(--color-text-secondary)] max-w-md">Ask any question about your policy documents and I'll provide detailed answers with citations.</p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shrink-0 shadow-sm">
                      <Bot size={18} className="text-white" />
                    </div>
                  )}

                  <div className={`flex-1 max-w-3xl ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                    <div className="mb-1.5 flex items-center gap-2">
                      <span className="text-xs font-semibold text-[var(--color-text-primary)]">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </span>
                      {message.timestamp && (
                        <span className="text-xs text-[var(--color-text-tertiary)]">
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>

                    <div className={`rounded-2xl px-4 py-3 ${
                      message.role === 'user' 
                        ? 'bg-blue-500 text-white inline-block' 
                        : 'bg-[var(--color-bg-message-assistant)] border border-[var(--color-border)]'
                    }`}>
                      <div className={`text-[15px] leading-relaxed ${message.role === 'assistant' ? 'prose prose-sm dark:prose-invert max-w-none' : ''}`}>
                        {message.role === 'assistant' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        ) : (
                          message.content
                        )}
                      </div>

                      {message.citations && message.citations.length > 0 && (
                        <details className="mt-4 group/details">
                          <summary className="flex items-center gap-2 text-sm cursor-pointer text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors list-none">
                            <FileText size={14} />
                            <span className="font-medium">{message.citations.length} {message.citations.length === 1 ? 'citation' : 'citations'}</span>
                            <ChevronDown size={14} className="group-open/details:rotate-180 transition-transform" />
                          </summary>
                          <div className="mt-3 space-y-2">
                            {message.citations.map((citation, idx) => (
                              <div key={idx} className="flex gap-3 p-3 bg-[var(--color-bg-citation)] rounded-lg text-sm border border-[var(--color-border)]">
                                <div className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-semibold shrink-0">
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  {citation.document_url ? (
                                    <a
                                      href={`${citation.document_url}#page=${citation.page_number}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 dark:text-blue-400 hover:underline font-medium block mb-1"
                                    >
                                      {citation.document_name} • Page {citation.page_number}
                                    </a>
                                  ) : (
                                    <div className="font-medium text-[var(--color-text-primary)] mb-1">
                                      {citation.document_name} • Page {citation.page_number}
                                    </div>
                                  )}
                                  <div className="text-[var(--color-text-secondary)] italic">"{citation.text_span}"</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}

                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {message.sources.map((source, idx) => (
                            <a
                              key={idx}
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                            >
                              📄 {source.name}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {message.role === 'user' && (
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 dark:from-gray-600 dark:to-gray-700 flex items-center justify-center shrink-0 shadow-sm">
                      <User size={18} className="text-white" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-4">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e as any);
                    }
                  }}
                  placeholder="Ask a question..."
                  className="w-full px-4 py-3 bg-[var(--color-bg-input)] border border-[var(--color-border)] rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] resize-none text-base"
                  disabled={isLoading}
                  rows={1}
                  style={{ minHeight: '48px', maxHeight: '200px' }}
                />
              </div>
              <button
                type="submit"
                className="px-5 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center shrink-0 h-12"
                disabled={isLoading || !input.trim()}
              >
                {isLoading ? <div className="loading-spinner" /> : <Send size={20} />}
              </button>
            </div>
          </form>
        </footer>
      </main>
    </div>
  );
}

export default ChatPage;
