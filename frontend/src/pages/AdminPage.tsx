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

interface UploadFileStatus {
    name: string;
    status: 'uploading' | 'success' | 'failed' | 'duplicate';
    progress?: string;
    error?: string;
    result?: any;
}

function AdminPage() {
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState<string>('');
    const [multiFileUploading, setMultiFileUploading] = useState(false);
    const [uploadStatuses, setUploadStatuses] = useState<UploadFileStatus[]>([]);
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
                await loadDocuments();
                await loadMetrics();
            } else {
                alert('Failed to delete document');
            }
        } catch (error) {
            console.error('Delete error:', error);
            alert('Failed to delete document');
        } finally {
            setDeleting(null);
        }
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
                setUploadProgress('Upload successful!');
                await loadDocuments();
                await loadMetrics();
                setTimeout(() => setUploadProgress(''), 2000);
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
            e.target.value = '';
        }
    };

    const handleMultiFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const fileArray = Array.from(files);
        setMultiFileUploading(true);

        const statusMap = new Map<string, UploadFileStatus>();
        fileArray.forEach(file => {
            statusMap.set(file.name, {
                name: file.name,
                status: 'uploading',
                progress: 'Starting...'
            });
        });
        setUploadStatuses(Array.from(statusMap.values()));

        try {
            const formData = new FormData();
            fileArray.forEach(file => {
                formData.append('files', file);
            });

            const response = await fetch('http://localhost:8000/api/upload/bulk', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload request failed');
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error('No response body');
            }

            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            let frontendStatus: 'uploading' | 'success' | 'failed' | 'duplicate' = 'uploading';
                            if (data.status === 'success') {
                                frontendStatus = 'success';
                            } else if (data.status === 'failed') {
                                frontendStatus = 'failed';
                            } else if (data.status === 'duplicate') {
                                frontendStatus = 'duplicate';
                            }
                            
                            statusMap.set(data.filename, {
                                name: data.filename,
                                status: frontendStatus,
                                progress: data.message || data.stage,
                                error: data.error,
                                result: data
                            });
                            
                            setUploadStatuses(Array.from(statusMap.values()));
                        } catch (err) {
                            console.error('Failed to parse SSE data:', err);
                        }
                    }
                }
            }

            setTimeout(() => {
                loadData();
                setTimeout(() => {
                    setUploadStatuses([]);
                }, 5000);
            }, 1500);

        } catch (error) {
            console.error('Upload error:', error);
            alert('Upload failed. Please try again.');
            setUploadStatuses([]);
        } finally {
            setMultiFileUploading(false);
            e.target.value = '';
        }
    };

    const formatBytes = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
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

    return (
        <div className="min-h-screen bg-[var(--color-bg-primary)]">
            <header className="bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Link to="/chat" className="p-2 hover:bg-[var(--color-bg-hover)] rounded-lg transition-colors">
                                <ArrowLeft size={20} className="text-[var(--color-text-primary)]" />
                            </Link>
                            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
                        </div>
                        <div className="flex items-center gap-2">
                            <button 
                                onClick={toggleDarkMode} 
                                className="p-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors"
                                aria-label="Toggle theme"
                            >
                                {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                            </button>
                            <button 
                                onClick={loadData} 
                                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors disabled:opacity-50"
                                disabled={loading}
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8">
                {/* Metrics Section */}
                <section className="mb-8">
                    <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-4">System Metrics</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-6 hover:shadow-lg transition-shadow">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                                    <FileText size={24} className="text-blue-600 dark:text-blue-400" />
                                </div>
                                <div>
                                    <div className="text-sm text-[var(--color-text-secondary)]">Documents</div>
                                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{metrics?.documents.total || 0}</div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-6 hover:shadow-lg transition-shadow">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                                    <MessageSquare size={24} className="text-green-600 dark:text-green-400" />
                                </div>
                                <div>
                                    <div className="text-sm text-[var(--color-text-secondary)]">Conversations</div>
                                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{metrics?.conversations.total || 0}</div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-6 hover:shadow-lg transition-shadow">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                                    <Database size={24} className="text-purple-600 dark:text-purple-400" />
                                </div>
                                <div>
                                    <div className="text-sm text-[var(--color-text-secondary)]">Total Tokens</div>
                                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{metrics?.tokens.total_tokens.toLocaleString() || 0}</div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-6 hover:shadow-lg transition-shadow">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                                    <DollarSign size={24} className="text-amber-600 dark:text-amber-400" />
                                </div>
                                <div>
                                    <div className="text-sm text-[var(--color-text-secondary)]">Total Cost</div>
                                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">${metrics?.tokens.total_cost_usd.toFixed(4) || '0.0000'}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Upload Section */}
                <section className="mb-8">
                    <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-4">Upload Documents</h2>
                    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-6">
                        <div className="flex flex-wrap gap-4">
                            <div>
                                <label className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                                    <Upload size={18} />
                                    Upload Single
                                    <input
                                        type="file"
                                        onChange={handleFileUpload}
                                        accept=".pdf,.doc,.docx,.txt"
                                        disabled={uploading || multiFileUploading}
                                        className="hidden"
                                    />
                                </label>
                            </div>
                            <div>
                                <label className="flex items-center gap-2 px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                                    <Upload size={18} />
                                    Upload Multiple
                                    <input
                                        type="file"
                                        onChange={handleMultiFileUpload}
                                        accept=".pdf,.doc,.docx,.txt"
                                        multiple
                                        disabled={uploading || multiFileUploading}
                                        className="hidden"
                                    />
                                </label>
                            </div>
                        </div>

                        {uploadProgress && (
                            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-blue-700 dark:text-blue-300">
                                {uploadProgress}
                            </div>
                        )}

                        {uploadStatuses.length > 0 && (
                            <div className="mt-4">
                                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-2">Upload Progress</h3>
                                <div className="space-y-2">
                                    {uploadStatuses.map((status, idx) => (
                                        <div key={idx} className={`flex items-center gap-3 p-3 rounded-lg border ${
                                            status.status === 'success' ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' :
                                            status.status === 'failed' ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' :
                                            status.status === 'duplicate' ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800' :
                                            'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                                        }`}>
                                            <span className="text-lg">
                                                {status.status === 'uploading' && '⏳'}
                                                {status.status === 'success' && '✓'}
                                                {status.status === 'failed' && '✗'}
                                                {status.status === 'duplicate' && '⚠'}
                                            </span>
                                            <span className="font-medium text-sm text-[var(--color-text-primary)] flex-shrink-0">{status.name}</span>
                                            <span className="text-sm text-[var(--color-text-secondary)] flex-1">
                                                {status.progress || (status.status === 'success' && 'Uploaded successfully') || (status.status === 'duplicate' && 'Already exists') || (status.status === 'failed' && (status.error || 'Upload failed')) || 'Processing...'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </section>

                {/* Documents Section */}
                <section>
                    <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-4">Documents</h2>
                    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Title</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Type</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Size</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Pages</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Chunks</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Created</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[var(--color-border)]">
                                    {documents.length === 0 ? (
                                        <tr>
                                            <td colSpan={8} className="px-6 py-12 text-center text-[var(--color-text-tertiary)]">
                                                No documents found
                                            </td>
                                        </tr>
                                    ) : (
                                        documents.map((doc) => (
                                            <tr key={doc.hash} className="hover:bg-[var(--color-bg-hover)] transition-colors">
                                                <td className="px-6 py-4 text-sm font-medium text-[var(--color-text-primary)]">{doc.title}</td>
                                                <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">{doc.mime_type}</td>
                                                <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">{formatBytes(doc.file_size)}</td>
                                                <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">{doc.page_count}</td>
                                                <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">{doc.chunk_count}</td>
                                                <td className="px-6 py-4">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                                        doc.status === 'indexed' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                                                        doc.status === 'processing' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                                                        'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                                                    }`}>
                                                        {doc.status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">{formatDate(doc.created_at)}</td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        {doc.signed_url && (
                                                            <a
                                                                href={doc.signed_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                                                title="View document"
                                                            >
                                                                <ExternalLink size={16} />
                                                            </a>
                                                        )}
                                                        <button
                                                            onClick={() => deleteDocument(doc.hash, doc.title)}
                                                            disabled={deleting === doc.hash}
                                                            className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                                                            title="Delete document"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default AdminPage;
