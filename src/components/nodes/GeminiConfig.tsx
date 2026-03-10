import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Key, Eye, EyeOff } from 'lucide-react';
import { api } from '../../lib/api';

type Operation = 'generate_content' | 'chat';

interface ModelInfo { id: string; name: string; description: string; }

interface GeminiConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const OPERATIONS: { value: Operation; label: string; description: string }[] = [
    { value: 'generate_content', label: 'Generate Content', description: 'Generate text from a single prompt' },
    { value: 'chat', label: 'Chat', description: 'Multi-turn conversation with Gemini' },
];

const FALLBACK_MODELS = ['gemini-2.5-flash', 'gemini-3-flash-preview', 'gemini-3.1-pro-preview', 'gemini-3.1-flash-lite-preview'];

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const GenerateContentForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void; models: string[] }> = ({ params, onChange, models }) => (
    <div className="space-y-4">
        <Field label="Model">
            <div className="relative">
                <select value={(params.model as string) ?? 'gemini-2.5-flash'} onChange={(e) => onChange({ ...params, model: e.target.value })} className={`${inputClass} appearance-none pr-8`}>
                    {models.map((m) => (<option key={m} value={m}>{m}</option>))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>
        <Field label="Prompt">
            <textarea className={`${inputClass} resize-none h-32`} placeholder="Enter your prompt..." value={(params.prompt as string) ?? ''} onChange={(e) => onChange({ ...params, prompt: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
            <Field label="Temperature" hint="0-2. Higher = more creative.">
                <input type="number" className={inputClass} min={0} max={2} step={0.1} placeholder="0.7" value={(params.temperature as number) ?? 0.7} onChange={(e) => onChange({ ...params, temperature: parseFloat(e.target.value) || 0.7 })} />
            </Field>
            <Field label="Max Tokens" hint="Max response length.">
                <input type="number" className={inputClass} min={1} max={65536} placeholder="1024" value={(params.maxTokens as number) ?? 1024} onChange={(e) => onChange({ ...params, maxTokens: parseInt(e.target.value, 10) || 1024 })} />
            </Field>
        </div>
    </div>
);

const ChatForm: React.FC<{ params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void; models: string[] }> = ({ params, onChange, models }) => (
    <div className="space-y-4">
        <Field label="Model">
            <div className="relative">
                <select value={(params.model as string) ?? 'gemini-2.5-flash'} onChange={(e) => onChange({ ...params, model: e.target.value })} className={`${inputClass} appearance-none pr-8`}>
                    {models.map((m) => (<option key={m} value={m}>{m}</option>))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
        </Field>
        <Field label="Messages" hint='JSON array of messages. e.g. [{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi!"},{"role":"user","content":"How are you?"}]'>
            <textarea className={`${inputClass} resize-none h-36 font-mono text-xs`} placeholder='[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi there!"},{"role":"user","content":"Tell me a joke"}]'
                value={(params.messages as string) ?? ''} onChange={(e) => onChange({ ...params, messages: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
            <Field label="Temperature" hint="0-2.">
                <input type="number" className={inputClass} min={0} max={2} step={0.1} placeholder="0.7" value={(params.temperature as number) ?? 0.7} onChange={(e) => onChange({ ...params, temperature: parseFloat(e.target.value) || 0.7 })} />
            </Field>
            <Field label="Max Tokens">
                <input type="number" className={inputClass} min={1} max={65536} placeholder="1024" value={(params.maxTokens as number) ?? 1024} onChange={(e) => onChange({ ...params, maxTokens: parseInt(e.target.value, 10) || 1024 })} />
            </Field>
        </div>
    </div>
);

const GeminiConfig: React.FC<GeminiConfigProps> = ({ initialData, onSave }) => {
    const [apiKey, setApiKey] = useState((initialData.apiKey as string) ?? '');
    const [showKey, setShowKey] = useState(false);
    const [operation, setOperation] = useState<Operation>((initialData.operation as Operation) ?? 'generate_content');
    const [params, setParams] = useState<Record<string, unknown>>((initialData.params as Record<string, unknown>) ?? {});
    const [testResult, setTestResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [testing, setTesting] = useState(false);
    const [models, setModels] = useState<string[]>(FALLBACK_MODELS);

    useEffect(() => {
        api<ModelInfo[]>('/api/gemini/models')
            .then((data) => setModels(data.map((m) => m.id)))
            .catch(() => { /* use fallback */ });
    }, []);

    const handleTest = async () => {
        if (!apiKey) return;
        setTesting(true); setTestResult(null);
        try {
            const body: Record<string, unknown> = { apiKey, operation, params: { ...params } };
            if (params.messages && typeof params.messages === 'string') {
                try { body.params = { ...params, messages: JSON.parse(params.messages as string) }; } catch { /* send as-is */ }
            }
            const result = await api<unknown>('/api/gemini/execute', { method: 'POST', body });
            setTestResult({ ok: true, data: result });
        } catch (err) { setTestResult({ ok: false, data: { error: (err as Error).message } }); } finally { setTesting(false); }
    };

    const currentOp = OPERATIONS.find((o) => o.value === operation)!;

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-violet-500 rounded-full" />API Key
                </h3>
                <div className="space-y-3">
                    <div className="relative">
                        <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input type={showKey ? 'text' : 'password'} className={`${inputClass} pl-9 pr-10`} placeholder="AIza..." value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
                        <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                    <p className="text-xs text-slate-500">Get your API key from <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" className="text-blue-400 underline">Google AI Studio</a>. Your key is sent directly and never stored on the server.</p>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-violet-500 rounded-full" />Operation
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
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-violet-500 rounded-full" />Parameters
                </h3>
                {operation === 'generate_content' && <GenerateContentForm params={params} onChange={setParams} models={models} />}
                {operation === 'chat' && <ChatForm params={params} onChange={setParams} models={models} />}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section className="space-y-3">
                <button type="button" onClick={handleTest} disabled={testing || !apiKey}
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
                    if (saveParams.messages && typeof saveParams.messages === 'string') {
                        try { saveParams.messages = JSON.parse(saveParams.messages as string); } catch { /* keep string */ }
                    }
                    onSave({ apiKey, operation, params: saveParams });
                }}
                    className="w-full py-3 bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 hover:from-blue-600 hover:via-violet-600 hover:to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />Save Configuration
                </button>
            </section>
        </div>
    );
};

export default GeminiConfig;
