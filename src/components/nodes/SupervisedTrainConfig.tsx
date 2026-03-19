import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Target, Settings } from 'lucide-react';
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

interface SupervisedTrainConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CLASSIFICATION_ALGORITHMS = [
    { value: 'logistic_regression', label: 'Logistic Regression' },
    { value: 'random_forest_classifier', label: 'Random Forest' },
    { value: 'svm_classifier', label: 'SVM (Support Vector Machine)' },
    { value: 'gradient_boosting_classifier', label: 'Gradient Boosting' },
    { value: 'adaboost_classifier', label: 'AdaBoost' },
    { value: 'catboost_classifier', label: 'CatBoost' },
];

const REGRESSION_ALGORITHMS = [
    { value: 'linear_regression', label: 'Linear Regression' },
    { value: 'random_forest_regressor', label: 'Random Forest' },
    { value: 'svm_regressor', label: 'SVR (Support Vector Regression)' },
    { value: 'gradient_boosting_regressor', label: 'Gradient Boosting' },
    { value: 'adaboost_regressor', label: 'AdaBoost' },
    { value: 'catboost_regressor', label: 'CatBoost' },
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
    { value: 'mode', label: 'Replace with Mode' },
    { value: 'drop', label: 'Drop Rows' },
];

// ─── Styles ───────────────────────────────────────────────────────────────────

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

const SupervisedTrainConfig: React.FC<SupervisedTrainConfigProps> = ({ initialData, onSave }) => {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);
    const [training, setTraining] = useState(false);
    const [trainResult, setTrainResult] = useState<{ ok: boolean; data: unknown } | null>(null);

    // Form state
    const [taskType, setTaskType] = useState<'classification' | 'regression'>(
        (initialData.task_type as 'classification' | 'regression') || 'classification'
    );
    const [datasetId, setDatasetId] = useState<string>((initialData.dataset_id as string) || '');
    const [algorithm, setAlgorithm] = useState<string>((initialData.algorithm as string) || '');
    const [targetColumn, setTargetColumn] = useState<string>((initialData.target_column as string) || '');
    const [featureColumns, setFeatureColumns] = useState<string[]>((initialData.feature_columns as string[]) || []);
    const [modelName, setModelName] = useState<string>((initialData.model_name as string) || '');

    // Preprocessing
    const [normalization, setNormalization] = useState<string>(
        (initialData.preprocessing as Record<string, string>)?.normalization || 'standard'
    );
    const [handleMissing, setHandleMissing] = useState<string>(
        (initialData.preprocessing as Record<string, string>)?.handle_missing || 'zero'
    );
    const [trainSize, setTrainSize] = useState<number>(
        (initialData.preprocessing as Record<string, number>)?.train_size || 0.7
    );
    const [valSize, setValSize] = useState<number>(
        (initialData.preprocessing as Record<string, number>)?.val_size || 0.15
    );
    const [testSize, setTestSize] = useState<number>(
        (initialData.preprocessing as Record<string, number>)?.test_size || 0.15
    );

    const selectedDataset = datasets.find((d) => d.id === datasetId);
    const algorithms = taskType === 'classification' ? CLASSIFICATION_ALGORITHMS : REGRESSION_ALGORITHMS;

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [datasetsRes, modelsRes] = await Promise.all([
                api<{ datasets: Dataset[] }>('/api/ml/datasets', { method: 'GET' }),
                api<{ models: Model[] }>('/api/ml/models', { method: 'GET' }),
            ]);
            setDatasets(datasetsRes.datasets || []);
            setModels(modelsRes.models?.filter(m => m.model_category === 'supervised') || []);
        } catch {
            // API may not be available
        } finally {
            setLoading(false);
        }
    };

    const handleTrain = async () => {
        if (!datasetId || !algorithm || !targetColumn) {
            alert('Please select a dataset, algorithm, and target column');
            return;
        }

        setTraining(true);
        setTrainResult(null);

        try {
            const result = await api<Model>('/api/ml/supervised/train', {
                method: 'POST',
                body: {
                    dataset_id: datasetId,
                    algorithm,
                    target_column: targetColumn,
                    feature_columns: featureColumns.length > 0 ? featureColumns : null,
                    model_name: modelName || `${algorithm}_model`,
                    preprocessing: {
                        normalization,
                        handle_missing: handleMissing,
                        train_size: trainSize,
                        val_size: valSize,
                        test_size: testSize,
                    },
                },
            });

            setTrainResult({ ok: true, data: result });
            await loadData(); // Refresh models list
        } catch (err) {
            setTrainResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTraining(false);
        }
    };

    const handleFeatureToggle = (col: string) => {
        if (col === targetColumn) return; // Can't select target as feature
        setFeatureColumns(prev =>
            prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
        );
    };

    return (
        <div className="space-y-6">
            {/* ── Task Type ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-violet-400 to-fuchsia-500 rounded-full" />
                    Task Type
                </h3>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        type="button"
                        onClick={() => { setTaskType('classification'); setAlgorithm(''); }}
                        className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                            taskType === 'classification'
                                ? 'border-violet-500/60 bg-violet-500/10 text-violet-300'
                                : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                        }`}
                    >
                        🏷️ Classification
                    </button>
                    <button
                        type="button"
                        onClick={() => { setTaskType('regression'); setAlgorithm(''); }}
                        className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                            taskType === 'regression'
                                ? 'border-violet-500/60 bg-violet-500/10 text-violet-300'
                                : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                        }`}
                    >
                        📈 Regression
                    </button>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Dataset & Algorithm ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-violet-400 to-fuchsia-500 rounded-full" />
                    <Target className="w-4 h-4" />
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
                                    onChange={(e) => { setDatasetId(e.target.value); setTargetColumn(''); setFeatureColumns([]); }}
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
                            <div className="relative">
                                <select
                                    value={algorithm}
                                    onChange={(e) => setAlgorithm(e.target.value)}
                                    className={`${inputClass} appearance-none pr-8`}
                                >
                                    <option value="">Select an algorithm...</option>
                                    {algorithms.map((a) => (
                                        <option key={a.value} value={a.value}>{a.label}</option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        </Field>

                        {selectedDataset && (
                            <Field label="Target Column" hint="The column to predict">
                                <div className="relative">
                                    <select
                                        value={targetColumn}
                                        onChange={(e) => { setTargetColumn(e.target.value); setFeatureColumns([]); }}
                                        className={`${inputClass} appearance-none pr-8`}
                                    >
                                        <option value="">Select target column...</option>
                                        {selectedDataset.columns.map((c) => (
                                            <option key={c.name} value={c.name}>
                                                {c.name} ({c.dtype})
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                                </div>
                            </Field>
                        )}

                        {selectedDataset && targetColumn && (
                            <Field label="Feature Columns" hint="Select features or leave empty to use all">
                                <div className="max-h-32 overflow-y-auto bg-slate-800/40 rounded-xl p-2 space-y-1">
                                    {selectedDataset.columns
                                        .filter(c => c.name !== targetColumn)
                                        .map((c) => (
                                            <label
                                                key={c.name}
                                                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-700/30 cursor-pointer"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={featureColumns.includes(c.name)}
                                                    onChange={() => handleFeatureToggle(c.name)}
                                                    className="rounded border-slate-600 bg-slate-700 text-violet-500 focus:ring-violet-500"
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
                                placeholder="My Classification Model"
                                value={modelName}
                                onChange={(e) => setModelName(e.target.value)}
                            />
                        </Field>
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Preprocessing ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-violet-400 to-fuchsia-500 rounded-full" />
                    <Settings className="w-4 h-4" />
                    Preprocessing
                </h3>

                <div className="space-y-4">
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

                    <Field label="Train / Validation / Test Split">
                        <div className="grid grid-cols-3 gap-2">
                            <div>
                                <input
                                    type="number"
                                    min="0.1"
                                    max="0.9"
                                    step="0.05"
                                    value={trainSize}
                                    onChange={(e) => setTrainSize(parseFloat(e.target.value))}
                                    className={`${inputClass} text-center text-xs`}
                                />
                                <p className="text-xs text-slate-500 text-center mt-1">Train</p>
                            </div>
                            <div>
                                <input
                                    type="number"
                                    min="0"
                                    max="0.5"
                                    step="0.05"
                                    value={valSize}
                                    onChange={(e) => setValSize(parseFloat(e.target.value))}
                                    className={`${inputClass} text-center text-xs`}
                                />
                                <p className="text-xs text-slate-500 text-center mt-1">Validation</p>
                            </div>
                            <div>
                                <input
                                    type="number"
                                    min="0.05"
                                    max="0.5"
                                    step="0.05"
                                    value={testSize}
                                    onChange={(e) => setTestSize(parseFloat(e.target.value))}
                                    className={`${inputClass} text-center text-xs`}
                                />
                                <p className="text-xs text-slate-500 text-center mt-1">Test</p>
                            </div>
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
                    disabled={training || !datasetId || !algorithm || !targetColumn}
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
                        target_column: targetColumn,
                        feature_columns: featureColumns,
                        model_name: modelName,
                        preprocessing: {
                            normalization,
                            handle_missing: handleMissing,
                            train_size: trainSize,
                            val_size: valSize,
                            test_size: testSize,
                        },
                    })}
                    className="w-full py-3 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-violet-600 hover:from-violet-600 hover:via-fuchsia-600 hover:to-violet-700 text-white font-bold rounded-xl shadow-lg shadow-violet-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default SupervisedTrainConfig;
