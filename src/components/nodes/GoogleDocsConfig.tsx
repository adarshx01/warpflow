import React, { useState, useEffect } from 'react';
import { Plus, ChevronDown, ExternalLink, CheckCircle2, AlertCircle, Loader2, Play } from 'lucide-react';
import { api } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type Operation = 'create' | 'get' | 'update' | 'delete' | 'find_text';

interface Credential {
    id: string;
    name: string;
    type: string;
}


interface GoogleDocsConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'create', label: 'Create Document', description: 'Create a new Google Doc' },
    { value: 'get', label: 'Get Document', description: 'Read a document by ID' },
    { value: 'update', label: 'Update Document', description: 'Append, replace, or edit a paragraph' },
    { value: 'delete', label: 'Delete Document', description: 'Move a document to trash' },
    { value: 'find_text', label: 'Find Text in Document', description: 'Search paragraphs for a string' },
];

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Operation-specific forms ─────────────────────────────────────────────────

const CreateForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Document Title">
            <input
                type="text"
                className={inputClass}
                placeholder="My New Document"
                value={(params.title as string) ?? ''}
                onChange={(e) => onChange({ ...params, title: e.target.value })}
            />
        </Field>
        <Field label="Initial Content" hint="Plain text to insert into the document body on creation.">
            <textarea
                className={`${inputClass} resize-none h-28`}
                placeholder="Hello, world!"
                value={(params.content as string) ?? ''}
                onChange={(e) => onChange({ ...params, content: e.target.value })}
            />
        </Field>
        <Field label="Parent Folder ID" hint="Optional. Drive folder ID to place the document into.">
            <input
                type="text"
                className={inputClass}
                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
                value={(params.folderId as string) ?? ''}
                onChange={(e) => onChange({ ...params, folderId: e.target.value })}
            />
        </Field>
    </div>
);

const GetForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => {
    const fields = (params.fields as string[]) ?? ['all'];
    const toggle = (f: string) =>
        onChange({ ...params, fields: fields.includes(f) ? fields.filter((x) => x !== f) : [...fields, f] });

    return (
        <div className="space-y-4">
            <Field label="Document ID" hint="Found in the URL: docs.google.com/document/d/{documentId}/edit">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
                    value={(params.documentId as string) ?? ''}
                    onChange={(e) => onChange({ ...params, documentId: e.target.value })}
                />
            </Field>
            <Field label="Fields to Return">
                <div className="flex flex-wrap gap-2 mt-1">
                    {['title', 'body', 'revisionId', 'all'].map((f) => (
                        <button
                            key={f}
                            type="button"
                            onClick={() => toggle(f)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${fields.includes(f)
                                ? 'bg-blue-500/20 border-blue-500/60 text-blue-300'
                                : 'bg-slate-800 border-slate-700/50 text-slate-400 hover:border-slate-600'
                                }`}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </Field>
        </div>
    );
};

const UpdateForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => {
    const mode = (params.updateMode as string) ?? 'append';

    return (
        <div className="space-y-4">
            <Field label="Document ID">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
                    value={(params.documentId as string) ?? ''}
                    onChange={(e) => onChange({ ...params, documentId: e.target.value })}
                />
            </Field>
            <Field label="Update Mode">
                <div className="space-y-2">
                    {[
                        { value: 'replace_body', label: 'Replace entire body', desc: 'Clears existing content and replaces it' },
                        { value: 'append', label: 'Append text', desc: 'Adds text after existing content' },
                        { value: 'by_index', label: 'Edit paragraph by index', desc: 'Replaces a specific paragraph' },
                    ].map((opt) => (
                        <label
                            key={opt.value}
                            className={`flex gap-3 p-3 rounded-xl border cursor-pointer transition-all ${mode === opt.value
                                ? 'border-blue-500/60 bg-blue-500/10'
                                : 'border-slate-700/50 bg-slate-800/40 hover:border-slate-600'
                                }`}
                        >
                            <input
                                type="radio"
                                name="updateMode"
                                value={opt.value}
                                checked={mode === opt.value}
                                onChange={() => onChange({ ...params, updateMode: opt.value })}
                                className="mt-0.5 accent-blue-500"
                            />
                            <div>
                                <p className="text-sm text-slate-200 font-medium">{opt.label}</p>
                                <p className="text-xs text-slate-500">{opt.desc}</p>
                            </div>
                        </label>
                    ))}
                </div>
            </Field>
            <Field label="Content">
                <textarea
                    className={`${inputClass} resize-none h-28`}
                    placeholder="Text to insert or replace with..."
                    value={(params.content as string) ?? ''}
                    onChange={(e) => onChange({ ...params, content: e.target.value })}
                />
            </Field>
            {mode === 'by_index' && (
                <Field label="Paragraph Index" hint="0-based index of the paragraph element to replace.">
                    <input
                        type="number"
                        className={inputClass}
                        min={0}
                        placeholder="0"
                        value={(params.paragraphIndex as number) ?? 0}
                        onChange={(e) => onChange({ ...params, paragraphIndex: parseInt(e.target.value, 10) })}
                    />
                </Field>
            )}
        </div>
    );
};

const DeleteForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Document ID">
            <input
                type="text"
                className={inputClass}
                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
                value={(params.documentId as string) ?? ''}
                onChange={(e) => onChange({ ...params, documentId: e.target.value })}
            />
        </Field>
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
            <p className="text-xs text-red-300 font-medium mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> This action moves the document to Google Drive trash.
            </p>
            <label className="flex items-center gap-3 cursor-pointer">
                <input
                    type="checkbox"
                    className="accent-red-500 w-4 h-4"
                    checked={(params.confirmed as boolean) ?? false}
                    onChange={(e) => onChange({ ...params, confirmed: e.target.checked })}
                />
                <span className="text-sm text-slate-300">I understand this action deletes the document</span>
            </label>
        </div>
    </div>
);

const FindTextForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => {
    const scope = (params.scope as string) ?? 'all';

    return (
        <div className="space-y-4">
            <Field label="Document ID">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
                    value={(params.documentId as string) ?? ''}
                    onChange={(e) => onChange({ ...params, documentId: e.target.value })}
                />
            </Field>
            <Field label="Search Query">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="Text to search for..."
                    value={(params.query as string) ?? ''}
                    onChange={(e) => onChange({ ...params, query: e.target.value })}
                />
            </Field>
            <Field label="Search Scope">
                <div className="flex gap-2">
                    {[
                        { value: 'all', label: 'All Paragraphs' },
                        { value: 'indexed', label: 'Specific Paragraph' },
                    ].map((s) => (
                        <button
                            key={s.value}
                            type="button"
                            onClick={() => onChange({ ...params, scope: s.value })}
                            className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium border transition-all ${scope === s.value
                                ? 'bg-blue-500/20 border-blue-500/60 text-blue-300'
                                : 'bg-slate-800 border-slate-700/50 text-slate-400 hover:border-slate-600'
                                }`}
                        >
                            {s.label}
                        </button>
                    ))}
                </div>
            </Field>
            {scope === 'indexed' && (
                <Field label="Paragraph Index" hint="0-based index of the paragraph to search within.">
                    <input
                        type="number"
                        className={inputClass}
                        min={0}
                        placeholder="0"
                        value={(params.paragraphIndex as number) ?? 0}
                        onChange={(e) => onChange({ ...params, paragraphIndex: parseInt(e.target.value, 10) })}
                    />
                </Field>
            )}
            <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-800/40 border border-slate-700/50 rounded-xl">
                <input
                    type="checkbox"
                    className="accent-blue-500 w-4 h-4"
                    checked={(params.returnContext as boolean) ?? false}
                    onChange={(e) => onChange({ ...params, returnContext: e.target.checked })}
                />
                <div>
                    <p className="text-sm text-slate-200">Return match context</p>
                    <p className="text-xs text-slate-500">Include surrounding text in the response</p>
                </div>
            </label>
        </div>
    );
};

// ─── Main Component ───────────────────────────────────────────────────────────

const GoogleDocsConfig: React.FC<GoogleDocsConfigProps> = ({ initialData, onSave }) => {
    const [credentials, setCredentials] = useState<Credential[]>([]);
    const [loadingCreds, setLoadingCreds] = useState(true);
    const [showNewCredForm, setShowNewCredForm] = useState(false);
    const [newCred, setNewCred] = useState({ name: '', clientId: '', clientSecret: '' });
    const [savingCred, setSavingCred] = useState(false);

    const [credentialId, setCredentialId] = useState((initialData.credentialId as string) ?? '');
    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'get');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? {});

    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    // Load credentials on mount
    useEffect(() => {
        (async () => {
            try {
                const data = await api<Credential[]>('/api/credentials?type=google-docs', { method: 'GET' });
                setCredentials(data);
                if (data.length > 0 && !credentialId) setCredentialId(data[0].id);
            } catch {
                // backend may not have credentials endpoint yet — silently ignore
            } finally {
                setLoadingCreds(false);
            }
        })();
    }, []);

    const handleAddCredential = async () => {
        if (!newCred.name || !newCred.clientId || !newCred.clientSecret) return;
        setSavingCred(true);
        try {
            const created = await api<Credential>('/api/credentials', {
                method: 'POST',
                body: {
                    type: 'google-docs',
                    name: newCred.name,
                    client_id: newCred.clientId,
                    client_secret: newCred.clientSecret,
                },
            });
            setCredentials((prev) => [...prev, created]);
            setCredentialId(created.id);
            setShowNewCredForm(false);
            setNewCred({ name: '', clientId: '', clientSecret: '' });
        } catch (err) {
            alert(`Failed to save credential: ${(err as Error).message}`);
        } finally {
            setSavingCred(false);
        }
    };

    const handleConnectGoogle = () => {
        // Opens OAuth flow — backend redirects to Google then back to callback
        window.open(`http://localhost:8000/api/google-docs/oauth/start?credential_id=${credentialId}`, '_blank');
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const result = await api<unknown>('/api/google-docs/execute', {
                method: 'POST',
                body: { credentialId, operation, params },
            });
            setTestResult({ ok: true, data: result });
        } catch (err) {
            setTestResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTesting(false);
        }
    };

    const isDeleteReady = operation !== 'delete' || (params.confirmed as boolean);
    const currentOp = OPERATIONS.find((o) => o.value === operation)!;

    return (
        <div className="space-y-6">
            {/* ── Credentials Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />
                    Google Account
                </h3>

                {loadingCreds ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading credentials...
                    </div>
                ) : (
                    <div className="space-y-3">
                        {credentials.length > 0 && (
                            <div className="relative">
                                <select
                                    value={credentialId}
                                    onChange={(e) => setCredentialId(e.target.value)}
                                    className={`${inputClass} appearance-none pr-8`}
                                >
                                    {credentials.map((c) => (
                                        <option key={c.id} value={c.id}>✅ {c.name}</option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        )}

                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={() => setShowNewCredForm((v) => !v)}
                                className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
                            >
                                <Plus className="w-4 h-4" />
                                {credentials.length === 0 ? 'Add Google Account' : 'Add another account'}
                            </button>
                            {credentialId && (
                                <button
                                    type="button"
                                    onClick={handleConnectGoogle}
                                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 font-medium transition-colors ml-auto"
                                >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                    Re-connect Google
                                </button>
                            )}
                        </div>

                        {showNewCredForm && (
                            <div className="border border-slate-700/50 rounded-xl overflow-hidden">
                                {/* Step-by-step how-to banner */}
                                <div className="bg-blue-500/10 border-b border-blue-500/20 px-4 py-3">
                                    <p className="text-xs font-semibold text-blue-300 mb-2">🔑 How to get these values (one-time setup)</p>
                                    <ol className="text-xs text-slate-300 space-y-1.5 list-decimal list-inside">
                                        <li>Open <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-blue-400 underline hover:text-blue-300">Google Cloud Console</a> and create or select a project</li>
                                        <li>In the left menu, go to <span className="text-white font-medium">APIs &amp; Services → Credentials</span></li>
                                        <li>Click <span className="text-white font-medium">+ Create Credentials → OAuth client ID</span></li>
                                        <li>Under "Application type" choose <span className="text-white font-medium">Web application</span></li>
                                        <li>Under "Authorized redirect URIs", add exactly:<br />
                                            <span className="font-mono text-yellow-300 text-[11px] break-all">http://localhost:8000/api/google-docs/oauth/callback</span>
                                        </li>
                                        <li>Click <span className="text-white font-medium">Create</span> → Google shows your Client ID &amp; Secret</li>
                                        <li>Also enable <span className="text-white font-medium">Google Docs API</span> and <span className="text-white font-medium">Google Drive API</span> from the APIs library</li>
                                    </ol>
                                </div>

                                <div className="p-4 space-y-4 bg-slate-800/60">
                                    {/* Nickname */}
                                    <div>
                                        <label className={labelClass}>Nickname for this account</label>
                                        <input
                                            type="text"
                                            className={inputClass}
                                            placeholder="e.g. Work Google Account"
                                            value={newCred.name}
                                            onChange={(e) => setNewCred({ ...newCred, name: e.target.value })}
                                        />
                                        <p className="text-xs text-slate-500 mt-1.5">
                                            A label just for you — so you can tell your Google accounts apart inside WarpFlow.
                                        </p>
                                    </div>

                                    {/* Client ID */}
                                    <div>
                                        <label className={labelClass}>Client ID</label>
                                        <input
                                            type="text"
                                            className={inputClass}
                                            placeholder="123456789-abc...apps.googleusercontent.com"
                                            value={newCred.clientId}
                                            onChange={(e) => setNewCred({ ...newCred, clientId: e.target.value })}
                                        />
                                        <p className="text-xs text-slate-500 mt-1.5">
                                            Shown on the Credentials page after you create the OAuth client. Looks like a long string ending in <span className="font-mono text-slate-400">.apps.googleusercontent.com</span>
                                        </p>
                                    </div>

                                    {/* Client Secret */}
                                    <div>
                                        <label className={labelClass}>Client Secret</label>
                                        <input
                                            type="password"
                                            className={inputClass}
                                            placeholder="GOCSPX-..."
                                            value={newCred.clientSecret}
                                            onChange={(e) => setNewCred({ ...newCred, clientSecret: e.target.value })}
                                        />
                                        <p className="text-xs text-slate-500 mt-1.5">
                                            Shown next to the Client ID. Usually starts with <span className="font-mono text-slate-400">GOCSPX-</span>. Treat it like a password — don't share it.
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={handleAddCredential}
                                        disabled={savingCred || !newCred.name || !newCred.clientId || !newCred.clientSecret}
                                        className="w-full py-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                                    >
                                        {savingCred ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                                        {savingCred ? 'Saving...' : 'Save & Connect Google Account'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Operation Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />
                    Operation
                </h3>
                <div className="relative">
                    <select
                        value={operation}
                        onChange={(e) => {
                            setOperation(e.target.value as Operation);
                            setParams({});
                            setTestResult(null);
                        }}
                        className={`${inputClass} appearance-none pr-8`}
                    >
                        {OPERATIONS.map((op) => (
                            <option key={op.value} value={op.value}>{op.label}</option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
                <p className="text-xs text-slate-500 mt-2">{currentOp.description}</p>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Operation-specific Fields ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />
                    Parameters
                </h3>

                {operation === 'create' && <CreateForm params={params} onChange={setParams} />}
                {operation === 'get' && <GetForm params={params} onChange={setParams} />}
                {operation === 'update' && <UpdateForm params={params} onChange={setParams} />}
                {operation === 'delete' && <DeleteForm params={params} onChange={setParams} />}
                {operation === 'find_text' && <FindTextForm params={params} onChange={setParams} />}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Test & Save ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handleTest}
                    disabled={testing || !credentialId}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {testing ? 'Running...' : 'Test Operation'}
                </button>

                {testResult && (() => {
                    const isNotConnected =
                        !testResult.ok &&
                        typeof testResult.data === 'object' &&
                        String((testResult.data as { error?: string }).error ?? '').toLowerCase().includes('not connected');

                    if (isNotConnected) {
                        return (
                            <div className="p-3 rounded-xl border bg-orange-500/10 border-orange-500/30 text-orange-300 text-xs space-y-2">
                                <div className="flex items-start gap-1.5 font-sans font-semibold">
                                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                    Google account not connected
                                </div>
                                <p className="font-sans text-orange-300/80 leading-relaxed">
                                    You've saved the credential (Client ID / Secret) but haven't authorised WarpFlow to access your Google account yet. Click "Re-connect Google" below to complete the OAuth step.
                                </p>
                                <button
                                    type="button"
                                    onClick={handleConnectGoogle}
                                    className="flex items-center gap-1.5 text-orange-300 hover:text-orange-200 font-medium transition-colors font-sans"
                                >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                    Re-connect Google Account
                                </button>
                            </div>
                        );
                    }

                    return (
                        <div className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-40 ${testResult.ok
                            ? 'bg-green-500/10 border-green-500/30 text-green-300'
                            : 'bg-red-500/10 border-red-500/30 text-red-300'
                            }`}>
                            <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                                {testResult.ok
                                    ? <><CheckCircle2 className="w-3.5 h-3.5" /> Success</>
                                    : <><AlertCircle className="w-3.5 h-3.5" /> Error</>}
                            </div>
                            {JSON.stringify(testResult.data, null, 2)}
                        </div>
                    );
                })()}

                <button
                    type="button"
                    onClick={() => onSave({ credentialId, operation, params: params as Record<string, unknown> })}
                    disabled={!isDeleteReady}
                    className="w-full py-3 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-600 hover:from-blue-600 hover:via-indigo-600 hover:to-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default GoogleDocsConfig;
