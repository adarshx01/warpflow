import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Key, ShieldCheck, RotateCcw, Play, Database } from 'lucide-react';
import { checkSecretExists, setSecret, deleteSecret } from '../../lib/secrets';
import { api } from '../../lib/api';

type Operation = 'query' | 'insert' | 'update' | 'delete' | 'select';

interface PostgreSQLConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'query', label: 'Execute Query', description: 'Execute a raw SQL query (SELECT, INSERT, UPDATE, DELETE)' },
    { value: 'select', label: 'Select Rows', description: 'Select rows from a table with optional conditions' },
    { value: 'insert', label: 'Insert Row', description: 'Insert a new row into a table' },
    { value: 'update', label: 'Update Rows', description: 'Update rows in a table matching conditions' },
    { value: 'delete', label: 'Delete Rows', description: 'Delete rows from a table matching conditions' },
];

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const QueryForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="SQL Query">
            <textarea
                className={`${inputClass} resize-none h-32 font-mono text-xs`}
                placeholder="SELECT * FROM users WHERE email = $1"
                value={(params.query as string) ?? ''}
                onChange={(e) => onChange({ ...params, query: e.target.value })}
            />
        </Field>
        <Field label="Parameters (JSON Array)" hint='Optional. e.g., ["user@example.com", 123]'>
            <textarea
                className={`${inputClass} resize-none h-20 font-mono text-xs`}
                placeholder='["user@example.com"]'
                value={(params.params as string) ?? ''}
                onChange={(e) => onChange({ ...params, params: e.target.value })}
            />
        </Field>
    </div>
);

const SelectForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Table Name">
            <input type="text" className={inputClass} placeholder="users" value={(params.table as string) ?? ''} onChange={(e) => onChange({ ...params, table: e.target.value })} />
        </Field>
        <Field label="Columns" hint='Comma-separated or "*" for all'>
            <input type="text" className={inputClass} placeholder="id, name, email" value={(params.columns as string) ?? '*'} onChange={(e) => onChange({ ...params, columns: e.target.value })} />
        </Field>
        <Field label="WHERE Clause" hint='Optional. e.g., "age > 18"'>
            <input type="text" className={inputClass} placeholder='age > 18' value={(params.where as string) ?? ''} onChange={(e) => onChange({ ...params, where: e.target.value })} />
        </Field>
        <Field label="LIMIT" hint="Optional. Max rows to return">
            <input type="number" className={inputClass} placeholder="100" min={1} value={(params.limit as number) ?? ''} onChange={(e) => onChange({ ...params, limit: parseInt(e.target.value, 10) || undefined })} />
        </Field>
    </div>
);

const InsertForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Table Name">
            <input type="text" className={inputClass} placeholder="users" value={(params.table as string) ?? ''} onChange={(e) => onChange({ ...params, table: e.target.value })} />
        </Field>
        <Field label="Data (JSON Object)" hint='e.g., {"name": "John", "email": "john@example.com"}'>
            <textarea
                className={`${inputClass} resize-none h-28 font-mono text-xs`}
                placeholder='{"name": "John", "email": "john@example.com"}'
                value={(params.data as string) ?? ''}
                onChange={(e) => onChange({ ...params, data: e.target.value })}
            />
        </Field>
    </div>
);

const UpdateForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Table Name">
            <input type="text" className={inputClass} placeholder="users" value={(params.table as string) ?? ''} onChange={(e) => onChange({ ...params, table: e.target.value })} />
        </Field>
        <Field label="Data (JSON Object)" hint='Fields to update, e.g., {"name": "Jane"}'>
            <textarea
                className={`${inputClass} resize-none h-24 font-mono text-xs`}
                placeholder='{"name": "Jane"}'
                value={(params.data as string) ?? ''}
                onChange={(e) => onChange({ ...params, data: e.target.value })}
            />
        </Field>
        <Field label="WHERE Clause" hint='e.g., "id = 123"'>
            <input type="text" className={inputClass} placeholder='id = 123' value={(params.where as string) ?? ''} onChange={(e) => onChange({ ...params, where: e.target.value })} />
        </Field>
    </div>
);

const DeleteForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Table Name">
            <input type="text" className={inputClass} placeholder="users" value={(params.table as string) ?? ''} onChange={(e) => onChange({ ...params, table: e.target.value })} />
        </Field>
        <Field label="WHERE Clause" hint='REQUIRED for safety, e.g., "id = 123"'>
            <input type="text" className={inputClass} placeholder='id = 123' value={(params.where as string) ?? ''} onChange={(e) => onChange({ ...params, where: e.target.value })} />
        </Field>
    </div>
);

const PostgreSQLConfig: React.FC<PostgreSQLConfigProps> = ({ initialData, onSave }) => {
    const [connectionStringExists, setConnectionStringExists] = useState(false);
    const [newConnectionString, setNewConnectionString] = useState('');
    const [enteringConnection, setEnteringConnection] = useState(false);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'select');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? { columns: '*' });
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            const exists = await checkSecretExists('postgresql_connection_string');
            setConnectionStringExists(exists);
            if (!exists) setEnteringConnection(true);
        })();
    }, []);

    const handleSaveConnection = async () => {
        if (!newConnectionString.trim()) return;
        setSaving(true);
        setStatus(null);
        try {
            await setSecret('postgresql_connection_string', newConnectionString.trim());
            setConnectionStringExists(true);
            setEnteringConnection(false);
            setNewConnectionString('');
            setStatus({ ok: true, message: 'PostgreSQL connection saved securely.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to save connection' });
        } finally {
            setSaving(false);
        }
    };

    const handleResetConnection = async () => {
        setSaving(true);
        setStatus(null);
        try {
            await deleteSecret('postgresql_connection_string');
            setConnectionStringExists(false);
            setEnteringConnection(true);
            setNewConnectionString('');
            setStatus({ ok: true, message: 'Connection removed. Enter a new connection string below.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to remove connection' });
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const body: Record<string, unknown> = { operation, params: { ...params } };

            // Parse JSON fields
            if (params.params && typeof params.params === 'string') {
                try { body.params = { ...params, params: JSON.parse(params.params as string) }; } catch { /* send as-is */ }
            }
            if (params.data && typeof params.data === 'string') {
                try { body.params = { ...params, data: JSON.parse(params.data as string) }; } catch { /* send as-is */ }
            }

            const result = await api<unknown>('/api/postgresql/execute', { method: 'POST', body });
            setTestResult({ ok: true, data: result });
        } catch (err) {
            setTestResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTesting(false);
        }
    };

    const handleSaveConfig = () => {
        const saveParams = { ...params };

        // Parse JSON fields for saving
        if (saveParams.params && typeof saveParams.params === 'string') {
            try { saveParams.params = JSON.parse(saveParams.params as string); } catch { /* keep string */ }
        }
        if (saveParams.data && typeof saveParams.data === 'string') {
            try { saveParams.data = JSON.parse(saveParams.data as string); } catch { /* keep string */ }
        }

        onSave({ operation, params: saveParams });
        setStatus({ ok: true, message: 'Configuration saved.' });
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;

    return (
        <div className="space-y-6">
            {/* Connection String Section */}
            <section className="space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">PostgreSQL Connection</h3>

                {connectionStringExists && !enteringConnection ? (
                    <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                        <div className="flex items-center gap-2 text-emerald-300 text-sm">
                            <ShieldCheck className="w-4 h-4" />
                            <span>PostgreSQL connection is saved securely</span>
                        </div>
                        <button
                            type="button"
                            onClick={handleResetConnection}
                            disabled={saving}
                            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-500/10"
                        >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Reset
                        </button>
                    </div>
                ) : (
                    <div className="space-y-2">
                        <div className="text-xs text-slate-400 mb-2">
                            Format: <span className="font-mono text-blue-400">postgresql://user:password@host:port/database</span>
                        </div>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9 font-mono text-xs`}
                                placeholder="postgresql://user:password@localhost:5432/mydb"
                                value={newConnectionString}
                                onChange={(e) => setNewConnectionString(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={handleSaveConnection}
                                disabled={saving || !newConnectionString.trim()}
                                className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                            >
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                                Save Connection
                            </button>
                            {connectionStringExists && (
                                <button
                                    type="button"
                                    onClick={() => { setEnteringConnection(false); setNewConnectionString(''); }}
                                    className="px-3 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors rounded-xl hover:bg-slate-700/40"
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Operation Selection */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />Operation
                </h3>
                <div className="relative">
                    <select value={operation} onChange={(e) => { setOperation(e.target.value as Operation); setParams(e.target.value === 'select' ? { columns: '*' } : {}); setTestResult(null); }} className={`${inputClass} appearance-none pr-8`}>
                        {OPERATIONS.map((op) => (<option key={op.value} value={op.value}>{op.label}</option>))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
                <p className="text-xs text-slate-500 mt-2">{currentOp.description}</p>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Parameters */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />Parameters
                </h3>
                {operation === 'query' && <QueryForm params={params} onChange={setParams} />}
                {operation === 'select' && <SelectForm params={params} onChange={setParams} />}
                {operation === 'insert' && <InsertForm params={params} onChange={setParams} />}
                {operation === 'update' && <UpdateForm params={params} onChange={setParams} />}
                {operation === 'delete' && <DeleteForm params={params} onChange={setParams} />}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Test & Save */}
            <section className="space-y-3">
                <button type="button" onClick={handleTest} disabled={testing || !connectionStringExists}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 disabled:opacity-40 text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
                    {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}{testing ? 'Testing...' : 'Test Operation'}
                </button>
                {testResult && (
                    <div className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-40 ${testResult.ok ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {testResult.ok ? <><CheckCircle2 className="w-3.5 h-3.5" /> Success</> : <><AlertCircle className="w-3.5 h-3.5" /> Error</>}
                        </div>
                        {JSON.stringify(testResult.data, null, 2)}
                    </div>
                )}
                {status && (
                    <div className={`p-3 rounded-xl border text-sm flex items-center gap-2 ${status.ok ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
                        {status.ok ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                        {status.message}
                    </div>
                )}
                <button type="button" onClick={handleSaveConfig}
                    className="w-full py-3 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-600 hover:from-blue-600 hover:via-indigo-600 hover:to-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <Database className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default PostgreSQLConfig;
