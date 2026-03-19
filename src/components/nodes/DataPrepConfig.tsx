import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Upload, Eye, BarChart3, Database } from 'lucide-react';
import { api } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ColumnInfo {
    name: string;
    dtype: string;
    column_type: 'numeric' | 'categorical';
    null_count: number;
    null_percentage: number;
    unique_count: number;
    stats?: {
        min?: number;
        max?: number;
        mean?: number;
        median?: number;
        std?: number;
    };
    top_values?: Array<{ value: string; count: number }>;
}

interface DatasetAnalysis {
    row_count: number;
    column_count: number;
    columns: ColumnInfo[];
    numeric_columns: string[];
    categorical_columns: string[];
    memory_usage_mb: number;
}

interface Dataset {
    id: string;
    name: string;
    file_type: string;
    row_count: number;
    columns: Array<{ name: string; dtype: string }>;
    analysis?: DatasetAnalysis;
}

interface DataPrepConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

const DataPrepConfig: React.FC<DataPrepConfigProps> = ({ initialData, onSave }) => {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [selectedDatasetId, setSelectedDatasetId] = useState<string>((initialData.dataset_id as string) || '');
    const [analysis, setAnalysis] = useState<DatasetAnalysis | null>(null);
    const [preview, setPreview] = useState<Record<string, unknown>[] | null>(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [uploading, setUploading] = useState(false);

    // Upload state
    const [dragActive, setDragActive] = useState(false);
    const [uploadResult, setUploadResult] = useState<{ ok: boolean; data: unknown } | null>(null);

    useEffect(() => {
        loadDatasets();
    }, []);

    useEffect(() => {
        if (selectedDatasetId) {
            loadAnalysis(selectedDatasetId);
        }
    }, [selectedDatasetId]);

    const loadDatasets = async () => {
        try {
            const res = await api<{ datasets: Dataset[] }>('/api/ml/datasets', { method: 'GET' });
            setDatasets(res.datasets || []);
        } catch {
            // API may not be available
        } finally {
            setLoading(false);
        }
    };

    const loadAnalysis = async (datasetId: string) => {
        setAnalyzing(true);
        try {
            const [analysisRes, previewRes] = await Promise.all([
                api<DatasetAnalysis>(`/api/ml/datasets/${datasetId}/analyze`, { method: 'GET' }),
                api<{ data: Record<string, unknown>[] }>(`/api/ml/datasets/${datasetId}/preview?n_rows=5`, { method: 'GET' }),
            ]);
            setAnalysis(analysisRes);
            setPreview(previewRes.data || []);
        } catch (err) {
            console.error('Failed to analyze dataset:', err);
        } finally {
            setAnalyzing(false);
        }
    };

    const handleFile = async (file: File) => {
        const ext = file.name.split('.').pop()?.toLowerCase();
        if (ext !== 'csv' && ext !== 'json') {
            alert('Please upload a CSV or JSON file');
            return;
        }

        setUploading(true);
        setUploadResult(null);

        try {
            const content = await file.arrayBuffer();
            const base64 = btoa(String.fromCharCode(...new Uint8Array(content)));

            const result = await api<Dataset>('/api/ml/datasets/upload', {
                method: 'POST',
                body: {
                    file_content: base64,
                    filename: file.name,
                    file_type: ext,
                },
            });

            setUploadResult({ ok: true, data: result });
            await loadDatasets();
            setSelectedDatasetId(result.id);
        } catch (err) {
            setUploadResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setUploading(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    return (
        <div className="space-y-6">
            {/* ── Upload Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-emerald-500 rounded-full" />
                    Upload Dataset
                </h3>
                <div
                    className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                        dragActive
                            ? 'border-cyan-500 bg-cyan-500/10'
                            : 'border-slate-700 hover:border-slate-600'
                    }`}
                    onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                    onDragLeave={() => setDragActive(false)}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        accept=".csv,.json"
                        className="hidden"
                        id="dataset-upload"
                        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />
                    <label htmlFor="dataset-upload" className="cursor-pointer">
                        {uploading ? (
                            <Loader2 className="w-8 h-8 mx-auto mb-2 text-cyan-400 animate-spin" />
                        ) : (
                            <Upload className="w-8 h-8 mx-auto mb-2 text-slate-500" />
                        )}
                        <p className="text-sm text-slate-400">
                            {uploading ? 'Uploading...' : 'Drop file here or click to browse'}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">CSV or JSON files only</p>
                    </label>
                </div>

                {uploadResult && (
                    <div
                        className={`mt-3 p-3 rounded-xl border text-xs ${
                            uploadResult.ok
                                ? 'bg-green-500/10 border-green-500/30 text-green-300'
                                : 'bg-red-500/10 border-red-500/30 text-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-1.5 font-semibold">
                            {uploadResult.ok ? (
                                <><CheckCircle2 className="w-3.5 h-3.5" /> Upload Successful</>
                            ) : (
                                <><AlertCircle className="w-3.5 h-3.5" /> Upload Failed</>
                            )}
                        </div>
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Select Dataset Section ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-emerald-500 rounded-full" />
                    Select Dataset
                </h3>

                {loading ? (
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading datasets...
                    </div>
                ) : (
                    <Field label="Dataset">
                        <div className="relative">
                            <select
                                value={selectedDatasetId}
                                onChange={(e) => setSelectedDatasetId(e.target.value)}
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
                )}
            </section>

            {/* ── Analysis Section ── */}
            {selectedDatasetId && (
                <>
                    <div className="h-px bg-slate-700/50" />

                    <section>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-emerald-500 rounded-full" />
                            <BarChart3 className="w-4 h-4" />
                            Dataset Analysis
                        </h3>

                        {analyzing ? (
                            <div className="flex items-center gap-2 text-slate-500 text-sm">
                                <Loader2 className="w-4 h-4 animate-spin" /> Analyzing dataset...
                            </div>
                        ) : analysis ? (
                            <div className="space-y-4">
                                {/* Summary Stats */}
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="bg-slate-800/60 rounded-xl p-3 text-center">
                                        <p className="text-2xl font-bold text-cyan-400">{analysis.row_count}</p>
                                        <p className="text-xs text-slate-500">Rows</p>
                                    </div>
                                    <div className="bg-slate-800/60 rounded-xl p-3 text-center">
                                        <p className="text-2xl font-bold text-emerald-400">{analysis.column_count}</p>
                                        <p className="text-xs text-slate-500">Columns</p>
                                    </div>
                                    <div className="bg-slate-800/60 rounded-xl p-3 text-center">
                                        <p className="text-2xl font-bold text-amber-400">{analysis.memory_usage_mb}</p>
                                        <p className="text-xs text-slate-500">MB</p>
                                    </div>
                                </div>

                                {/* Column Types */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-3">
                                        <p className="text-xs text-blue-400 font-semibold mb-2">Numeric Columns ({analysis.numeric_columns.length})</p>
                                        <div className="flex flex-wrap gap-1">
                                            {analysis.numeric_columns.map((col) => (
                                                <span key={col} className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-xs rounded-full">
                                                    {col}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3">
                                        <p className="text-xs text-purple-400 font-semibold mb-2">Categorical Columns ({analysis.categorical_columns.length})</p>
                                        <div className="flex flex-wrap gap-1">
                                            {analysis.categorical_columns.map((col) => (
                                                <span key={col} className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded-full">
                                                    {col}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Column Details */}
                                <div className="bg-slate-800/40 rounded-xl p-3">
                                    <p className="text-xs text-slate-400 font-semibold mb-2">Column Details</p>
                                    <div className="max-h-40 overflow-y-auto space-y-2">
                                        {analysis.columns.map((col) => (
                                            <div key={col.name} className="flex items-center justify-between text-xs">
                                                <span className="text-slate-300">{col.name}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className={`px-2 py-0.5 rounded-full ${
                                                        col.column_type === 'numeric'
                                                            ? 'bg-blue-500/20 text-blue-300'
                                                            : 'bg-purple-500/20 text-purple-300'
                                                    }`}>
                                                        {col.column_type}
                                                    </span>
                                                    {col.null_count > 0 && (
                                                        <span className="text-amber-400">
                                                            {col.null_percentage}% null
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : null}
                    </section>

                    {/* ── Preview Section ── */}
                    {preview && preview.length > 0 && (
                        <>
                            <div className="h-px bg-slate-700/50" />

                            <section>
                                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-emerald-500 rounded-full" />
                                    <Eye className="w-4 h-4" />
                                    Data Preview
                                </h3>
                                <div className="bg-slate-800/40 rounded-xl p-3 overflow-x-auto">
                                    <table className="w-full text-xs">
                                        <thead>
                                            <tr className="text-slate-400">
                                                {Object.keys(preview[0]).map((key) => (
                                                    <th key={key} className="px-2 py-1 text-left font-semibold">
                                                        {key}
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {preview.map((row, i) => (
                                                <tr key={i} className="text-slate-300 border-t border-slate-700/50">
                                                    {Object.values(row).map((val, j) => (
                                                        <td key={j} className="px-2 py-1 truncate max-w-[150px]">
                                                            {String(val)}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        </>
                    )}
                </>
            )}

            <div className="h-px bg-slate-700/50" />

            {/* ── Save Button ── */}
            <section>
                <button
                    type="button"
                    onClick={() => onSave({
                        dataset_id: selectedDatasetId,
                        analysis: analysis,
                    })}
                    disabled={!selectedDatasetId}
                    className="w-full py-3 bg-gradient-to-r from-cyan-500 via-emerald-500 to-cyan-600 hover:from-cyan-600 hover:via-emerald-600 hover:to-cyan-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default DataPrepConfig;
