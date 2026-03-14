import React, { useState, useEffect } from 'react';
import { X, Play, Loader2, CheckCircle2, AlertCircle, ChevronDown, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api } from '../lib/api';
import { checkSecretExists, type SecretKey } from '../lib/secrets';

interface Node {
    id: string;
    type: string;
    name: string;
    icon: string;
    color: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
}

interface Connection {
    id: string;
    from: string;
    to: string;
}

interface StepResult {
    tool: string;
    params: Record<string, unknown>;
    result?: unknown;
    error?: string;
}

interface ExecuteResult {
    status: string;
    summary: string;
    steps: StepResult[];
}

interface ExecuteModalProps {
    nodes: Node[];
    connections: Connection[];
    onClose: () => void;
}

interface ModelInfo { id: string; name: string; description: string }

const inputClass = 'w-full bg-slate-800/80 border border-slate-600/50 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all placeholder:text-slate-500';

const ExecuteModal: React.FC<ExecuteModalProps> = ({ nodes, connections, onClose }) => {
    const agentNode = nodes.find((n) => n.type === 'ai-agent');
    const configuredProvider = (agentNode?.data.aiProvider as 'gemini' | 'openai' | undefined) ?? 'gemini';
    const configuredModel = (agentNode?.data.aiModel as string | undefined) ?? '';

    const [prompt, setPrompt] = useState('');
    const [aiProvider, setAiProvider] = useState<'gemini' | 'openai'>(configuredProvider);
    const [model, setModel] = useState(configuredModel);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [keyExists, setKeyExists] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [result, setResult] = useState<ExecuteResult | null>(null);
    const [error, setError] = useState('');

    const secretKeyForProvider = (provider: 'gemini' | 'openai'): SecretKey =>
        provider === 'openai' ? 'agent_openai_api_key' : 'agent_gemini_api_key';

    // Fetch models and check API key existence when provider changes
    useEffect(() => {
        checkSecretExists(secretKeyForProvider(aiProvider)).then(setKeyExists);
    }, [aiProvider]);

    useEffect(() => {
        setModels([]);
        api<ModelInfo[]>(`/api/${aiProvider}/models`)
            .then((data) => {
                setModels(data);
                setModel((prev) => {
                    if (configuredModel && data.some((m) => m.id === configuredModel)) {
                        return configuredModel;
                    }
                    if (prev && data.some((m) => m.id === prev)) {
                        return prev;
                    }
                    return data[0]?.id ?? '';
                });
            })
            .catch(() => { /* fallback handled by empty list */ });
    }, [aiProvider, configuredModel]);

    // Check if there's an AI agent node
    const hasAgentNode = Boolean(agentNode);
    const serviceNodes = nodes.filter(n =>
        ['google-docs', 'google-drive', 'gmail', 'google-sheets', 'google-forms'].includes(n.type)
    );

    const handleExecute = async () => {
        if (!prompt.trim()) return;

        setExecuting(true);
        setError('');
        setResult(null);

        try {
            // API key is fetched internally by the backend from the encrypted secrets store
            const res = await api<ExecuteResult>('/api/agent/execute', {
                method: 'POST',
                body: {
                    nodes: nodes.map(n => ({ id: n.id, type: n.type, name: n.name, data: n.data })),
                    connections: connections.map(c => ({ id: c.id, from: c.from, to: c.to })),
                    prompt,
                    ai_provider: aiProvider,
                    ai_model: model || undefined,
                },
            });
            setResult(res);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Execution failed');
        } finally {
            setExecuting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
            <div className="relative w-full max-w-2xl max-h-[90vh] bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-400 via-fuchsia-400 to-pink-500 flex items-center justify-center text-xl">
                            👾
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-100">Execute Workflow</h2>
                            <p className="text-xs text-slate-400">AI Agent will orchestrate connected services</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 space-y-5">
                    {/* Validation Warnings */}
                    {!hasAgentNode && (
                        <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                            <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
                            <div>
                                <p className="text-sm font-medium text-amber-300">No AI Agent node found</p>
                                <p className="text-xs text-amber-400/80 mt-1">Add an AI Agent node and connect it to service nodes to enable execution.</p>
                            </div>
                        </div>
                    )}

                    {hasAgentNode && serviceNodes.length === 0 && (
                        <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                            <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
                            <div>
                                <p className="text-sm font-medium text-amber-300">No service nodes connected</p>
                                <p className="text-xs text-amber-400/80 mt-1">Connect Google Docs, Gmail, Drive, Sheets, or Forms nodes to the AI Agent.</p>
                            </div>
                        </div>
                    )}

                    {/* Connected Services Summary */}
                    {serviceNodes.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-slate-400">Available tools:</span>
                            {serviceNodes.map(n => (
                                <span key={n.id} className="px-2.5 py-1 bg-slate-700/50 rounded-lg text-xs text-slate-300 flex items-center gap-1.5">
                                    <span>{n.icon}</span> {n.name}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Prompt */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Prompt</label>
                        <textarea
                            className={`${inputClass} resize-none h-28`}
                            placeholder="Describe what you want the AI agent to do... e.g. 'Create a document titled Meeting Notes with today's agenda and email a summary to team@example.com'"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                        />
                    </div>

                    {/* API Key Status */}
                    {hasAgentNode && (
                        <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border text-sm ${
                            keyExists
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                                : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                        }`}>
                            {keyExists
                                ? <ShieldCheck className="w-4 h-4 shrink-0" />
                                : <ShieldAlert className="w-4 h-4 shrink-0" />}
                            <span>
                                {keyExists
                                    ? `${aiProvider === 'gemini' ? 'Gemini' : 'OpenAI'} API key is configured. The backend will use it securely.`
                                    : 'No API key found. Open the AI Agent node → Configure and save your API key first.'}
                            </span>
                        </div>
                    )}

                    {/* AI Provider & Model */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">AI Provider</label>
                            <div className="relative">
                                <select
                                    value={aiProvider}
                                    onChange={(e) => setAiProvider(e.target.value as 'gemini' | 'openai')}
                                    className={`${inputClass} appearance-none pr-8`}
                                >
                                    <option value="gemini">Google Gemini</option>
                                    <option value="openai">OpenAI (GPT)</option>
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Model</label>
                            <div className="relative">
                                <select
                                    value={model}
                                    onChange={(e) => setModel(e.target.value)}
                                    className={`${inputClass} appearance-none pr-8`}
                                >
                                    {models.map((m) => (
                                        <option key={m.id} value={m.id}>{m.name}</option>
                                    ))}
                                    {models.length === 0 && <option value="">Loading models...</option>}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
                            <p className="text-sm text-red-300">{error}</p>
                        </div>
                    )}

                    {/* Results */}
                    {result && (
                        <div className="space-y-4">
                            <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                                <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
                                <div>
                                    <p className="text-sm font-medium text-emerald-300">Execution {result.status}</p>
                                    <p className="text-sm text-slate-300 mt-2 whitespace-pre-wrap">{result.summary}</p>
                                </div>
                            </div>

                            {result.steps.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-slate-300 mb-2">Execution Steps</h3>
                                    <div className="space-y-2">
                                        {result.steps.map((step, i) => (
                                            <div key={i} className={`p-3 rounded-xl border text-sm ${step.error ? 'bg-red-500/5 border-red-500/20' : 'bg-slate-800/50 border-slate-700/30'}`}>
                                                <div className="flex items-center gap-2 mb-1">
                                                    {step.error ? (
                                                        <AlertCircle className="w-4 h-4 text-red-400" />
                                                    ) : (
                                                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                                    )}
                                                    <span className="font-mono text-xs text-cyan-400">{step.tool}</span>
                                                </div>
                                                {step.error && (
                                                    <p className="text-xs text-red-300 mt-1">{step.error}</p>
                                                )}
                                                {step.result && (
                                                    <pre className="text-xs text-slate-400 mt-1 overflow-x-auto max-h-24 overflow-y-auto">
                                                        {JSON.stringify(step.result, null, 2)}
                                                    </pre>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-700/50 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition-colors"
                    >
                        {result ? 'Close' : 'Cancel'}
                    </button>
                    {!result && (
                        <button
                            onClick={handleExecute}
                            disabled={executing || !prompt.trim() || !hasAgentNode || !keyExists}
                            className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600 text-white rounded-xl text-sm font-semibold flex items-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/25"
                        >
                            {executing ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Executing...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4" fill="currentColor" />
                                    Execute
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ExecuteModal;
