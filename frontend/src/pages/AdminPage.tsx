import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    FileText,
    MessageSquare,
    Database,
    DollarSign,
    Trash2,
    ExternalLink,
    ArrowLeft,
    RefreshCw,
    Upload,
    Moon,
    Sun
} from 'lucide-react';
import { useDarkMode } from '../contexts/DarkModeContext';

interface Metrics {
    documents: { total: number };
    conversations: { total: number };
    messages: { total: number };
    tokens: {
        total_tokens: number;
        prompt_tokens: number;
        completion_tokens: number;
        total_cost_usd: number;
    };
}

interface Document {
    id: string;
    title: string;
    hash: string;
    mime_type: string;
    created_at: string;
    file_size: number;
    page_count: number;
    chunk_count: number;
    status: string;
    signed_url?: string;
}

function AdminPage() {
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState<string>('');
    const { isDarkMode, toggleDarkMode } = useDarkMode();

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        await Promise.all([loadMetrics(), loadDocuments()]);
        setLoading(false);
    };

    const loadMetrics = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/admin/metrics');
            if (response.ok) {
                const data = await response.json();
                setMetrics(data);
            }
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    };

    const loadDocuments = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/admin/documents');
            if (response.ok) {
                const data = await response.json();
                setDocuments(data.documents || []);
            }
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    };

    const deleteDocument = async (docId: string, title: string) => {
        if (!confirm(`Delete "${title}"? This will remove the document from all systems.`)) {
            return;
        }

        setDeleting(docId);
        try {
            const response = await fetch(`http://localhost:8000/api/admin/documents/${docId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await loadData(); // Reload both metrics and documents
            } else {
                alert('Failed to delete document');
            }
        } catch (error) {
            console.error('Failed to delete document:', error);
            alert('Failed to delete document');
        } finally {
            setDeleting(null);
        }
    };

    const formatBytes = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setUploadProgress('Uploading...');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://localhost:8000/api/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                setUploadProgress('Processing document...');

                // Poll for completion or wait for response
                const result = await response.json();

                setUploadProgress('Upload complete!');
                setTimeout(() => {
                    setUploadProgress('');
                    loadData(); // Reload data
                }, 1500);
            } else {
                const error = await response.json();
                alert(`Upload failed: ${error.detail || 'Unknown error'}`);
                setUploadProgress('');
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('Upload failed. Please try again.');
            setUploadProgress('');
        } finally {
            setUploading(false);
            // Reset file input
            e.target.value = '';
        }
    };

    return (
        <div className="admin-page">
            <header className="admin-header">
                <div className="admin-header-content">
                    <div className="admin-title-section">
                        <Link to="/chat" className="back-link">
                            <ArrowLeft size={20} />
                        </Link>
                        <h1 className="admin-title">Admin Dashboard</h1>
                    </div>
                    <div className="admin-actions">
                        <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle theme">
                            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                        </button>
                        <button onClick={loadData} className="refresh-btn" disabled={loading}>
                            <RefreshCw size={18} className={loading ? 'spinning' : ''} />
                            Refresh
                        </button>
                    </div>
                </div>
            </header>

            <main className="admin-content">
                {/* Metrics Section */}
                <section className="metrics-section">
                    <h2 className="section-title">System Metrics</h2>
                    <div className="metrics-grid">
                        <div className="metric-card">
                            <div className="metric-icon documents">
                                <FileText size={24} />
                            </div>
                            <div className="metric-info">
                                <div className="metric-label">Documents</div>
                                <div className="metric-value">{metrics?.documents.total || 0}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon conversations">
                                <MessageSquare size={24} />
                            </div>
                            <div className="metric-info">
                                <div className="metric-label">Conversations</div>
                                <div className="metric-value">{metrics?.conversations.total || 0}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon messages">
                                <Database size={24} />
                            </div>
                            <div className="metric-info">
                                <div className="metric-label">Messages</div>
                                <div className="metric-value">{metrics?.messages.total || 0}</div>
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-icon tokens">
                                <DollarSign size={24} />
                            </div>
                            <div className="metric-info">
                                <div className="metric-label">Token Usage</div>
                                <div className="metric-value">
                                    {(metrics?.tokens.total_tokens || 0).toLocaleString()}
                                </div>
                                <div className="metric-subtext">
                                    ${(metrics?.tokens.total_cost_usd || 0).toFixed(4)} cost
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Documents Section */}
                <section className="documents-section">
                    <div className="section-header">
                        <h2 className="section-title">Document Management</h2>
                        <div className="upload-section">
                            {uploadProgress && (
                                <span className="upload-progress">{uploadProgress}</span>
                            )}
                            <label htmlFor="file-upload" className={`upload-btn ${uploading ? 'uploading' : ''}`}>
                                <Upload size={18} />
                                {uploading ? 'Uploading...' : 'Upload Document'}
                            </label>
                            <input
                                id="file-upload"
                                type="file"
                                accept=".pdf,.doc,.docx,.txt"
                                onChange={handleFileUpload}
                                disabled={uploading}
                                style={{ display: 'none' }}
                            />
                        </div>
                    </div>

                    {documents.length === 0 ? (
                        <div className="empty-documents">
                            <FileText size={48} opacity={0.3} />
                            <p>No documents uploaded yet</p>
                        </div>
                    ) : (
                        <div className="documents-table-wrapper">
                            <table className="documents-table">
                                <thead>
                                    <tr>
                                        <th>Title</th>
                                        <th>Type</th>
                                        <th>Size</th>
                                        <th>Pages</th>
                                        <th>Chunks</th>
                                        <th>Created</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {documents.map(doc => (
                                        <tr key={doc.id}>
                                            <td className="doc-title">
                                                {doc.signed_url ? (
                                                    <a
                                                        href={doc.signed_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="doc-link"
                                                    >
                                                        {doc.title}
                                                        <ExternalLink size={14} />
                                                    </a>
                                                ) : (
                                                    doc.title
                                                )}
                                            </td>
                                            <td>{doc.mime_type.split('/')[1]?.toUpperCase() || 'PDF'}</td>
                                            <td>{formatBytes(doc.file_size)}</td>
                                            <td>{doc.page_count || '-'}</td>
                                            <td>{doc.chunk_count || '-'}</td>
                                            <td>{formatDate(doc.created_at)}</td>
                                            <td>
                                                <button
                                                    onClick={() => deleteDocument(doc.id, doc.title)}
                                                    className="delete-btn"
                                                    disabled={deleting === doc.id}
                                                    title="Delete document"
                                                >
                                                    {deleting === doc.id ? (
                                                        <div className="mini-spinner" />
                                                    ) : (
                                                        <Trash2 size={16} />
                                                    )}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}

export default AdminPage;
