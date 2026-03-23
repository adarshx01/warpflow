import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Zap, Image, Link, Cloud, HardDrive, Upload } from 'lucide-react';
import { api } from '../../lib/api';
import { checkSecretExists } from '../../lib/secrets';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CVInferenceConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

interface SavedModel {
    name: string;
    file: string;
    path: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CV_TASKS = {
    classification: [
        { value: 'resnet', label: 'ResNet-50' },
        { value: 'efficientnet', label: 'EfficientNet-B0' },
        { value: 'vgg', label: 'VGG-16' },
        { value: 'mobilenet', label: 'MobileNet-V2' },
        { value: 'densenet', label: 'DenseNet-121' },
        { value: 'vit', label: 'Vision Transformer' },
        { value: 'convnext', label: 'ConvNeXt-Tiny' },
    ],
    detection: [
        { value: 'fasterrcnn', label: 'Faster R-CNN' },
        { value: 'ssd', label: 'SSD' },
        { value: 'retinanet', label: 'RetinaNet' },
        { value: 'yolov5', label: 'YOLOv5' },
        { value: 'yolov8', label: 'YOLOv8' },
    ],
    segmentation: [
        { value: 'unet', label: 'U-Net' },
        { value: 'deeplabv3', label: 'DeepLabV3' },
        { value: 'fcn', label: 'FCN' },
        { value: 'pspnet', label: 'PSPNet' },
        { value: 'maskrcnn', label: 'Mask R-CNN' },
    ],
};

// ─── Styles ───────────────────────────────────────────────────────────────────

const inputClass =
    'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all';

const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

const CVInferenceConfig: React.FC<CVInferenceConfigProps> = ({ initialData, onSave }) => {
    const [inferencing, setInferencing] = useState(false);
    const [inferenceResult, setInferenceResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [s3Configured, setS3Configured] = useState(false);
    const [cvServiceAlive, setCvServiceAlive] = useState<boolean | null>(null);
    const [savedModels, setSavedModels] = useState<Record<string, SavedModel[]>>({});
    const [loadingModels, setLoadingModels] = useState(true);

    // Form state - Task & Model
    const [taskType, setTaskType] = useState<'classification' | 'detection' | 'segmentation'>(
        (initialData.task_type as 'classification' | 'detection' | 'segmentation') || 'classification'
    );
    const [modelName, setModelName] = useState<string>((initialData.model_name as string) || 'resnet');

    // Model source
    const [modelSource, setModelSource] = useState<'local' | 's3' | 'trained'>(
        (initialData.model_source as 'local' | 's3' | 'trained') || 'local'
    );
    const [modelPath, setModelPath] = useState<string>((initialData.model_path as string) || '');
    const [s3ModelPath, setS3ModelPath] = useState<string>((initialData.s3_model_path as string) || '');
    const [selectedSavedModel, setSelectedSavedModel] = useState<string>((initialData.selected_saved_model as string) || '');

    // Image input
    const [inputType, setInputType] = useState<'file' | 'url' | 'webcam'>(
        (initialData.input_type as 'file' | 'url' | 'webcam') || 'file'
    );
    const [imagePath, setImagePath] = useState<string>((initialData.image_path as string) || '');
    const [imageUrl, setImageUrl] = useState<string>((initialData.image_url as string) || '');

    // Model parameters
    const [numClasses, setNumClasses] = useState<number>((initialData.num_classes as number) || 0);
    const [datasetPath, setDatasetPath] = useState<string>((initialData.dataset_path as string) || '');
    const [confidenceThreshold, setConfidenceThreshold] = useState<number>(
        (initialData.confidence_threshold as number) || 0.5
    );

    const models = CV_TASKS[taskType] || [];

    useEffect(() => {
        // Check if S3 is configured
        Promise.all([
            checkSecretExists('s3_access_key'),
            checkSecretExists('s3_secret_key'),
            checkSecretExists('s3_bucket_name'),
        ]).then(([accessKey, secretKey, bucket]) => {
            setS3Configured(accessKey && secretKey && bucket);
        });

        // Check if CV service is alive
        api<{ status: string }>('/api/cv/alive', { method: 'GET' })
            .then(() => setCvServiceAlive(true))
            .catch(() => setCvServiceAlive(false));

        // Fetch saved models
        api<{ saved_models: Record<string, SavedModel[]> }>('/api/cv/models/saved', { method: 'GET' })
            .then((res) => {
                setSavedModels(res.saved_models || {});
            })
            .catch(() => {})
            .finally(() => setLoadingModels(false));
    }, []);

    // Update model when task changes
    useEffect(() => {
        const defaultModel = CV_TASKS[taskType]?.[0]?.value || '';
        if (!CV_TASKS[taskType]?.find(m => m.value === modelName)) {
            setModelName(defaultModel);
        }
    }, [taskType]);

    const handleLoadModel = async () => {
        setInferencing(true);
        setInferenceResult(null);

        try {
            let finalModelPath = modelPath;
            if (modelSource === 's3') {
                // Download from S3 first
                const downloadRes = await api<{ local_path: string }>('/api/cv/models/download-s3', {
                    method: 'POST',
                    body: { s3_path: s3ModelPath },
                });
                finalModelPath = downloadRes.local_path;
            } else if (modelSource === 'trained' && selectedSavedModel) {
                finalModelPath = selectedSavedModel;
            }

            const result = await api<{ status: string; message: string }>('/api/cv/models/load', {
                method: 'POST',
                body: {
                    task_type: taskType,
                    model_name: modelName,
                    model_path: finalModelPath,
                    dataset_path: datasetPath || undefined,
                    num_classes: numClasses || undefined,
                },
            });

            setInferenceResult({ ok: true, data: result });
        } catch (err) {
            setInferenceResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setInferencing(false);
        }
    };

    const handleInference = async () => {
        setInferencing(true);
        setInferenceResult(null);

        try {
            const result = await api<{ predictions: unknown; annotated_image?: string }>('/api/cv/infer', {
                method: 'POST',
                body: {
                    input_type: inputType,
                    image_path: inputType === 'file' ? imagePath : undefined,
                    image_url: inputType === 'url' ? imageUrl : undefined,
                    confidence_threshold: confidenceThreshold,
                },
            });

            setInferenceResult({ ok: true, data: result });
        } catch (err) {
            setInferenceResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setInferencing(false);
        }
    };

    const taskModels = savedModels[taskType] || [];

    return (
        <div className="space-y-6">
            {/* ── Service Status ── */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm ${
                cvServiceAlive === null
                    ? 'bg-slate-700/30 border-slate-600/30 text-slate-400'
                    : cvServiceAlive
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-red-500/10 border-red-500/30 text-red-300'
            }`}>
                <div className={`w-2 h-2 rounded-full ${
                    cvServiceAlive === null ? 'bg-slate-400' : cvServiceAlive ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                }`} />
                {cvServiceAlive === null
                    ? 'Checking CV service...'
                    : cvServiceAlive
                    ? 'CV Inference Service Online'
                    : 'CV Inference Service Offline - Start with python main.py'}
            </div>

            {/* ── Task Type ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-emerald-400 to-teal-500 rounded-full" />
                    Task Type
                </h3>
                <div className="grid grid-cols-3 gap-2">
                    {(['classification', 'detection', 'segmentation'] as const).map((task) => (
                        <button
                            key={task}
                            type="button"
                            onClick={() => setTaskType(task)}
                            className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                                taskType === task
                                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                    : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                            }`}
                        >
                            {task === 'classification' && '🏷️'}
                            {task === 'detection' && '🎯'}
                            {task === 'segmentation' && '🖼️'}
                            {' '}{task.charAt(0).toUpperCase() + task.slice(1)}
                        </button>
                    ))}
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Model Selection ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-emerald-400 to-teal-500 rounded-full" />
                    <Zap className="w-4 h-4" />
                    Model Selection
                </h3>

                <div className="space-y-4">
                    <Field label="Model Architecture">
                        <div className="relative">
                            <select
                                value={modelName}
                                onChange={(e) => setModelName(e.target.value)}
                                className={`${inputClass} appearance-none pr-8`}
                            >
                                {models.map((m) => (
                                    <option key={m.value} value={m.value}>
                                        {m.label}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>

                    {/* Model Source */}
                    <Field label="Model Source">
                        <div className="grid grid-cols-3 gap-2">
                            <button
                                type="button"
                                onClick={() => setModelSource('local')}
                                className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                    modelSource === 'local'
                                        ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                        : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                }`}
                            >
                                <HardDrive className="w-3.5 h-3.5" /> Local Path
                            </button>
                            <button
                                type="button"
                                onClick={() => setModelSource('trained')}
                                className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                    modelSource === 'trained'
                                        ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                        : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                }`}
                            >
                                <CheckCircle2 className="w-3.5 h-3.5" /> Saved Models
                            </button>
                            <button
                                type="button"
                                onClick={() => setModelSource('s3')}
                                disabled={!s3Configured}
                                className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                    modelSource === 's3'
                                        ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                        : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                                } ${!s3Configured ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                <Cloud className="w-3.5 h-3.5" /> S3
                            </button>
                        </div>
                    </Field>

                    {modelSource === 'local' && (
                        <Field label="Model Path" hint="Path to .pt model file">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="/path/to/model.pt"
                                value={modelPath}
                                onChange={(e) => setModelPath(e.target.value)}
                            />
                        </Field>
                    )}

                    {modelSource === 'trained' && (
                        <Field label="Saved Model">
                            <div className="relative">
                                <select
                                    value={selectedSavedModel}
                                    onChange={(e) => setSelectedSavedModel(e.target.value)}
                                    className={`${inputClass} appearance-none pr-8`}
                                    disabled={loadingModels}
                                >
                                    <option value="">
                                        {loadingModels ? 'Loading models...' : 'Select a saved model'}
                                    </option>
                                    {taskModels.map((m) => (
                                        <option key={m.path} value={m.path}>
                                            {m.name} - {m.file}
                                        </option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                            </div>
                        </Field>
                    )}

                    {modelSource === 's3' && (
                        <Field label="S3 Model Path" hint="Path within S3 bucket">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="models/cv/my_model.pt"
                                value={s3ModelPath}
                                onChange={(e) => setS3ModelPath(e.target.value)}
                            />
                        </Field>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Number of Classes" hint="For classification/segmentation">
                            <input
                                type="number"
                                min="0"
                                max="10000"
                                value={numClasses}
                                onChange={(e) => setNumClasses(parseInt(e.target.value) || 0)}
                                className={inputClass}
                            />
                        </Field>
                        <Field label="Dataset Path" hint="For class names (optional)">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="/path/to/dataset"
                                value={datasetPath}
                                onChange={(e) => setDatasetPath(e.target.value)}
                            />
                        </Field>
                    </div>

                    <button
                        type="button"
                        onClick={handleLoadModel}
                        disabled={inferencing || !cvServiceAlive}
                        className="w-full py-2 bg-slate-700 hover:bg-slate-600 border border-slate-600/50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-medium rounded-xl transition-all flex items-center justify-center gap-2"
                    >
                        {inferencing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                        Load Model
                    </button>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Image Input ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-emerald-400 to-teal-500 rounded-full" />
                    <Image className="w-4 h-4" />
                    Image Input
                </h3>

                <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-2">
                        <button
                            type="button"
                            onClick={() => setInputType('file')}
                            className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                inputType === 'file'
                                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                    : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                            }`}
                        >
                            <HardDrive className="w-3.5 h-3.5" /> Local File
                        </button>
                        <button
                            type="button"
                            onClick={() => setInputType('url')}
                            className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                inputType === 'url'
                                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                    : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                            }`}
                        >
                            <Link className="w-3.5 h-3.5" /> URL
                        </button>
                        <button
                            type="button"
                            onClick={() => setInputType('webcam')}
                            className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                                inputType === 'webcam'
                                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                                    : 'border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600'
                            }`}
                        >
                            📹 Webcam
                        </button>
                    </div>

                    {inputType === 'file' && (
                        <Field label="Image Path">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="/path/to/image.jpg"
                                value={imagePath}
                                onChange={(e) => setImagePath(e.target.value)}
                            />
                        </Field>
                    )}

                    {inputType === 'url' && (
                        <Field label="Image URL">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="https://example.com/image.jpg"
                                value={imageUrl}
                                onChange={(e) => setImageUrl(e.target.value)}
                            />
                        </Field>
                    )}

                    {inputType === 'webcam' && (
                        <div className="p-4 bg-slate-800/40 rounded-xl text-center">
                            <p className="text-sm text-slate-400">
                                Webcam stream will be used for real-time inference
                            </p>
                            <p className="text-xs text-slate-500 mt-1">
                                Access the video feed at /video_feed endpoint
                            </p>
                        </div>
                    )}

                    <Field label="Confidence Threshold">
                        <div className="flex items-center gap-3">
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.05"
                                value={confidenceThreshold}
                                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                                className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                            <span className="text-sm text-slate-300 w-12 text-right">
                                {(confidenceThreshold * 100).toFixed(0)}%
                            </span>
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Inference & Results ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handleInference}
                    disabled={inferencing || !cvServiceAlive || (inputType === 'file' && !imagePath) || (inputType === 'url' && !imageUrl)}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {inferencing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {inferencing ? 'Running Inference...' : 'Run Inference'}
                </button>

                {inferenceResult && (
                    <div
                        className={`p-3 rounded-xl border text-xs font-mono overflow-auto max-h-48 ${
                            inferenceResult.ok
                                ? 'bg-green-500/10 border-green-500/30 text-green-300'
                                : 'bg-red-500/10 border-red-500/30 text-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-1.5 mb-2 font-sans font-semibold">
                            {inferenceResult.ok ? (
                                <><CheckCircle2 className="w-3.5 h-3.5" /> Inference Result</>
                            ) : (
                                <><AlertCircle className="w-3.5 h-3.5" /> Inference Failed</>
                            )}
                        </div>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(inferenceResult.data, null, 2)}</pre>
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => onSave({
                        task_type: taskType,
                        model_name: modelName,
                        model_source: modelSource,
                        model_path: modelPath,
                        s3_model_path: s3ModelPath,
                        selected_saved_model: selectedSavedModel,
                        input_type: inputType,
                        image_path: imagePath,
                        image_url: imageUrl,
                        num_classes: numClasses,
                        dataset_path: datasetPath,
                        confidence_threshold: confidenceThreshold,
                    })}
                    className="w-full py-3 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-600 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-700 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default CVInferenceConfig;
