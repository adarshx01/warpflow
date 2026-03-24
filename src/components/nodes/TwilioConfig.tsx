import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Key, ShieldCheck, RotateCcw, Play } from 'lucide-react';
import { checkSecretExists, setSecret, deleteSecret } from '../../lib/secrets';
import { api } from '../../lib/api';

type Operation = 'make_call' | 'send_sms' | 'get_call_status' | 'get_message_status';

interface TwilioConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'make_call', label: 'Make Phone Call', description: 'Initiate an outbound phone call with TwiML or webhook' },
    { value: 'send_sms', label: 'Send SMS', description: 'Send an SMS message to a phone number' },
    { value: 'get_call_status', label: 'Get Call Status', description: 'Get the status of a call by SID' },
    { value: 'get_message_status', label: 'Get Message Status', description: 'Get the status of an SMS by SID' },
];

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const MakeCallForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="To Phone Number" hint="E.164 format: +1234567890">
            <input type="tel" className={inputClass} placeholder="+1234567890" value={(params.to as string) ?? ''} onChange={(e) => onChange({ ...params, to: e.target.value })} />
        </Field>
        <Field label="From Phone Number" hint="Your Twilio number">
            <input type="tel" className={inputClass} placeholder="+1234567890" value={(params.from as string) ?? ''} onChange={(e) => onChange({ ...params, from: e.target.value })} />
        </Field>
        <Field label="TwiML or URL (Required)" hint="TwiML XML (e.g., <Response><Say>Hello</Say></Response>) or URL to TwiML endpoint">
            <textarea className={`${inputClass} resize-none h-32`} placeholder="<Response><Say>Hello! This is a test call.</Say></Response>" value={(params.twiml as string) ?? ''} onChange={(e) => onChange({ ...params, twiml: e.target.value })} />
        </Field>
        <Field label="Status Callback URL" hint="Optional webhook for call events">
            <input type="url" className={inputClass} placeholder="https://example.com/callback" value={(params.statusCallback as string) ?? ''} onChange={(e) => onChange({ ...params, statusCallback: e.target.value })} />
        </Field>
    </div>
);

const SendSMSForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="To Phone Number" hint="E.164 format: +1234567890">
            <input type="tel" className={inputClass} placeholder="+1234567890" value={(params.to as string) ?? ''} onChange={(e) => onChange({ ...params, to: e.target.value })} />
        </Field>
        <Field label="From Phone Number" hint="Your Twilio number">
            <input type="tel" className={inputClass} placeholder="+1234567890" value={(params.from as string) ?? ''} onChange={(e) => onChange({ ...params, from: e.target.value })} />
        </Field>
        <Field label="Message Body">
            <textarea className={`${inputClass} resize-none h-24`} placeholder="Your message here..." value={(params.body as string) ?? ''} onChange={(e) => onChange({ ...params, body: e.target.value })} maxLength={1600} />
        </Field>
    </div>
);

const GetStatusForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void; label: string }> = ({ params, onChange, label }) => (
    <div className="space-y-4">
        <Field label={label}>
            <input type="text" className={inputClass} placeholder="CAxxxx or SMxxxx" value={(params.sid as string) ?? ''} onChange={(e) => onChange({ ...params, sid: e.target.value })} />
        </Field>
    </div>
);

const TwilioConfig: React.FC<TwilioConfigProps> = ({ initialData, onSave }) => {
    const [accountSidExists, setAccountSidExists] = useState(false);
    const [authTokenExists, setAuthTokenExists] = useState(false);
    const [newAccountSid, setNewAccountSid] = useState('');
    const [newAuthToken, setNewAuthToken] = useState('');
    const [enteringCreds, setEnteringCreds] = useState(false);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'make_call');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? {});
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            const [sidExists, tokenExists] = await Promise.all([
                checkSecretExists('twilio_account_sid'),
                checkSecretExists('twilio_auth_token'),
            ]);
            setAccountSidExists(sidExists);
            setAuthTokenExists(tokenExists);
            if (!sidExists || !tokenExists) setEnteringCreds(true);
        })();
    }, []);

    const handleSaveCredentials = async () => {
        if (!newAccountSid.trim() || !newAuthToken.trim()) return;
        setSaving(true);
        setStatus(null);
        try {
            await Promise.all([
                setSecret('twilio_account_sid', newAccountSid.trim()),
                setSecret('twilio_auth_token', newAuthToken.trim()),
            ]);
            setAccountSidExists(true);
            setAuthTokenExists(true);
            setEnteringCreds(false);
            setNewAccountSid('');
            setNewAuthToken('');
            setStatus({ ok: true, message: 'Twilio credentials saved securely.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to save credentials' });
        } finally {
            setSaving(false);
        }
    };

    const handleResetCredentials = async () => {
        setSaving(true);
        setStatus(null);
        try {
            await Promise.all([
                deleteSecret('twilio_account_sid'),
                deleteSecret('twilio_auth_token'),
            ]);
            setAccountSidExists(false);
            setAuthTokenExists(false);
            setEnteringCreds(true);
            setNewAccountSid('');
            setNewAuthToken('');
            setStatus({ ok: true, message: 'Credentials removed. Enter new credentials below.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to remove credentials' });
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const result = await api<unknown>('/api/twilio/execute', { method: 'POST', body: { operation, params } });
            setTestResult({ ok: true, data: result });
        } catch (err) {
            setTestResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTesting(false);
        }
    };

    const handleSaveConfig = () => {
        onSave({ operation, params });
        setStatus({ ok: true, message: 'Configuration saved.' });
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;
    const credsConfigured = accountSidExists && authTokenExists;

    return (
        <div className="space-y-6">
            {/* Credentials Section */}
            <section className="space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Twilio Credentials</h3>

                {credsConfigured && !enteringCreds ? (
                    <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                        <div className="flex items-center gap-2 text-emerald-300 text-sm">
                            <ShieldCheck className="w-4 h-4" />
                            <span>Twilio credentials are saved securely</span>
                        </div>
                        <button
                            type="button"
                            onClick={handleResetCredentials}
                            disabled={saving}
                            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-500/10"
                        >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Reset
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3 p-4 border border-slate-700/50 rounded-xl bg-slate-800/40">
                        <div className="text-xs text-slate-400 mb-3">
                            Get your credentials from <a href="https://console.twilio.com/" target="_blank" rel="noreferrer" className="text-purple-400 underline">Twilio Console</a>
                        </div>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="Account SID (ACxxxx...)"
                                value={newAccountSid}
                                onChange={(e) => setNewAccountSid(e.target.value)}
                            />
                        </div>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9`}
                                placeholder="Auth Token"
                                value={newAuthToken}
                                onChange={(e) => setNewAuthToken(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={handleSaveCredentials}
                                disabled={saving || !newAccountSid.trim() || !newAuthToken.trim()}
                                className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                            >
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                                Save Credentials
                            </button>
                            {credsConfigured && (
                                <button
                                    type="button"
                                    onClick={() => { setEnteringCreds(false); setNewAccountSid(''); setNewAuthToken(''); }}
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
                    <div className="w-1 h-4 bg-gradient-to-b from-purple-400 to-pink-500 rounded-full" />Operation
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

            {/* Parameters */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-purple-400 to-pink-500 rounded-full" />Parameters
                </h3>
                {operation === 'make_call' && <MakeCallForm params={params} onChange={setParams} />}
                {operation === 'send_sms' && <SendSMSForm params={params} onChange={setParams} />}
                {operation === 'get_call_status' && <GetStatusForm params={params} onChange={setParams} label="Call SID" />}
                {operation === 'get_message_status' && <GetStatusForm params={params} onChange={setParams} label="Message SID" />}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Test & Save */}
            <section className="space-y-3">
                <button type="button" onClick={handleTest} disabled={testing || !credsConfigured}
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
                    className="w-full py-3 bg-gradient-to-r from-purple-500 via-fuchsia-500 to-pink-500 hover:from-purple-600 hover:via-fuchsia-600 hover:to-pink-600 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default TwilioConfig;
