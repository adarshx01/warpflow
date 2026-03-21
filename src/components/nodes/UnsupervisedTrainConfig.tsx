import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Shapes, Settings } from 'lucide-react';
import { api } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Dataset {
    id: string;
    name: string;
    file_type: string;
    row_count: number;
    columns: Array<{ name: string; dtype: string }>;
}

interface Model {
    id: string;
    name: string;
    algorithm: string;
    model_type: string;
    model_category: string;
    metrics: Record<string, unknown>;
}

interface UnsupervisedTrainConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CLUSTERING_ALGORITHMS = [
    { value: 'kmeans', label: 'K-Means Clustering', description: 'Groups data into k clusters' },
    { value: 'dbscan', label: 'DBSCAN', description: 'Density-based clustering' },
];

const DIMENSIONALITY_REDUCTION_ALGORITHMS = [
    { value: 'pca', label: 'PCA', description: 'Principal Component Analysis' },
];

const NORMALIZATION_OPTIONS = [
    { value: 'standard', label: 'Standard Scaler (Z-score)' },
    { value: 'minmax', label: 'Min-Max Scaler (0-1)' },
    { value: 'robust', label: 'Robust Scaler' },
    { value: 'none', label: 'No Normalization' },
];

const MISSING_VALUE_OPTIONS = [
    { value: 'zero', label: 'Replace with 0' },
    { value: 'mean', label: 'Replace with Mean' },
    { value: 'median', label: 'Replace with Median' },
    { value: 'drop', label: 'Drop Rows' },
];

// ─── Styles ───────────────────────────────────────────────────────────────────

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

const UnsupervisedTrainConfig: React.FC<UnsupervisedTrainConfigProps> = ({ initialData, onSave }) => {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [loading, setLoading] = useState(true);
    const [training, setTraining] = useState(false);
    const [trainResult, setTrainResult] = useState<{ ok: boolean; data: unknown } | null>(null);

    // Form state
    const [taskType, setTaskType] = useState<'clustering' | 'dimensionality_reduction'>(
        (initialData.task_type as 'clustering' | 'dimensionality_reduction') || 'clustering'
    );
    const [datasetId, setDatasetId] = useState<string>((initialData.dataset_id as string) || '');
    const [algorithm, setAlgorithm] = useState<string>((initialData.algorithm as string) || '');
    const [featureColumns, setFeatureColumns] = useState<string[]>((initialData.feature_columns as string[]) || []);
    const [modelName, setModelName] = useState<string>((initialData.model_name as string) || '');

    // Hyperparameters
    const [nClusters, setNClusters] = useState<number>((initialData.hyperparameters as Record<string, number>)?.n_clusters || 3);
    const [eps, setEps] = useState<number>((initialData.hyperparameters as Record<string, number>)?.eps || 0.5);
    const [minSamples, setMinSamples] = useState<number>((initialData.hyperparameters as Record<string, number>)?.min_samples || 5);
    const [nComponents, setNComponents] = useState<number>((initialData.hyperparameters as Record<string, number>)?.n_components || 2);

    // Preprocessing
    const [normalization, setNormalization] = useState<string>(
        (initialData.preprocessing as Record<string, string>)?.normalization || 'standard'
    );
    const [handleMissing, setHandleMissing] = useState<string>(
        (initialData.preprocessing as Record<string, string>)?.handle_missing || 'zero'
    );

    const selectedDataset = datasets.find((d) => d.id === datasetId);
    const algorithms = taskType === 'clustering' ? CLUSTERING_ALGORITHMS : DIMENSIONALITY_REDUCTION_ALGORITHMS;

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const res = await api<{ datasets: Dataset[] }>('/api/ml/datasets', { method: 'GET' });
            setDatasets(res.datasets || []);
        } catch {
            // API may not be available
        } finally {
            setLoading(false);
        }
    };

    const getHyperparameters = () => {
        if (algorithm === 'kmeans') {
            return { n_clusters: nClusters };
        } else if (algorithm === 'dbscan') {
            return { eps, min_samples: minSamples };
        } else if (algorithm === 'pca') {
            return { n_components: nComponents };
        }
        return {};
    };

    const handleTrain = async () => {
        if (!datasetId || !algorithm) {
            alert('Please select a dataset and algorithm');
            return;
        }

        setTraining(true);
        setTrainResult(null);

        try {
            const result = await api<Model>('/api/ml/unsupervised/train', {
                method: 'POST',
                body: {
                    dataset_id: datasetId,
                    algorithm,
                    feature_columns: featureColumns.length > 0 ? featureColumns : null,
                    model_name: modelName || `${algorithm}_model`,
                    hyperparameters: getHyperparameters(),
                    preprocessing: {
                        normalization,
                        handle_missing: handleMissing,
                    },
                },
            });

            setTrainResult({ ok: true, data: result });
        } catch (err) {
            setTrainResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTraining(false);
        }
    };

    const handleFeatureToggle = (col: string) => {
        setFeatureColumns(prev =>
            prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
        );
    };

    return (
        <div className="space-y-6">
            {/* ── Task Type ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-lime-500 rounded-full" />
                    Task Type
                </h3>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        type="button"
                        onClick={() => { setTaskType('clustering'); setAlgorithm(''); }}
                        className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                            taskType === 'clustering'
                                ? 'border-amber-500/60 bg-amber-500/10 text-amber-300'
                                : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                        }`}
                    >
                        🔮 Clustering
                    </button>
                    <button
                        type="button"
                        onClick={() => { setTaskType('dimensionality_reduction'); setAlgorithm(''); }}
                        className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                            taskType === 'dimensionality_reduction'
                                ? 'border-amber-500/60 bg-amber-500/10 text-amber-300'
                                : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                        }`}
                    >
                        📉 Dim. Reduction
                    </button>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Dataset & Algorithm ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-lime-500 rounded-full" />
                    <Shapes className="w-4 h-4" />
                    Model Configuration
                </h3>

                {loading ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading data...
                    </div>
                ) : (
                    <div className="space-y-4">
                        <Field label="Dataset">
                            <div className="relative">
                                <select
                                    value={datasetId}
                                    onChange={(e) => { setDatasetId(e.target.value); setFeatureColumns([]); }}
                                    className={`${inputClass} appearance-none pr-8`}
                                >
                                    <option value="">Select a dataset...</option>
                                    {datasets.map((d) => (
                                        <option key={d.id} value={d.id}>
                                            {d.name} ({d.row_count} rows)
                                        </option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        </Field>

                        <Field label="Algorithm">
                            <div className="grid grid-cols-1 gap-2">
                                {algorithms.map((a) => (
                                    <button
                                        key={a.value}
                                        type="button"
                                        onClick={() => setAlgorithm(a.value)}
                                        className={`p-3 rounded-xl border text-left transition-all ${
                                            algorithm === a.value
                                                ? 'border-amber-500/60 bg-amber-500/10 text-amber-300'
                                                : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                        }`}
                                    >
                                        <span className="text-sm font-medium">{a.label}</span>
                                        <p className="text-xs text-slate-500 mt-0.5">{a.description}</p>
                                    </button>
                                ))}
                            </div>
                        </Field>

                        {selectedDataset && (
                            <Field label="Feature Columns" hint="Select features or leave empty to use all numeric">
                                <div className="max-h-32 overflow-y-auto bg-slate-800/40 rounded-xl p-2 space-y-1">
                                    {selectedDataset?.columns?.map((c) => (
                                        <label
                                            key={c.name}
                                            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-700/30 cursor-pointer"
                                        >
                                            <input
                                                type="checkbox"
                                                checked={featureColumns.includes(c.name)}
                                                onChange={() => handleFeatureToggle(c.name)}
                                                className="rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
                                            />
                                            <span className="text-sm text-slate-300">{c.name}</span>
                                            <span className="text-xs text-slate-500">({c.dtype})</span>
                                        </label>
                                    ))}
                                </div>
                            </Field>
                        )}

                        <Field label="Model Name" hint="Optional name for the trained model">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="My Clustering Model"
                                value={modelName}
                                onChange={(e) => setModelName(e.target.value)}
                            />
                        </Field>
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Hyperparameters ── */}
            {algorithm && (
                <section>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-lime-500 rounded-full" />
                        <Settings className="w-4 h-4" />
                        Hyperparameters
                    </h3>

                    <div className="space-y-4">
                        {algorithm === 'kmeans' && (
                            <Field label="Number of Clusters" hint="How many groups to create">
                                <input
                                    type="number"
                                    min="2"
                                    max="20"
                                    value={nClusters}
                                    onChange={(e) => setNClusters(parseInt(e.target.value))}
                                    className={inputClass}
                                />
                            </Field>
                        )}

                        {algorithm === 'dbscan' && (
                            <>
                                <Field label="Epsilon (eps)" hint="Maximum distance between points in a cluster">
                                    <input
                                        type="number"
                                        min="0.01"
                                        max="10"
                                        step="0.1"
                                        value={eps}
                                        onChange={(e) => setEps(parseFloat(e.target.value))}
                                        className={inputClass}
                                    />
                                </Field>
                                <Field label="Min Samples" hint="Minimum points to form a cluster">
                                    <input
                                        type="number"
                                        min="1"
                                        max="50"
                                        value={minSamples}
                                        onChange={(e) => setMinSamples(parseInt(e.target.value))}
                                        className={inputClass}
                                    />
                                </Field>
                            </>
                        )}

                        {algorithm === 'pca' && (
                            <Field label="Number of Components" hint="Dimensions to reduce to">
                                <input
                                    type="number"
                                    min="1"
                                    max="100"
                                    value={nComponents}
                                    onChange={(e) => setNComponents(parseInt(e.target.value))}
                                    className={inputClass}
                                />
                            </Field>
                        )}
                    </div>
                </section>
            )}

            {algorithm && <div className="h-px bg-slate-700/50" />}

            {/* ── Preprocessing ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-lime-500 rounded-full" />
                    Preprocessing
                </h3>

                <div className="grid grid-cols-2 gap-3">
                    <Field label="Normalization">
                        <div className="relative">
                            <select
                                value={normalization}
                                onChange={(e) => setNormalization(e.target.value)}
                                className={`${inputClass} appearance-none pr-8 text-xs`}
                            >
                                {NORMALIZATION_OPTIONS.map((o) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>

                    <Field label="Missing Values">
                        <div className="relative">
                            <select
                                value={handleMissing}
                                onChange={(e) => setHandleMissing(e.target.value)}
                                className={`${inputClass} appearance-none pr-8 text-xs`}
                            >
                                {MISSING_VALUE_OPTIONS.map((o) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Train & Results ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handleTrain}
                    disabled={training || !datasetId || !algorithm}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {training ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {training ? 'Training...' : 'Train Model'}
                </button>

                {trainResult && (
                    <div
                        className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-48 ${
                            trainResult.ok
                                ? 'bg-green-500/10 border-green-500/30 text-green-300'
                                : 'bg-red-500/10 border-red-500/30 text-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {trainResult.ok ? (
                                <><CheckCircle2 className="w-3.5 h-3.5" /> Training Successful</>
                            ) : (
                                <><AlertCircle className="w-3.5 h-3.5" /> Training Failed</>
                            )}
                        </div>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(trainResult.data, null, 2)}</pre>
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => onSave({
                        task_type: taskType,
                        dataset_id: datasetId,
                        algorithm,
                        feature_columns: featureColumns,
                        model_name: modelName,
                        hyperparameters: getHyperparameters(),
                        preprocessing: {
                            normalization,
                            handle_missing: handleMissing,
                        },
                    })}
                    className="w-full py-3 bg-gradient-to-r from-amber-500 via-yellow-500 to-lime-600 hover:from-amber-600 hover:via-yellow-600 hover:to-lime-700 text-white font-bold rounded-xl shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default UnsupervisedTrainConfig;
