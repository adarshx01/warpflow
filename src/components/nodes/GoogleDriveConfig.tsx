import React, { useState, useEffect } from 'react';
import { Plus, ChevronDown, ExternalLink, CheckCircle2, AlertCircle, Loader2, Play } from 'lucide-react';
import { api } from '../../lib/api';

type Operation = 'list_files' | 'get_file' | 'upload_file' | 'download_file' | 'delete_file' | 'create_folder' | 'share_file';

interface Credential { id: string; name: string; type: string; }

interface GoogleDriveConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'list_files', label: 'List Files', description: 'List files in Google Drive' },
    { value: 'get_file', label: 'Get File', description: 'Get file metadata by ID' },
    { value: 'upload_file', label: 'Upload File', description: 'Create/upload a file with text content' },
    { value: 'download_file', label: 'Download File', description: 'Download or export file content' },
    { value: 'delete_file', label: 'Delete File', description: 'Move a file to trash' },
    { value: 'create_folder', label: 'Create Folder', description: 'Create a new folder in Drive' },
    { value: 'share_file', label: 'Share File', description: 'Share a file with a user or make public' },
];

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const ListFilesForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Search Query" hint="Filter files by name. Leave empty to list all.">
            <input type="text" className={inputClass} placeholder="Search files..." value={(params.query as string) ?? ''} onChange={(e) => onChange({ ...params, query: e.target.value })} />
        </Field>
        <Field label="Folder ID" hint="Optional. List files inside a specific folder.">
            <input type="text" className={inputClass} placeholder="Folder ID" value={(params.folderId as string) ?? ''} onChange={(e) => onChange({ ...params, folderId: e.target.value })} />
        </Field>
        <Field label="Page Size">
            <input type="number" className={inputClass} min={1} max={100} placeholder="20" value={(params.pageSize as number) ?? 20} onChange={(e) => onChange({ ...params, pageSize: parseInt(e.target.value, 10) || 20 })} />
        </Field>
    </div>
);

const GetFileForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="File ID" hint="The Google Drive file ID.">
            <input type="text" className={inputClass} placeholder="File ID" value={(params.fileId as string) ?? ''} onChange={(e) => onChange({ ...params, fileId: e.target.value })} />
        </Field>
    </div>
);

const UploadFileForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="File Name">
            <input type="text" className={inputClass} placeholder="document.txt" value={(params.name as string) ?? ''} onChange={(e) => onChange({ ...params, name: e.target.value })} />
        </Field>
        <Field label="Content">
            <textarea className={`${inputClass} resize-none h-28`} placeholder="File content..." value={(params.content as string) ?? ''} onChange={(e) => onChange({ ...params, content: e.target.value })} />
        </Field>
        <Field label="MIME Type" hint="Default: text/plain">
            <input type="text" className={inputClass} placeholder="text/plain" value={(params.mimeType as string) ?? ''} onChange={(e) => onChange({ ...params, mimeType: e.target.value })} />
        </Field>
        <Field label="Folder ID" hint="Optional. Place file in a specific folder.">
            <input type="text" className={inputClass} placeholder="Folder ID" value={(params.folderId as string) ?? ''} onChange={(e) => onChange({ ...params, folderId: e.target.value })} />
        </Field>
    </div>
);

const DownloadFileForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="File ID">
            <input type="text" className={inputClass} placeholder="File ID" value={(params.fileId as string) ?? ''} onChange={(e) => onChange({ ...params, fileId: e.target.value })} />
        </Field>
        <Field label="Export MIME Type" hint="For Google Workspace files. Default: text/plain">
            <input type="text" className={inputClass} placeholder="text/plain" value={(params.exportMimeType as string) ?? ''} onChange={(e) => onChange({ ...params, exportMimeType: e.target.value })} />
        </Field>
    </div>
);

const DeleteFileForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="File ID">
            <input type="text" className={inputClass} placeholder="File ID" value={(params.fileId as string) ?? ''} onChange={(e) => onChange({ ...params, fileId: e.target.value })} />
        </Field>
    </div>
);

const CreateFolderForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Folder Name">
            <input type="text" className={inputClass} placeholder="New Folder" value={(params.name as string) ?? ''} onChange={(e) => onChange({ ...params, name: e.target.value })} />
        </Field>
        <Field label="Parent Folder ID" hint="Optional. Create inside another folder.">
            <input type="text" className={inputClass} placeholder="Parent folder ID" value={(params.parentId as string) ?? ''} onChange={(e) => onChange({ ...params, parentId: e.target.value })} />
        </Field>
    </div>
);

const ShareFileForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="File ID">
            <input type="text" className={inputClass} placeholder="File ID" value={(params.fileId as string) ?? ''} onChange={(e) => onChange({ ...params, fileId: e.target.value })} />
        </Field>
        <Field label="Share Type">
            <div className="flex gap-2">
                {[{ value: 'user', label: 'Specific User' }, { value: 'anyone', label: 'Anyone with link' }].map((t) => (
                    <button key={t.value} type="button" onClick={() => onChange({ ...params, type: t.value })}
                        className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium border transition-all ${(params.type ?? 'user') === t.value ? 'bg-green-500/20 border-green-500/60 text-green-300' : 'bg-slate-800 border-slate-700/50 text-slate-400 hover:border-slate-600'}`}>{t.label}</button>
                ))}
            </div>
        </Field>
        {(params.type ?? 'user') === 'user' && (
            <Field label="Email Address">
                <input type="email" className={inputClass} placeholder="user@example.com" value={(params.email as string) ?? ''} onChange={(e) => onChange({ ...params, email: e.target.value })} />
            </Field>
        )}
        <Field label="Permission Role">
            <select value={(params.role as string) ?? 'reader'} onChange={(e) => onChange({ ...params, role: e.target.value })} className={`${inputClass} appearance-none`}>
                <option value="reader">Viewer</option>
                <option value="commenter">Commenter</option>
                <option value="writer">Editor</option>
            </select>
        </Field>
    </div>
);

const GoogleDriveConfig: React.FC<GoogleDriveConfigProps> = ({ initialData, onSave }) => {
    const [credentials, setCredentials] = useState<Credential[]>([]);
    const [loadingCreds, setLoadingCreds] = useState(true);
    const [showNewCredForm, setShowNewCredForm] = useState(false);
    const [newCred, setNewCred] = useState({ name: '', clientId: '', clientSecret: '' });
    const [savingCred, setSavingCred] = useState(false);

    const [credentialId, setCredentialId] = useState((initialData.credentialId as string) ?? '');
    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'list_files');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? {});
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const data = await api<Credential[]>('/api/credentials?type=google-drive', { method: 'GET' });
                setCredentials(data);
                if (data.length > 0 && !credentialId) setCredentialId(data[0].id);
            } catch { /* ignore */ } finally { setLoadingCreds(false); }
        })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleAddCredential = async () => {
        if (!newCred.name || !newCred.clientId || !newCred.clientSecret) return;
        setSavingCred(true);
        try {
            const created = await api<Credential>('/api/credentials', { method: 'POST', body: { type: 'google-drive', name: newCred.name, client_id: newCred.clientId, client_secret: newCred.clientSecret } });
            setCredentials((prev) => [...prev, created]);
            setCredentialId(created.id);
            setShowNewCredForm(false);
            setNewCred({ name: '', clientId: '', clientSecret: '' });
        } catch (err) { alert(`Failed: ${(err as Error).message}`); } finally { setSavingCred(false); }
    };

    const handleConnectGoogle = () => { window.open(`http://localhost:8000/api/google-drive/oauth/start?credential_id=${credentialId}`, '_blank'); };

    const handleTest = async () => {
        setTesting(true); setTestResult(null);
        try {
            const result = await api<unknown>('/api/google-drive/execute', { method: 'POST', body: { credentialId, operation, params } });
            setTestResult({ ok: true, data: result });
        } catch (err) { setTestResult({ ok: false, data: { error: (err as Error).message } }); } finally { setTesting(false); }
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-yellow-400 to-green-500 rounded-full" />Google Account
                </h3>
                {loadingCreds ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Loading credentials...</div>
                ) : (
                    <div className="space-y-3">
                        {credentials.length > 0 && (
                            <div className="relative">
                                <select value={credentialId} onChange={(e) => setCredentialId(e.target.value)} className={`${inputClass} appearance-none pr-8`}>
                                    {credentials.map((c) => (<option key={c.id} value={c.id}>✅ {c.name}</option>))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        )}
                        <div className="flex gap-2">
                            <button type="button" onClick={() => setShowNewCredForm((v) => !v)} className="flex items-center gap-1.5 text-xs text-green-400 hover:text-green-300 font-medium transition-colors">
                                <Plus className="w-4 h-4" />{credentials.length === 0 ? 'Add Google Account' : 'Add another account'}
                            </button>
                            {credentialId && (
                                <button type="button" onClick={handleConnectGoogle} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 font-medium transition-colors ml-auto">
                                    <ExternalLink className="w-3.5 h-3.5" />Re-connect Google
                                </button>
                            )}
                        </div>
                        {showNewCredForm && (
                            <div className="border border-slate-700/50 rounded-xl overflow-hidden">
                                <div className="bg-green-500/10 border-b border-green-500/20 px-4 py-3">
                                    <p className="text-xs font-semibold text-green-300 mb-2">🔑 Setup Instructions</p>
                                    <ol className="text-xs text-slate-300 space-y-1.5 list-decimal list-inside">
                                        <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-green-400 underline">Google Cloud Console</a></li>
                                        <li>Create OAuth credentials (Web application)</li>
                                        <li>Add redirect URI: <span className="font-mono text-yellow-300 text-[11px]">http://localhost:8000/api/google-drive/oauth/callback</span></li>
                                        <li>Enable <span className="text-white font-medium">Google Drive API</span></li>
                                    </ol>
                                </div>
                                <div className="p-4 space-y-4 bg-slate-800/60">
                                    <div><label className={labelClass}>Nickname</label><input type="text" className={inputClass} placeholder="e.g. Work Account" value={newCred.name} onChange={(e) => setNewCred({ ...newCred, name: e.target.value })} /></div>
                                    <div><label className={labelClass}>Client ID</label><input type="text" className={inputClass} placeholder="123...apps.googleusercontent.com" value={newCred.clientId} onChange={(e) => setNewCred({ ...newCred, clientId: e.target.value })} /></div>
                                    <div><label className={labelClass}>Client Secret</label><input type="password" className={inputClass} placeholder="GOCSPX-..." value={newCred.clientSecret} onChange={(e) => setNewCred({ ...newCred, clientSecret: e.target.value })} /></div>
                                    <button type="button" onClick={handleAddCredential} disabled={savingCred || !newCred.name || !newCred.clientId || !newCred.clientSecret}
                                        className="w-full py-2.5 bg-gradient-to-r from-yellow-500 to-green-500 hover:from-yellow-600 hover:to-green-600 disabled:opacity-40 text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
                                        {savingCred ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}{savingCred ? 'Saving...' : 'Save & Connect'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-yellow-400 to-green-500 rounded-full" />Operation
                </h3>
                <div className="relative">
                    <select value={operation} onChange={(e) => { setOperation(e.target.value as Operation); setParams({}); setTestResult(null); }} className={`${inputClass} appearance-none pr-8`}>
                        {OPERATIONS.map((op) => (<option key={op.value} value={op.value}>{op.label}</option>))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
                <p className="text-xs text-slate-500 mt-2">{currentOp.description}</p>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-yellow-400 to-green-500 rounded-full" />Parameters
                </h3>
                {operation === 'list_files' && <ListFilesForm params={params} onChange={setParams} />}
                {operation === 'get_file' && <GetFileForm params={params} onChange={setParams} />}
                {operation === 'upload_file' && <UploadFileForm params={params} onChange={setParams} />}
                {operation === 'download_file' && <DownloadFileForm params={params} onChange={setParams} />}
                {operation === 'delete_file' && <DeleteFileForm params={params} onChange={setParams} />}
                {operation === 'create_folder' && <CreateFolderForm params={params} onChange={setParams} />}
                {operation === 'share_file' && <ShareFileForm params={params} onChange={setParams} />}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section className="space-y-3">
                <button type="button" onClick={handleTest} disabled={testing || !credentialId}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 disabled:opacity-40 text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
                    {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}{testing ? 'Running...' : 'Test Operation'}
                </button>
                {testResult && (
                    <div className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-40 ${testResult.ok ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {testResult.ok ? <><CheckCircle2 className="w-3.5 h-3.5" /> Success</> : <><AlertCircle className="w-3.5 h-3.5" /> Error</>}
                        </div>
                        {JSON.stringify(testResult.data, null, 2)}
                    </div>
                )}
                <button type="button" onClick={() => onSave({ credentialId, operation, params })}
                    className="w-full py-3 bg-gradient-to-r from-yellow-500 via-green-500 to-blue-500 hover:from-yellow-600 hover:via-green-600 hover:to-blue-600 text-white font-bold rounded-xl shadow-lg shadow-green-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default GoogleDriveConfig;
