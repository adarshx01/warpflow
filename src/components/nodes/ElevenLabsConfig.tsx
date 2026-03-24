import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Key, ShieldCheck, RotateCcw, Play, Volume2 } from 'lucide-react';
import { checkSecretExists, setSecret, deleteSecret } from '../../lib/secrets';
import { api } from '../../lib/api';

type Operation = 'text_to_speech' | 'list_voices' | 'get_voice';

interface Voice {
    voice_id: string;
    name: string;
    category?: string;
}

interface ElevenLabsConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'text_to_speech', label: 'Text to Speech', description: 'Convert text to natural-sounding speech' },
    { value: 'list_voices', label: 'List Voices', description: 'Get all available voices' },
    { value: 'get_voice', label: 'Get Voice', description: 'Get details of a specific voice' },
];

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const TextToSpeechForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => {
    const [voices, setVoices] = useState<Voice[]>([]);
    const [loadingVoices, setLoadingVoices] = useState(false);

    useEffect(() => {
        (async () => {
            setLoadingVoices(true);
            try {
                const result = await api<{ voices: Voice[] }>('/api/elevenlabs/voices', { method: 'GET' });
                setVoices(result.voices || []);
                if (!params.voice_id && result.voices && result.voices.length > 0) {
                    onChange({ ...params, voice_id: result.voices[0].voice_id });
                }
            } catch (err) {
                console.error('Failed to load voices:', err);
            } finally {
                setLoadingVoices(false);
            }
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="space-y-4">
            <Field label="Text" hint="Text to convert to speech">
                <textarea
                    className={`${inputClass} resize-none h-32`}
                    placeholder="Enter the text you want to convert to speech..."
                    value={(params.text as string) ?? ''}
                    onChange={(e) => onChange({ ...params, text: e.target.value })}
                    maxLength={5000}
                />
            </Field>
            <Field label="Voice">
                <div className="relative">
                    <select
                        value={(params.voice_id as string) ?? ''}
                        onChange={(e) => onChange({ ...params, voice_id: e.target.value })}
                        className={`${inputClass} appearance-none pr-8`}
                        disabled={loadingVoices}
                    >
                        {loadingVoices && <option value="">Loading voices...</option>}
                        {!loadingVoices && voices.length === 0 && <option value="">No voices available</option>}
                        {voices.map((v) => (
                            <option key={v.voice_id} value={v.voice_id}>
                                {v.name} {v.category ? `(${v.category})` : ''}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
            </Field>
            <Field label="Model ID" hint="Optional. Default: eleven_multilingual_v2">
                <input
                    type="text"
                    className={inputClass}
                    placeholder="eleven_multilingual_v2"
                    value={(params.model_id as string) ?? ''}
                    onChange={(e) => onChange({ ...params, model_id: e.target.value })}
                />
            </Field>
            <Field label="Stability" hint="0.0 - 1.0. Higher = more consistent">
                <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={(params.stability as number) ?? 0.5}
                    onChange={(e) => onChange({ ...params, stability: parseFloat(e.target.value) })}
                    className="w-full"
                />
                <div className="text-xs text-slate-400 text-center">{(params.stability as number) ?? 0.5}</div>
            </Field>
            <Field label="Similarity Boost" hint="0.0 - 1.0. Higher = closer to original voice">
                <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={(params.similarity_boost as number) ?? 0.5}
                    onChange={(e) => onChange({ ...params, similarity_boost: parseFloat(e.target.value) })}
                    className="w-full"
                />
                <div className="text-xs text-slate-400 text-center">{(params.similarity_boost as number) ?? 0.5}</div>
            </Field>
        </div>
    );
};

const GetVoiceForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void }> = ({ params, onChange }) => (
    <div className="space-y-4">
        <Field label="Voice ID">
            <input type="text" className={inputClass} placeholder="Voice ID" value={(params.voice_id as string) ?? ''} onChange={(e) => onChange({ ...params, voice_id: e.target.value })} />
        </Field>
    </div>
);

const ElevenLabsConfig: React.FC<ElevenLabsConfigProps> = ({ initialData, onSave }) => {
    const [apiKeyExists, setApiKeyExists] = useState(false);
    const [newApiKey, setNewApiKey] = useState('');
    const [enteringKey, setEnteringKey] = useState(false);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'text_to_speech');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? { stability: 0.5, similarity_boost: 0.5 });
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            const exists = await checkSecretExists('elevenlabs_api_key');
            setApiKeyExists(exists);
            if (!exists) setEnteringKey(true);
        })();
    }, []);

    const handleSaveKey = async () => {
        if (!newApiKey.trim()) return;
        setSaving(true);
        setStatus(null);
        try {
            await setSecret('elevenlabs_api_key', newApiKey.trim());
            setApiKeyExists(true);
            setEnteringKey(false);
            setNewApiKey('');
            setStatus({ ok: true, message: 'ElevenLabs API key saved securely.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to save API key' });
        } finally {
            setSaving(false);
        }
    };

    const handleResetKey = async () => {
        setSaving(true);
        setStatus(null);
        try {
            await deleteSecret('elevenlabs_api_key');
            setApiKeyExists(false);
            setEnteringKey(true);
            setNewApiKey('');
            setStatus({ ok: true, message: 'API key removed. Enter a new key below.' });
        } catch (err) {
            setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to remove API key' });
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const result = await api<unknown>('/api/elevenlabs/execute', { method: 'POST', body: { operation, params } });
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

    return (
        <div className="space-y-6">
            {/* API Key Section */}
            <section className="space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">ElevenLabs API Key</h3>

                {apiKeyExists && !enteringKey ? (
                    <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                        <div className="flex items-center gap-2 text-emerald-300 text-sm">
                            <ShieldCheck className="w-4 h-4" />
                            <span>ElevenLabs API key is saved securely</span>
                        </div>
                        <button
                            type="button"
                            onClick={handleResetKey}
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
                            Get your API key from <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer" className="text-indigo-400 underline">ElevenLabs Settings</a>
                        </div>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9`}
                                placeholder="Paste your ElevenLabs API key"
                                value={newApiKey}
                                onChange={(e) => setNewApiKey(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={handleSaveKey}
                                disabled={saving || !newApiKey.trim()}
                                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                            >
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                                Save API Key
                            </button>
                            {apiKeyExists && (
                                <button
                                    type="button"
                                    onClick={() => { setEnteringKey(false); setNewApiKey(''); }}
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
                    <div className="w-1 h-4 bg-gradient-to-b from-indigo-400 to-purple-500 rounded-full" />Operation
                </h3>
                <div className="relative">
                    <select value={operation} onChange={(e) => { const newOp = e.target.value as Operation; setOperation(newOp); setParams(newOp === 'text_to_speech' ? { stability: 0.5, similarity_boost: 0.5 } : {}); setTestResult(null); }} className={`${inputClass} appearance-none pr-8`}>
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
                    <div className="w-1 h-4 bg-gradient-to-b from-indigo-400 to-purple-500 rounded-full" />Parameters
                </h3>
                {operation === 'text_to_speech' && <TextToSpeechForm params={params} onChange={setParams} />}
                {operation === 'list_voices' && <p className="text-sm text-slate-400">No parameters needed. This will list all available voices.</p>}
                {operation === 'get_voice' && <GetVoiceForm params={params} onChange={setParams} />}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Test & Save */}
            <section className="space-y-3">
                <button type="button" onClick={handleTest} disabled={testing || !apiKeyExists}
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
                    className="w-full py-3 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <Volume2 className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default ElevenLabsConfig;
