import React, { useState, useEffect } from 'react';
import { Plus, ChevronDown, ExternalLink, CheckCircle2, AlertCircle, Loader2, Play } from 'lucide-react';
import { api } from '../../lib/api';

type Operation = 'create' | 'get' | 'read_values' | 'write_values' | 'append_values' | 'clear_values';

interface Credential { id: string; name: string; type: string; }

interface GoogleSheetsConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'create', label: 'Create Spreadsheet', description: 'Create a new Google Spreadsheet' },
    { value: 'get', label: 'Get Spreadsheet', description: 'Get spreadsheet metadata and sheets' },
    { value: 'read_values', label: 'Read Values', description: 'Read cell values from a range' },
    { value: 'write_values', label: 'Write Values', description: 'Write values to a range' },
    { value: 'append_values', label: 'Append Values', description: 'Append rows to a sheet' },
    { value: 'clear_values', label: 'Clear Values', description: 'Clear cell values in a range' },
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

const CreateForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet Title">
            <input type="text" className={inputClass} placeholder="My Spreadsheet" value={(params.title as string) ?? ''} onChange={(e) => onChange({ ...params, title: e.target.value })} />
        </Field>
        <Field label="Sheet Names" hint="Comma-separated. Default: Sheet1">
            <input type="text" className={inputClass} placeholder="Sheet1, Sheet2, Data" value={(params.sheets as string) ?? ''} onChange={(e) => onChange({ ...params, sheets: e.target.value })} />
        </Field>
    </div>
);

const GetForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet ID">
            <input type="text" className={inputClass} placeholder="Spreadsheet ID" value={(params.spreadsheetId as string) ?? ''} onChange={(e) => onChange({ ...params, spreadsheetId: e.target.value })} />
        </Field>
    </div>
);

const ReadValuesForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet ID">
            <input type="text" className={inputClass} placeholder="Spreadsheet ID" value={(params.spreadsheetId as string) ?? ''} onChange={(e) => onChange({ ...params, spreadsheetId: e.target.value })} />
        </Field>
        <Field label="Range" hint="e.g. Sheet1!A1:D10 or Sheet1!A:A">
            <input type="text" className={inputClass} placeholder="Sheet1!A1:D10" value={(params.range as string) ?? ''} onChange={(e) => onChange({ ...params, range: e.target.value })} />
        </Field>
    </div>
);

const WriteValuesForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet ID">
            <input type="text" className={inputClass} placeholder="Spreadsheet ID" value={(params.spreadsheetId as string) ?? ''} onChange={(e) => onChange({ ...params, spreadsheetId: e.target.value })} />
        </Field>
        <Field label="Range" hint="e.g. Sheet1!A1:C3">
            <input type="text" className={inputClass} placeholder="Sheet1!A1:C3" value={(params.range as string) ?? ''} onChange={(e) => onChange({ ...params, range: e.target.value })} />
        </Field>
        <Field label="Values" hint='JSON array of rows. e.g. [["Name","Age"],["Alice","30"]]'>
            <textarea className={`${inputClass} resize-none h-28 font-mono text-xs`} placeholder='[["Name", "Age"], ["Alice", "30"]]' value={(params.values as string) ?? ''} onChange={(e) => onChange({ ...params, values: e.target.value })} />
        </Field>
    </div>
);

const AppendValuesForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet ID">
            <input type="text" className={inputClass} placeholder="Spreadsheet ID" value={(params.spreadsheetId as string) ?? ''} onChange={(e) => onChange({ ...params, spreadsheetId: e.target.value })} />
        </Field>
        <Field label="Range" hint="e.g. Sheet1!A:C">
            <input type="text" className={inputClass} placeholder="Sheet1!A:C" value={(params.range as string) ?? ''} onChange={(e) => onChange({ ...params, range: e.target.value })} />
        </Field>
        <Field label="Values" hint='JSON array of rows to append. e.g. [["Bob","25"]]'>
            <textarea className={`${inputClass} resize-none h-28 font-mono text-xs`} placeholder='[["Bob", "25"]]' value={(params.values as string) ?? ''} onChange={(e) => onChange({ ...params, values: e.target.value })} />
        </Field>
    </div>
);

const ClearValuesForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Spreadsheet ID">
            <input type="text" className={inputClass} placeholder="Spreadsheet ID" value={(params.spreadsheetId as string) ?? ''} onChange={(e) => onChange({ ...params, spreadsheetId: e.target.value })} />
        </Field>
        <Field label="Range" hint="e.g. Sheet1!A1:D10">
            <input type="text" className={inputClass} placeholder="Sheet1!A1:D10" value={(params.range as string) ?? ''} onChange={(e) => onChange({ ...params, range: e.target.value })} />
        </Field>
    </div>
);

const GoogleSheetsConfig: React.FC<GoogleSheetsConfigProps> = ({ initialData, onSave }) => {
    const [credentials, setCredentials] = useState<Credential[]>([]);
    const [loadingCreds, setLoadingCreds] = useState(true);
    const [showNewCredForm, setShowNewCredForm] = useState(false);
    const [newCred, setNewCred] = useState({ name: '', clientId: '', clientSecret: '' });
    const [savingCred, setSavingCred] = useState(false);

    const [credentialId, setCredentialId] = useState((initialData.credentialId as string) ?? '');
    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'read_values');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? {});
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const data = await api<Credential[]>('/api/credentials?type=google-sheets', { method: 'GET' });
                setCredentials(data);
                if (data.length > 0 && !credentialId) setCredentialId(data[0].id);
            } catch { /* ignore */ } finally { setLoadingCreds(false); }
        })();
    }, []);

    const handleAddCredential = async () => {
        if (!newCred.name || !newCred.clientId || !newCred.clientSecret) return;
        setSavingCred(true);
        try {
            const created = await api<Credential>('/api/credentials', { method: 'POST', body: { type: 'google-sheets', name: newCred.name, client_id: newCred.clientId, client_secret: newCred.clientSecret } });
            setCredentials((prev) => [...prev, created]);
            setCredentialId(created.id);
            setShowNewCredForm(false);
            setNewCred({ name: '', clientId: '', clientSecret: '' });
        } catch (err) { alert(`Failed: ${(err as Error).message}`); } finally { setSavingCred(false); }
    };

    const handleConnectGoogle = () => { window.open(`http://localhost:8000/api/google-sheets/oauth/start?credential_id=${credentialId}`, '_blank'); };

    const handleTest = async () => {
        setTesting(true); setTestResult(null);
        try {
            const body: Record<string, unknown> = { credentialId, operation, params: { ...params } };
            if (params.values && typeof params.values === 'string') {
                try { body.params = { ...params, values: JSON.parse(params.values as string) }; } catch { /* send as-is */ }
            }
            const result = await api<unknown>('/api/google-sheets/execute', { method: 'POST', body });
            setTestResult({ ok: true, data: result });
        } catch (err) { setTestResult({ ok: false, data: { error: (err as Error).message } }); } finally { setTesting(false); }
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-green-400 to-teal-500 rounded-full" />Google Account
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
                                        <li>Add redirect URI: <span className="font-mono text-yellow-300 text-[11px]">http://localhost:8000/api/google-sheets/oauth/callback</span></li>
                                        <li>Enable <span className="text-white font-medium">Google Sheets API</span></li>
                                    </ol>
                                </div>
                                <div className="p-4 space-y-4 bg-slate-800/60">
                                    <div><label className={labelClass}>Nickname</label><input type="text" className={inputClass} placeholder="e.g. Work Account" value={newCred.name} onChange={(e) => setNewCred({ ...newCred, name: e.target.value })} /></div>
                                    <div><label className={labelClass}>Client ID</label><input type="text" className={inputClass} placeholder="123...apps.googleusercontent.com" value={newCred.clientId} onChange={(e) => setNewCred({ ...newCred, clientId: e.target.value })} /></div>
                                    <div><label className={labelClass}>Client Secret</label><input type="password" className={inputClass} placeholder="GOCSPX-..." value={newCred.clientSecret} onChange={(e) => setNewCred({ ...newCred, clientSecret: e.target.value })} /></div>
                                    <button type="button" onClick={handleAddCredential} disabled={savingCred || !newCred.name || !newCred.clientId || !newCred.clientSecret}
                                        className="w-full py-2.5 bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-600 hover:to-teal-600 disabled:opacity-40 text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
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
                    <div className="w-1 h-4 bg-gradient-to-b from-green-400 to-teal-500 rounded-full" />Operation
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
                    <div className="w-1 h-4 bg-gradient-to-b from-green-400 to-teal-500 rounded-full" />Parameters
                </h3>
                {operation === 'create' && <CreateForm params={params} onChange={setParams} />}
                {operation === 'get' && <GetForm params={params} onChange={setParams} />}
                {operation === 'read_values' && <ReadValuesForm params={params} onChange={setParams} />}
                {operation === 'write_values' && <WriteValuesForm params={params} onChange={setParams} />}
                {operation === 'append_values' && <AppendValuesForm params={params} onChange={setParams} />}
                {operation === 'clear_values' && <ClearValuesForm params={params} onChange={setParams} />}
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
                <button type="button" onClick={() => {
                    const saveParams = { ...params };
                    if (saveParams.values && typeof saveParams.values === 'string') {
                        try { saveParams.values = JSON.parse(saveParams.values as string); } catch { /* keep string */ }
                    }
                    onSave({ credentialId, operation, params: saveParams });
                }}
                    className="w-full py-3 bg-gradient-to-r from-green-500 via-teal-500 to-blue-500 hover:from-green-600 hover:via-teal-600 hover:to-blue-600 text-white font-bold rounded-xl shadow-lg shadow-green-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default GoogleSheetsConfig;
