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
    Sun,
    ChevronRight,
    Plus
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

    return (
        <div className="min-h-screen bg-[var(--bg-primary)] overflow-y-auto">
            {/* Top Header */}
            <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] sticky top-0 z-20 shadow-sm">
                <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <Link
                            to="/chat"
                            className="group flex items-center gap-2 p-2 px-4 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl hover:bg-[var(--bg-hover)] transition-all font-semibold text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-sm active:scale-95"
                        >
                            <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                            Exit to Chat
                        </Link>
                        <div className="h-8 w-[1px] bg-[var(--border-color)]" />
                        <h1 className="text-xl font-black text-[var(--text-primary)] tracking-tight uppercase">
                            Admin <span className="text-blue-500">Dashboard</span>
                        </h1>
                    </div>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={toggleDarkMode}
                            className="w-11 h-11 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-xl hover:bg-[var(--bg-hover)] transition-all flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-sm active:scale-90"
                            aria-label="Toggle theme"
                        >
                            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                        </button>
                        <button
                            onClick={loadData}
                            className="flex items-center gap-2 h-11 px-5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-all font-bold text-sm shadow-md shadow-blue-500/10 active:scale-95 disabled:opacity-50"
                            disabled={loading}
                        >
                            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            {loading ? 'Refreshing...' : 'Refresh Data'}
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-16 flex flex-col gap-16">
                {/* Metrics Grid */}
                <section>
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex flex-col gap-1">
                            <h2 className="text-2xl font-extrabold text-[var(--text-primary)] tracking-tight">System Metrics</h2>
                            <p className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-widest opacity-70">Real-time status overview</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            { label: 'Documents', value: metrics?.documents.total || 0, icon: <FileText className="text-blue-500" />, color: 'blue' },
                            { label: 'Conversations', value: metrics?.conversations.total || 0, icon: <MessageSquare className="text-emerald-500" />, color: 'emerald' },
                            { label: 'Total Tokens', value: metrics?.tokens.total_tokens.toLocaleString() || 0, icon: <Database className="text-indigo-500" />, color: 'indigo' },
                            { label: 'Cloud Cost', value: `$${metrics?.tokens.total_cost_usd.toFixed(4) || '0.0000'}`, icon: <DollarSign className="text-amber-500" />, color: 'amber' }
                        ].map((stat, i) => (
                            <div key={i} className="group bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-6 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                                <div className="flex items-start justify-between mb-4">
                                    <div className={`p-4 bg-[var(--bg-tertiary)] rounded-2xl group-hover:scale-110 transition-transform duration-500 ring-4 ring-transparent group-hover:ring-${stat.color}-500/5`}>
                                        {stat.icon}
                                    </div>
                                    <ChevronRight size={16} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                                </div>
                                <div className="text-[11px] font-bold text-[var(--text-tertiary)] uppercase tracking-[0.2em] mb-1">{stat.label}</div>
                                <div className="text-2xl font-black text-[var(--text-primary)] tracking-tight">{stat.value}</div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Action Row: Uploads */}
                <section>
                    <div className="flex flex-col gap-6">
                        <div className="flex flex-col gap-1">
                            <h2 className="text-2xl font-extrabold text-[var(--text-primary)] tracking-tight">Content Management</h2>
                            <p className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-widest opacity-70">Import new knowledge bases</p>
                        </div>

                        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-[32px] p-8 shadow-sm">
                            <div className="grid md:grid-cols-2 gap-8 divide-x-0 md:divide-x divide-[var(--border-color)]">
                                {/* Single Upload */}
                                <div className="pr-0 md:pr-8 flex flex-col gap-4">
                                    <div className="flex flex-col gap-1">
                                        <h3 className="text-lg font-bold text-[var(--text-primary)]">Single Document</h3>
                                        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">Fast import for individual policy files or guides.</p>
                                    </div>
                                    <label className="group flex items-center justify-center gap-3 w-full px-6 py-4 bg-[var(--bg-tertiary)] border-2 border-dashed border-[var(--border-color)] rounded-2xl hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 cursor-pointer transition-all disabled:opacity-50">
                                        <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center group-hover:scale-110 transition-transform">
                                            <Plus size={20} strokeWidth={3} />
                                        </div>
                                        <span className="font-bold text-[var(--text-primary)]">Select File</span>
                                        <input type="file" onChange={handleFileUpload} accept=".pdf,.doc,.docx,.txt" disabled={uploading || multiFileUploading} className="hidden" />
                                    </label>
                                </div>

                                {/* Bulk Upload */}
                                <div className="pl-0 md:pl-8 flex flex-col gap-4">
                                    <div className="flex flex-col gap-1">
                                        <h3 className="text-lg font-bold text-[var(--text-primary)]">Bulk Ingestion</h3>
                                        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">Import entire directories for large-scale RAG builds.</p>
                                    </div>
                                    <label className="group flex items-center justify-center gap-3 w-full px-6 py-4 bg-[var(--bg-tertiary)] border-2 border-dashed border-[var(--border-color)] rounded-2xl hover:border-emerald-500 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/10 cursor-pointer transition-all disabled:opacity-50">
                                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center group-hover:scale-110 transition-transform">
                                            <Upload size={20} strokeWidth={3} />
                                        </div>
                                        <span className="font-bold text-[var(--text-primary)]">Batch Upload</span>
                                        <input type="file" onChange={handleMultiFileUpload} accept=".pdf,.doc,.docx,.txt" multiple disabled={uploading || multiFileUploading} className="hidden" />
                                    </label>
                                </div>
                            </div>

                            {/* Status Feed */}
                            {(uploadProgress || uploadStatuses.length > 0) && (
                                <div className="mt-10 pt-8 border-t border-[var(--border-color)]">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                                        <h3 className="text-[10px] font-black text-[var(--text-secondary)] uppercase tracking-[0.3em]">Processing Live Feed</h3>
                                    </div>

                                    {uploadProgress && (
                                        <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-2xl text-[13px] font-bold text-blue-500 mb-4 animate-in fade-in slide-in-from-top-2">
                                            {uploadProgress}
                                        </div>
                                    )}

                                    <div className="grid gap-3">
                                        {uploadStatuses.map((status, idx) => (
                                            <div key={idx} className={`flex items-center gap-4 p-4 rounded-2xl border transition-all ${status.status === 'success' ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-600' :
                                                status.status === 'failed' ? 'bg-red-500/5 border-red-500/20 text-red-600' :
                                                    status.status === 'duplicate' ? 'bg-amber-500/5 border-amber-500/20 text-amber-600' :
                                                        'bg-blue-500/5 border-blue-500/20 text-blue-600'
                                                }`}>
                                                <div className="shrink-0 font-bold text-lg">
                                                    {status.status === 'uploading' ? <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" /> :
                                                        status.status === 'success' ? '✓' :
                                                            status.status === 'failed' ? '!' : '△'}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-xs font-black uppercase tracking-wider truncate mb-0.5">{status.name}</div>
                                                    <div className="text-[11px] font-medium opacity-80 uppercase tracking-widest shrink-0">
                                                        {status.progress || (status.status === 'success' && 'Confirmed') || (status.status === 'duplicate' && 'Duplicate Skipped') || (status.status === 'failed' && (status.error || 'Failed')) || 'Queueing...'}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* Database Explorer */}
                <section className="mb-12">
                    <div className="flex flex-col gap-1 mb-8">
                        <h2 className="text-2xl font-extrabold text-[var(--text-primary)] tracking-tight">Knowledge Base</h2>
                        <p className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-widest opacity-70">Indexed document database</p>
                    </div>

                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-[32px] overflow-hidden shadow-sm">
                        <div className="overflow-x-auto scrollbar-hide">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-[var(--bg-tertiary)] border-b border-[var(--border-color)]">
                                        {['Title', 'Meta', 'Size', 'Pages', 'Chunks', 'Status', 'Actions'].map((h) => (
                                            <th key={h} className="px-8 py-5 text-left text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] whitespace-nowrap">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[var(--border-color)]">
                                    {documents.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} className="px-8 py-24 text-center">
                                                <div className="flex flex-col items-center gap-4 opacity-30">
                                                    <Database size={48} />
                                                    <p className="text-sm font-bold uppercase tracking-widest">No indices found</p>
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        documents.map((doc) => (
                                            <tr key={doc.hash} className="group hover:bg-[var(--bg-hover)] transition-all duration-300">
                                                <td className="px-8 py-6">
                                                    <div className="flex flex-col gap-1">
                                                        <span className="text-sm font-bold text-[var(--text-primary)] group-hover:text-blue-500 transition-colors">{doc.title}</span>
                                                        <span className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-widest">{doc.hash.slice(0, 12)}...</span>
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6">
                                                    <span className="text-[11px] font-bold text-[var(--text-secondary)] uppercase tracking-wider bg-[var(--bg-tertiary)] px-2.5 py-1.5 rounded-lg border border-[var(--border-color)]">
                                                        {doc.mime_type.split('/')[1] || doc.mime_type}
                                                    </span>
                                                </td>
                                                <td className="px-8 py-6 text-sm font-bold text-[var(--text-secondary)]">{formatBytes(doc.file_size)}</td>
                                                <td className="px-8 py-6 text-sm font-bold text-[var(--text-secondary)]">{doc.page_count}</td>
                                                <td className="px-8 py-6 text-sm font-bold text-[var(--text-secondary)]">{doc.chunk_count}</td>
                                                <td className="px-8 py-6 text-sm font-bold text-[var(--text-secondary)]">
                                                    <div className="flex items-center gap-2">
                                                        <div className={`w-2 h-2 rounded-full ${doc.status === 'indexed' ? 'bg-emerald-500 shadow-lg shadow-emerald-500/40' :
                                                            doc.status === 'processing' ? 'bg-blue-500 shadow-lg shadow-blue-500/40 animate-pulse' :
                                                                'bg-red-500'
                                                            }`} />
                                                        <span className="text-[11px] font-black uppercase tracking-widest opacity-80">{doc.status}</span>
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6">
                                                    <div className="flex items-center gap-3">
                                                        {doc.signed_url && (
                                                            <a
                                                                href={doc.signed_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="w-10 h-10 flex items-center justify-center bg-blue-500/5 text-blue-500 border border-blue-500/20 rounded-xl hover:bg-blue-500 hover:text-white transition-all shadow-sm active:scale-90"
                                                                title="View document"
                                                            >
                                                                <ExternalLink size={16} />
                                                            </a>
                                                        )}
                                                        <button
                                                            onClick={() => deleteDocument(doc.hash, doc.title)}
                                                            disabled={deleting === doc.hash}
                                                            className="w-10 h-10 flex items-center justify-center bg-red-500/5 text-red-500 border border-red-500/20 rounded-xl hover:bg-red-500 hover:text-white transition-all shadow-sm active:scale-90 disabled:opacity-50"
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
