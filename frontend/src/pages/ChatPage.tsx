import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Send, FileText, ChevronDown, Plus, MessageSquare, Trash2, Moon, Sun } from 'lucide-react';
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
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const { isDarkMode, toggleDarkMode } = useDarkMode();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load conversations from localStorage on mount
    useEffect(() => {
        loadConversations();
        const activeId = localStorage.getItem(ACTIVE_CONVERSATION_KEY);
        if (activeId) {
            loadConversation(activeId);
        }
    }, []);

    const loadConversations = async () => {
        try {
            // Get conversation IDs from localStorage
            const storedIds = localStorage.getItem(STORAGE_KEY);
            if (!storedIds) {
                setConversations([]);
                return;
            }

            const ids: string[] = JSON.parse(storedIds);

            // Fetch conversation details from backend
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

                // Convert messages to UI format
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
            ids.unshift(id); // Add to beginning
            localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
            loadConversations(); // Reload to update sidebar
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
                // Remove from localStorage
                const storedIds = localStorage.getItem(STORAGE_KEY);
                if (storedIds) {
                    const ids: string[] = JSON.parse(storedIds);
                    const newIds = ids.filter(cId => cId !== id);
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(newIds));
                }

                // If this was the active conversation, clear it
                if (conversationId === id) {
                    startNewChat();
                }

                // Reload conversations
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
        <div className="chat-page">
            {/* Sidebar */}
            <aside className="conversation-sidebar open">
                <div className="sidebar-header">
                    <button onClick={startNewChat} className="new-chat-btn">
                        <Plus size={18} />
                        New Chat
                    </button>
                    <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle theme">
                        {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
                    </button>
                </div>

                <div className="conversations-list">
                    {conversations.length === 0 ? (
                        <div className="empty-conversations">
                            <MessageSquare size={32} opacity={0.3} />
                            <p>No conversations yet</p>
                        </div>
                    ) : (
                        conversations.map(conv => (
                            <div
                                key={conv.id}
                                className={`conversation-item ${conversationId === conv.id ? 'active' : ''}`}
                                onClick={() => loadConversation(conv.id)}
                            >
                                <div className="conversation-info">
                                    <div className="conversation-title">
                                        {conv.title || 'New Chat'}
                                    </div>
                                    <div className="conversation-meta">
                                        {conv.message_count} messages
                                    </div>
                                </div>
                                <button
                                    className="delete-conversation-btn"
                                    onClick={(e) => deleteConversation(conv.id, e)}
                                    title="Delete conversation"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </aside>

            {/* Main Chat Area */}
            <main className="chat-main">
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
            </main>
        </div>
    );
}

export default ChatPage;
