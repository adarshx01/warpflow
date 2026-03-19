import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Zap, Info } from 'lucide-react';
import { api } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Model {
    id: string;
    name: string;
    algorithm: string;
    model_type: string;
    model_category: string;
    metrics: Record<string, unknown>;
    feature_names: string[];
}

interface ModelInferenceConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

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

// ─── Main Component ───────────────────────────────────────────────────────────

const ModelInferenceConfig: React.FC<ModelInferenceConfigProps> = ({ initialData, onSave }) => {
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);
    const [predicting, setPredicting] = useState(false);
    const [predictResult, setPredictResult] = useState<{ ok: boolean; data: unknown } | null>(null);

    // Form state
    const [modelId, setModelId] = useState<string>((initialData.model_id as string) || '');
    const [inputData, setInputData] = useState<string>((initialData.input_data as string) || '');
    const [inputMode, setInputMode] = useState<'json' | 'form'>('json');
    const [formValues, setFormValues] = useState<Record<string, string>>({});

    const selectedModel = models.find((m) => m.id === modelId);

    useEffect(() => {
        loadModels();
    }, []);

    useEffect(() => {
        if (selectedModel?.feature_names) {
            const initialValues: Record<string, string> = {};
            selectedModel.feature_names.forEach(f => { initialValues[f] = ''; });
            setFormValues(initialValues);
        }
    }, [selectedModel]);

    const loadModels = async () => {
        try {
            const res = await api<{ models: Model[] }>('/api/ml/models', { method: 'GET' });
            setModels(res.models || []);
        } catch {
            // API may not be available
        } finally {
            setLoading(false);
        }
    };

    const handlePredict = async () => {
        if (!modelId) {
            alert('Please select a model');
            return;
        }

        let data: unknown[];
        if (inputMode === 'json') {
            try {
                data = JSON.parse(inputData);
                if (!Array.isArray(data)) {
                    data = [data];
                }
            } catch {
                alert('Invalid JSON input');
                return;
            }
        } else {
            // Form mode - create object from form values
            const obj: Record<string, number> = {};
            for (const [key, value] of Object.entries(formValues)) {
                obj[key] = parseFloat(value) || 0;
            }
            data = [obj];
        }

        setPredicting(true);
        setPredictResult(null);

        try {
            const result = await api<unknown>(`/api/ml/models/${modelId}/predict`, {
                method: 'POST',
                body: {
                    model_id: modelId,
                    input_data: data,
                },
            });

            setPredictResult({ ok: true, data: result });
        } catch (err) {
            setPredictResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setPredicting(false);
        }
    };

    const getModelTypeColor = (type: string) => {
        switch (type) {
            case 'classification': return 'text-violet-400';
            case 'regression': return 'text-emerald-400';
            case 'clustering': return 'text-amber-400';
            case 'dimensionality_reduction': return 'text-cyan-400';
            default: return 'text-slate-400';
        }
    };

    const getModelTypeIcon = (type: string) => {
        switch (type) {
            case 'classification': return '🏷️';
            case 'regression': return '📈';
            case 'clustering': return '🔮';
            case 'dimensionality_reduction': return '📉';
            default: return '🤖';
        }
    };

    return (
        <div className="space-y-6">
            {/* ── Model Selection ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-red-400 to-orange-500 rounded-full" />
                    <Zap className="w-4 h-4" />
                    Select Model
                </h3>

                {loading ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading models...
                    </div>
                ) : (
                    <Field label="Trained Model">
                        <div className="relative">
                            <select
                                value={modelId}
                                onChange={(e) => setModelId(e.target.value)}
                                className={`${inputClass} appearance-none pr-8`}
                            >
                                <option value="">Select a model...</option>
                                {models.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {m.name} ({m.algorithm})
                                    </option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>
                )}
            </section>

            {/* ── Model Info ── */}
            {selectedModel && (
                <>
                    <div className="h-px bg-slate-700/50" />

                    <section>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <div className="w-1 h-4 bg-gradient-to-b from-red-400 to-orange-500 rounded-full" />
                            <Info className="w-4 h-4" />
                            Model Info
                        </h3>

                        <div className="bg-slate-800/40 rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-slate-500">Type</span>
                                <span className={`text-sm font-medium ${getModelTypeColor(selectedModel.model_type)}`}>
                                    {getModelTypeIcon(selectedModel.model_type)} {selectedModel.model_type}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-slate-500">Algorithm</span>
                                <span className="text-sm text-slate-300">{selectedModel.algorithm}</span>
                            </div>
                            {selectedModel.feature_names && (
                                <div>
                                    <span className="text-xs text-slate-500">Features ({selectedModel.feature_names.length})</span>
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {selectedModel.feature_names.map((f) => (
                                            <span key={f} className="px-2 py-0.5 bg-slate-700/50 text-slate-300 text-xs rounded-full">
                                                {f}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Metrics Preview */}
                            {selectedModel.metrics && Object.keys(selectedModel.metrics).length > 0 && (
                                <div>
                                    <span className="text-xs text-slate-500">Key Metrics</span>
                                    <div className="grid grid-cols-2 gap-2 mt-1">
                                        {Object.entries(selectedModel.metrics)
                                            .filter(([k]) => ['accuracy', 'f1_score', 'r2', 'silhouette_score'].includes(k))
                                            .slice(0, 4)
                                            .map(([key, value]) => (
                                                <div key={key} className="bg-slate-700/30 rounded-lg p-2 text-center">
                                                    <p className="text-lg font-bold text-orange-400">
                                                        {typeof value === 'number' ? value.toFixed(3) : value}
                                                    </p>
                                                    <p className="text-xs text-slate-500">{key}</p>
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </section>

                    <div className="h-px bg-slate-700/50" />

                    {/* ── Input Data ── */}
                    <section>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <div className="w-1 h-4 bg-gradient-to-b from-red-400 to-orange-500 rounded-full" />
                            Input Data
                        </h3>

                        {/* Input Mode Toggle */}
                        <div className="flex gap-2 mb-4">
                            <button
                                type="button"
                                onClick={() => setInputMode('json')}
                                className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-all ${
                                    inputMode === 'json'
                                        ? 'border-orange-500/60 bg-orange-500/10 text-orange-300'
                                        : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                }`}
                            >
                                JSON Input
                            </button>
                            <button
                                type="button"
                                onClick={() => setInputMode('form')}
                                className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-all ${
                                    inputMode === 'form'
                                        ? 'border-orange-500/60 bg-orange-500/10 text-orange-300'
                                        : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                }`}
                            >
                                Form Input
                            </button>
                        </div>

                        {inputMode === 'json' ? (
                            <Field label="JSON Data" hint="Array of objects with feature values">
                                <textarea
                                    className={`${inputClass} resize-none h-32 font-mono text-xs`}
                                    placeholder={`[{"${selectedModel.feature_names?.[0] || 'feature1'}": 1.5, ...}]`}
                                    value={inputData}
                                    onChange={(e) => setInputData(e.target.value)}
                                />
                            </Field>
                        ) : (
                            <div className="space-y-3 max-h-48 overflow-y-auto">
                                {selectedModel.feature_names?.map((feature) => (
                                    <div key={feature} className="flex items-center gap-3">
                                        <label className="text-xs text-slate-400 w-1/3 truncate">{feature}</label>
                                        <input
                                            type="number"
                                            step="any"
                                            value={formValues[feature] || ''}
                                            onChange={(e) => setFormValues({ ...formValues, [feature]: e.target.value })}
                                            className={`${inputClass} flex-1`}
                                            placeholder="0"
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}

            <div className="h-px bg-slate-700/50" />

            {/* ── Predict & Results ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handlePredict}
                    disabled={predicting || !modelId}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {predicting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {predicting ? 'Predicting...' : 'Run Prediction'}
                </button>

                {predictResult && (
                    <div
                        className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-48 ${
                            predictResult.ok
                                ? 'bg-green-500/10 border-green-500/30 text-green-300'
                                : 'bg-red-500/10 border-red-500/30 text-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {predictResult.ok ? (
                                <><CheckCircle2 className="w-3.5 h-3.5" /> Prediction Result</>
                            ) : (
                                <><AlertCircle className="w-3.5 h-3.5" /> Prediction Failed</>
                            )}
                        </div>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(predictResult.data, null, 2)}</pre>
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => onSave({
                        model_id: modelId,
                        input_mode: inputMode,
                        input_data: inputMode === 'json' ? inputData : JSON.stringify([formValues]),
                    })}
                    className="w-full py-3 bg-gradient-to-r from-red-500 via-orange-500 to-amber-600 hover:from-red-600 hover:via-orange-600 hover:to-amber-700 text-white font-bold rounded-xl shadow-lg shadow-orange-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default ModelInferenceConfig;
