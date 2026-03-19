import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Upload, Search, FileText, Trash2, FolderOpen } from 'lucide-react';
import { api } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type Operation = 'upload_document' | 'query' | 'list_documents' | 'delete_document' | 'clear_collection';

interface Collection {
    id: string;
    name: string;
    document_count: number;
    chunk_count: number;
}

interface Document {
    document_id: string;
    filename: string;
    total_chunks: number;
}

interface ContextStoreConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const OPERATIONS: { value: Operation; label: string; description: string; icon: React.ReactNode }[] = [
    { value: 'upload_document', label: 'Upload Document', description: 'Upload PDF, TXT, or Markdown for semantic search', icon: <Upload className="w-4 h-4" /> },
    { value: 'query', label: 'Query', description: 'Search for relevant content using semantic similarity', icon: <Search className="w-4 h-4" /> },
    { value: 'list_documents', label: 'List Documents', description: 'View all documents in a collection', icon: <FileText className="w-4 h-4" /> },
    { value: 'delete_document', label: 'Delete Document', description: 'Remove a document from the collection', icon: <Trash2 className="w-4 h-4" /> },
    { value: 'clear_collection', label: 'Clear Collection', description: 'Remove all documents from a collection', icon: <FolderOpen className="w-4 h-4" /> },
];

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Operation Forms ──────────────────────────────────────────────────────────

const UploadDocumentForm: React.FC<{
    params: Record<string, unknown>;
    onChange: (p: Record<string, unknown>) => void;
    collections: Collection[];
}> = ({ params, onChange, collections }) => {
    const [dragActive, setDragActive] = useState(false);
    const [fileName, setFileName] = useState<string>('');

    const handleFile = async (file: File) => {
        const ext = file.name.split('.').pop()?.toLowerCase();
        if (ext !== 'pdf' && ext !== 'txt' && ext !== 'md') {
            alert('Please upload a PDF, TXT, or Markdown file');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target?.result as string;
            const base64 = content.split(',')[1];
            onChange({
                ...params,
                file_content: base64,
                filename: file.name,
                file_type: ext,
            });
            setFileName(file.name);
        };
        reader.readAsDataURL(file);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    return (
        <div className="space-y-4">
            <Field label="Collection Name" hint="Documents will be stored in this collection">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="my-documents"
                    value={(params.collection_name as string) || ''}
                    onChange={(e) => onChange({ ...params, collection_name: e.target.value })}
                    list="collections-list"
                />
                <datalist id="collections-list">
                    {collections.map((c) => (
                        <option key={c.id} value={c.name} />
                    ))}
                </datalist>
            </Field>

            <Field label="Document File" hint="Upload a PDF, TXT, or Markdown file">
                <div
                    className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                        dragActive
                            ? 'border-orange-500 bg-orange-500/10'
                            : 'border-slate-700 hover:border-slate-600'
                    }`}
                    onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                    onDragLeave={() => setDragActive(false)}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        accept=".pdf,.txt,.md"
                        className="hidden"
                        id="document-upload"
                        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />
                    <label htmlFor="document-upload" className="cursor-pointer">
                        <Upload className="w-8 h-8 mx-auto mb-2 text-slate-500" />
                        {fileName ? (
                            <p className="text-sm text-orange-400 font-medium">{fileName}</p>
                        ) : (
                            <>
                                <p className="text-sm text-slate-400">Drop file here or click to browse</p>
                                <p className="text-xs text-slate-500 mt-1">PDF, TXT, or Markdown</p>
                            </>
                        )}
                    </label>
                </div>
            </Field>

            <div className="grid grid-cols-2 gap-4">
                <Field label="Chunk Size" hint="Characters per chunk">
                    <input
                        type="number"
                        className={inputClass}
                        placeholder="500"
                        min={100}
                        max={2000}
                        value={(params.chunk_size as number) || 500}
                        onChange={(e) => onChange({ ...params, chunk_size: parseInt(e.target.value, 10) })}
                    />
                </Field>
                <Field label="Chunk Overlap" hint="Overlap between chunks">
                    <input
                        type="number"
                        className={inputClass}
                        placeholder="50"
                        min={0}
                        max={200}
                        value={(params.chunk_overlap as number) || 50}
                        onChange={(e) => onChange({ ...params, chunk_overlap: parseInt(e.target.value, 10) })}
                    />
                </Field>
            </div>
        </div>
    );
};

const QueryForm: React.FC<{
    params: Record<string, unknown>;
    onChange: (p: Record<string, unknown>) => void;
    collections: Collection[];
}> = ({ params, onChange, collections }) => (
    <div className="space-y-4">
        <Field label="Collection">
            <div className="relative">
                <select
                    value={(params.collection_name as string) || ''}
                    onChange={(e) => onChange({ ...params, collection_name: e.target.value })}
                    className={`${inputClass} appearance-none pr-8`}
                >
                    <option value="">Select a collection...</option>
                    {collections.map((c) => (
                        <option key={c.id} value={c.name}>
                            {c.name} ({c.document_count} docs, {c.chunk_count} chunks)
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>

        <Field label="Query Text" hint="What are you looking for?">
            <textarea
                className={`${inputClass} resize-none h-24`}
                placeholder="Enter your search query..."
                value={(params.query_text as string) || ''}
                onChange={(e) => onChange({ ...params, query_text: e.target.value })}
            />
        </Field>

        <Field label="Number of Results">
            <input
                type="range"
                min={1}
                max={20}
                value={(params.top_k as number) || 5}
                onChange={(e) => onChange({ ...params, top_k: parseInt(e.target.value, 10) })}
                className="w-full accent-orange-500"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>1</span>
                <span className="text-orange-400 font-medium">{(params.top_k as number) || 5} results</span>
                <span>20</span>
            </div>
        </Field>
    </div>
);

const ListDocumentsForm: React.FC<{
    params: Record<string, unknown>;
    onChange: (p: Record<string, unknown>) => void;
    collections: Collection[];
}> = ({ params, onChange, collections }) => (
    <div className="space-y-4">
        <Field label="Collection">
            <div className="relative">
                <select
                    value={(params.collection_name as string) || ''}
                    onChange={(e) => onChange({ ...params, collection_name: e.target.value })}
                    className={`${inputClass} appearance-none pr-8`}
                >
                    <option value="">Select a collection...</option>
                    {collections.map((c) => (
                        <option key={c.id} value={c.name}>
                            {c.name} ({c.document_count} docs)
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>
    </div>
);

const DeleteDocumentForm: React.FC<{
    params: Record<string, unknown>;
    onChange: (p: Record<string, unknown>) => void;
    collections: Collection[];
    documents: Document[];
    onCollectionChange: (name: string) => void;
}> = ({ params, onChange, collections, documents, onCollectionChange }) => (
    <div className="space-y-4">
        <Field label="Collection">
            <div className="relative">
                <select
                    value={(params.collection_name as string) || ''}
                    onChange={(e) => {
                        onChange({ ...params, collection_name: e.target.value, document_id: '' });
                        onCollectionChange(e.target.value);
                    }}
                    className={`${inputClass} appearance-none pr-8`}
                >
                    <option value="">Select a collection...</option>
                    {collections.map((c) => (
                        <option key={c.id} value={c.name}>{c.name}</option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>

        <Field label="Document">
            <div className="relative">
                <select
                    value={(params.document_id as string) || ''}
                    onChange={(e) => onChange({ ...params, document_id: e.target.value })}
                    className={`${inputClass} appearance-none pr-8`}
                    disabled={!params.collection_name}
                >
                    <option value="">Select a document...</option>
                    {documents.map((d) => (
                        <option key={d.document_id} value={d.document_id}>
                            {d.filename} ({d.total_chunks} chunks)
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>

        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
            <p className="text-xs text-red-300 font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> This will permanently delete the document from the vector store.
            </p>
        </div>
    </div>
);

const ClearCollectionForm: React.FC<{
    params: Record<string, unknown>;
    onChange: (p: Record<string, unknown>) => void;
    collections: Collection[];
}> = ({ params, onChange, collections }) => (
    <div className="space-y-4">
        <Field label="Collection">
            <div className="relative">
                <select
                    value={(params.collection_name as string) || ''}
                    onChange={(e) => onChange({ ...params, collection_name: e.target.value })}
                    className={`${inputClass} appearance-none pr-8`}
                >
                    <option value="">Select a collection...</option>
                    {collections.map((c) => (
                        <option key={c.id} value={c.name}>
                            {c.name} ({c.document_count} docs, {c.chunk_count} chunks)
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>

        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
            <p className="text-xs text-red-300 font-medium mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> This will permanently delete ALL documents in this collection.
            </p>
            <label className="flex items-center gap-3 cursor-pointer">
                <input
                    type="checkbox"
                    className="accent-red-500 w-4 h-4"
                    checked={(params.confirmed as boolean) || false}
                    onChange={(e) => onChange({ ...params, confirmed: e.target.checked })}
                />
                <span className="text-sm text-slate-300">I understand this action cannot be undone</span>
            </label>
        </div>
    </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

const ContextStoreConfig: React.FC<ContextStoreConfigProps> = ({ initialData, onSave }) => {
    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) || 'query');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) || {});

    const [collections, setCollections] = useState<Collection[]>([]);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);

    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const res = await api<{ collections: Collection[] }>('/api/context-store/collections', { method: 'GET' });
                setCollections(res.collections || []);
            } catch {
                // API may not be available yet
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const loadDocuments = async (collectionName: string) => {
        if (!collectionName) {
            setDocuments([]);
            return;
        }
        try {
            const res = await api<{ documents: Document[] }>(`/api/context-store/documents/${collectionName}`, { method: 'GET' });
            setDocuments(res.documents || []);
        } catch {
            setDocuments([]);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const result = await api<unknown>('/api/context-store/execute', {
                method: 'POST',
                body: { operation, params },
            });
            setTestResult({ ok: true, data: result });

            // Refresh collections after upload or clear
            if (operation === 'upload_document' || operation === 'clear_collection' || operation === 'delete_document') {
                const res = await api<{ collections: Collection[] }>('/api/context-store/collections', { method: 'GET' });
                setCollections(res.collections || []);
            }
        } catch (err) {
            setTestResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTesting(false);
        }
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;
    const isClearReady = operation !== 'clear_collection' || (params.confirmed as boolean);

    return (
        <div className="space-y-6">
            {/* ── Operation Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-orange-500 rounded-full" />
                    Operation
                </h3>
                <div className="grid grid-cols-2 gap-2">
                    {OPERATIONS.map((op) => (
                        <button
                            key={op.value}
                            type="button"
                            onClick={() => {
                                setOperation(op.value);
                                setParams({});
                                setTestResult(null);
                            }}
                            className={`flex items-center gap-2 p-3 rounded-xl border text-left transition-all ${
                                operation === op.value
                                    ? 'border-orange-500/60 bg-orange-500/10 text-orange-300'
                                    : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                            }`}
                        >
                            {op.icon}
                            <span className="text-xs font-medium">{op.label}</span>
                        </button>
                    ))}
                </div>
                <p className="text-xs text-slate-500 mt-2">{currentOp.description}</p>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Parameters Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-orange-500 rounded-full" />
                    Parameters
                </h3>

                {loading ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading data...
                    </div>
                ) : (
                    <>
                        {operation === 'upload_document' && (
                            <UploadDocumentForm params={params} onChange={setParams} collections={collections} />
                        )}
                        {operation === 'query' && (
                            <QueryForm params={params} onChange={setParams} collections={collections} />
                        )}
                        {operation === 'list_documents' && (
                            <ListDocumentsForm params={params} onChange={setParams} collections={collections} />
                        )}
                        {operation === 'delete_document' && (
                            <DeleteDocumentForm
                                params={params}
                                onChange={setParams}
                                collections={collections}
                                documents={documents}
                                onCollectionChange={loadDocuments}
                            />
                        )}
                        {operation === 'clear_collection' && (
                            <ClearCollectionForm params={params} onChange={setParams} collections={collections} />
                        )}
                    </>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Test & Save ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handleTest}
                    disabled={testing || !isClearReady}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {testing ? 'Running...' : 'Test Operation'}
                </button>

                {testResult && (
                    <div
                        className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-48 ${
                            testResult.ok
                                ? 'bg-green-500/10 border-green-500/30 text-green-300'
                                : 'bg-red-500/10 border-red-500/30 text-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {testResult.ok ? (
                                <><CheckCircle2 className="w-3.5 h-3.5" /> Success</>
                            ) : (
                                <><AlertCircle className="w-3.5 h-3.5" /> Error</>
                            )}
                        </div>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(testResult.data, null, 2)}</pre>
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => onSave({ operation, params })}
                    disabled={!isClearReady}
                    className="w-full py-3 bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-600 hover:via-orange-600 hover:to-amber-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl shadow-lg shadow-orange-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default ContextStoreConfig;
