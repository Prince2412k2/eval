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
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <aside className={`
        relative border-r border-[var(--border-color)] bg-[var(--bg-secondary)] 
        flex flex-col transition-all duration-300 ease-in-out shrink-0 z-20 
        ${sidebarOpen ? 'w-[320px]' : 'w-0'}
      `}>
        <div className="flex flex-col h-full overflow-hidden">
          <div className="p-6 border-b border-[var(--border-color)]">
            <button
              onClick={startNewChat}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 active:scale-[0.98] transition-all font-semibold text-sm mb-4 shadow-sm"
            >
              <Plus size={18} strokeWidth={3} />
              New Chat
            </button>
            <div className="flex gap-3">
              <button
                onClick={toggleDarkMode}
                className="flex-1 p-3 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl hover:bg-[var(--bg-hover)] transition-all flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                aria-label="Toggle theme"
              >
                {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="flex-1 p-3 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl hover:bg-[var(--bg-hover)] transition-all flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                aria-label="Collapse sidebar"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-hide">
            {conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-[var(--text-tertiary)] px-4">
                <MessageSquare size={48} opacity={0.3} className="mb-4" />
                <p className="text-sm font-medium text-center">No history yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {conversations.map(conv => (
                  <div
                    key={conv.id}
                    className={`
                      relative p-4 rounded-xl cursor-pointer transition-all border group
                      ${conversationId === conv.id
                        ? 'bg-blue-50/50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800'
                        : 'bg-transparent border-transparent hover:bg-[var(--bg-hover)]'
                      }
                    `}
                    onClick={() => loadConversation(conv.id)}
                  >
                    <div className="flex-1 min-w-0 pr-8">
                      <div className="text-sm font-semibold text-[var(--text-primary)] truncate mb-1">
                        {conv.title || 'Untitled Chat'}
                      </div>
                      <div className="text-xs text-[var(--text-tertiary)] font-medium">
                        {conv.message_count} {conv.message_count === 1 ? 'message' : 'messages'}
                      </div>
                    </div>
                    <button
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-2 opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all text-red-500"
                      onClick={(e) => deleteConversation(conv.id, e)}
                      title="Delete conversation"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative min-w-0 h-full">
        {/* Mobile-style Toggle */}
        {!sidebarOpen && (
          <button
            className="absolute top-6 left-6 z-30 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg hover:bg-[var(--bg-hover)] active:scale-95 transition-all text-[var(--text-primary)]"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>
        )}

        <main className="flex-1 flex flex-col h-full bg-[var(--bg-primary)] px-6 py-12">
          <div className="flex-1 overflow-y-auto scrollbar-hide py-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center">
                <div className="w-24 h-24 bg-blue-500/10 rounded-3xl flex items-center justify-center mb-10 animate-bounce-slow">
                  <Bot size={48} className="text-blue-500" />
                </div>
                <h1 className="text-4xl font-extrabold text-[var(--text-primary)] mb-4 tracking-tight">
                  How can I help you?
                </h1>
                <p className="text-lg text-[var(--text-secondary)] leading-relaxed font-medium">
                  I'm your AI assistant, ready to help you analyze policy documents, extract insights, and answer questions with citations.
                </p>
                <div className="grid grid-cols-2 gap-4 mt-12 w-full max-w-lg">
                  {['Summarize my documents', 'Extract key terms', 'Find citation policy', 'Verify coverage'].map((item) => (
                    <button
                      key={item}
                      onClick={() => setInput(item)}
                      className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-sm font-semibold text-[var(--text-secondary)] hover:border-blue-400 hover:text-blue-500 transition-all text-left shadow-sm"
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto flex flex-col gap-10">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-5 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <div className={`
                      w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm
                      ${message.role === 'assistant'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                      }
                    `}>
                      {message.role === 'assistant' ? <Bot size={22} /> : <User size={22} />}
                    </div>

                    <div className={`flex flex-col gap-2 max-w-[85%] ${message.role === 'user' ? 'items-end' : ''}`}>
                      <div className="flex items-center gap-2 px-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-tertiary)]">
                          {message.role === 'assistant' ? 'Assistant' : 'You'}
                        </span>
                        {message.timestamp && (
                          <span className="text-[10px] text-[var(--text-tertiary)]">
                            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      <div className={`
                        relative px-6 py-4 rounded-3xl shadow-sm text-[15px] leading-[1.6]
                        ${message.role === 'user'
                          ? 'bg-blue-500 text-white rounded-tr-none'
                          : 'bg-[var(--bg-message-assistant)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-tl-none'
                        }
                      `}>
                        <div className={message.role === 'assistant' ? 'prose prose-sm dark:prose-invert max-w-none' : ''}>
                          {message.role === 'assistant' ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {message.content}
                            </ReactMarkdown>
                          ) : (
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          )}
                        </div>

                        {message.citations && message.citations.length > 0 && (
                          <div className="mt-6 pt-4 border-t border-[var(--border-color)]/30">
                            <details className="group/details">
                              <summary className="flex items-center gap-2 text-xs font-bold cursor-pointer text-blue-500 hover:text-blue-600 transition-colors list-none uppercase tracking-widest">
                                <FileText size={16} strokeWidth={2.5} />
                                <span>{message.citations.length} Ref{message.citations.length === 1 ? 'erence' : 'erences'}</span>
                                <ChevronDown size={14} className="group-open/details:rotate-180 transition-transform ml-auto" />
                              </summary>
                              <div className="mt-4 space-y-3">
                                {message.citations.map((citation, idx) => (
                                  <div key={idx} className="flex gap-4 p-4 bg-[var(--bg-citation)] rounded-2xl border border-[var(--border-color)] group/item hover:border-blue-200 transition-colors shadow-sm">
                                    <div className="w-7 h-7 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center text-xs font-black shrink-0">
                                      {idx + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <a
                                        href={citation.document_url ? `${citation.document_url}#page=${citation.page_number}` : '#'}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs font-bold text-[var(--text-primary)] hover:text-blue-500 transition-colors block mb-1.5"
                                      >
                                        {citation.document_name} • Page {citation.page_number}
                                      </a>
                                      <div className="text-[13px] text-[var(--text-secondary)] italic font-medium leading-normal line-clamp-3">
                                        "{citation.text_span}"
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </div>
                        )}

                        {message.sources && message.sources.length > 0 && (
                          <div className="mt-4 flex flex-wrap gap-2">
                            {message.sources.map((source, idx) => (
                              <a
                                key={idx}
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-500 rounded-lg text-[11px] font-bold uppercase tracking-wider hover:bg-blue-500/20 transition-all border border-blue-500/20"
                              >
                                📄 {source.name}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            )}
          </div>

          {/* Footer / Input */}
          <footer className="w-full bg-gradient-to-t from-[var(--bg-primary)] via-[var(--bg-primary)] to-transparent pt-10 pb-8 px-6">
            <div className="max-w-4xl mx-auto relative group">
              <form
                onSubmit={handleSubmit}
                className="relative flex items-end bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-[32px] p-2 pr-4 shadow-xl shadow-blue-500/5 focus-within:border-blue-400 transition-all group-hover:shadow-blue-500/10 focus-within:shadow-blue-500/15"
              >
                <div className="flex-1 relative">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e as any);
                      }
                    }}
                    placeholder="Ask a follow-up or a new question..."
                    className="w-full max-h-[200px] min-h-[56px] pl-6 pr-4 py-4 bg-transparent border-none focus:ring-0 text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] resize-none text-[16px] scrollbar-hide"
                    disabled={isLoading}
                    rows={1}
                  />
                </div>
                <button
                  type="submit"
                  className="mb-1 w-12 h-12 bg-blue-500 text-white rounded-full flex items-center justify-center hover:bg-blue-600 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 transition-all shadow-md active:scale-95 disabled:scale-100 disabled:shadow-none"
                  disabled={isLoading || !input.trim()}
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Send size={18} strokeWidth={3} />
                  )}
                </button>
              </form>
              <div className="mt-3 text-center">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-tertiary)]">
                  AI-generated answers. Verify critical information.
                </p>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default ChatPage;
