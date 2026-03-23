import React, { useState, useEffect } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Play, Cpu, Settings, FolderOpen, Cloud, HardDrive } from 'lucide-react';
import { api } from '../../lib/api';
import { checkSecretExists } from '../../lib/secrets';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CVTrainConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CV_TASKS = {
    classification: [
        { value: 'resnet', label: 'ResNet-50', description: 'Deep residual network' },
        { value: 'efficientnet', label: 'EfficientNet-B0', description: 'Efficient scaling' },
        { value: 'vgg', label: 'VGG-16', description: 'Very deep CNN' },
        { value: 'mobilenet', label: 'MobileNet-V2', description: 'Lightweight mobile' },
        { value: 'densenet', label: 'DenseNet-121', description: 'Dense connections' },
        { value: 'vit', label: 'Vision Transformer', description: 'Transformer-based' },
        { value: 'convnext', label: 'ConvNeXt-Tiny', description: 'Modern ConvNet' },
    ],
    detection: [
        { value: 'fasterrcnn', label: 'Faster R-CNN', description: 'Two-stage detector' },
        { value: 'ssd', label: 'SSD', description: 'Single shot detector' },
        { value: 'retinanet', label: 'RetinaNet', description: 'Focal loss detector' },
        { value: 'yolov5', label: 'YOLOv5', description: 'YOLO v5 (requires ultralytics)' },
        { value: 'yolov8', label: 'YOLOv8', description: 'YOLO v8 (requires ultralytics)' },
    ],
    segmentation: [
        { value: 'unet', label: 'U-Net', description: 'Encoder-decoder architecture' },
        { value: 'deeplabv3', label: 'DeepLabV3', description: 'Atrous convolutions' },
        { value: 'fcn', label: 'FCN', description: 'Fully convolutional network' },
        { value: 'pspnet', label: 'PSPNet', description: 'Pyramid pooling module' },
        { value: 'maskrcnn', label: 'Mask R-CNN', description: 'Instance segmentation' },
    ],
};

const OPTIMIZERS = [
    { value: 'adam', label: 'Adam', description: 'Adaptive learning rate' },
    { value: 'sgd', label: 'SGD', description: 'Stochastic gradient descent' },
    { value: 'adamw', label: 'AdamW', description: 'Adam with weight decay' },
    { value: 'rmsprop', label: 'RMSprop', description: 'Root mean square prop' },
];

const DATASET_FORMATS = [
    { value: 'imagefolder', label: 'ImageFolder', description: 'class_name/images structure' },
    { value: 'coco', label: 'COCO', description: 'COCO JSON annotations' },
    { value: 'binary', label: 'Binary Mask', description: 'images/ and masks/ folders' },
];

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

const CVTrainConfig: React.FC<CVTrainConfigProps> = ({ initialData, onSave }) => {
    const [training, setTraining] = useState(false);
    const [trainResult, setTrainResult] = useState<{ ok: boolean; data: unknown } | null>(null);
    const [s3Configured, setS3Configured] = useState(false);
    const [cvServiceAlive, setCvServiceAlive] = useState<boolean | null>(null);

    // Form state - Task & Model
    const [taskType, setTaskType] = useState<'classification' | 'detection' | 'segmentation'>(
        (initialData.task_type as 'classification' | 'detection' | 'segmentation') || 'classification'
    );
    const [modelName, setModelName] = useState<string>((initialData.model_name as string) || 'resnet');
    const [datasetPath, setDatasetPath] = useState<string>((initialData.dataset_path as string) || '');
    const [datasetFormat, setDatasetFormat] = useState<string>((initialData.dataset_format as string) || 'imagefolder');

    // Training parameters
    const [epochs, setEpochs] = useState<number>((initialData.epochs as number) || 10);
    const [imageSize, setImageSize] = useState<number>((initialData.image_size as number) || 224);
    const [batchSize, setBatchSize] = useState<number>((initialData.batch_size as number) || 32);
    const [learningRate, setLearningRate] = useState<number>((initialData.learning_rate as number) || 0.001);
    const [optimizer, setOptimizer] = useState<string>((initialData.optimizer as string) || 'adam');

    // Data split
    const [trainPct, setTrainPct] = useState<number>((initialData.train_pct as number) || 0.7);
    const [valPct, setValPct] = useState<number>((initialData.val_pct as number) || 0.15);
    const [testPct, setTestPct] = useState<number>((initialData.test_pct as number) || 0.15);

    // Save options
    const [saveLocal, setSaveLocal] = useState<boolean>((initialData.save_local as boolean) ?? true);
    const [uploadToS3, setUploadToS3] = useState<boolean>((initialData.upload_to_s3 as boolean) ?? false);
    const [s3ModelPath, setS3ModelPath] = useState<string>((initialData.s3_model_path as string) || '');
    const [customModelName, setCustomModelName] = useState<string>((initialData.custom_model_name as string) || '');

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
    }, []);

    // Update model when task changes
    useEffect(() => {
        const defaultModel = CV_TASKS[taskType]?.[0]?.value || '';
        if (!CV_TASKS[taskType]?.find(m => m.value === modelName)) {
            setModelName(defaultModel);
        }
        // Update image size based on task
        if (taskType === 'segmentation') {
            setImageSize(256);
        } else {
            setImageSize(224);
        }
    }, [taskType]);

    const handleTrain = async () => {
        if (!datasetPath) {
            alert('Please specify the dataset path');
            return;
        }

        setTraining(true);
        setTrainResult(null);

        try {
            const result = await api<{ status: string; model_saved_at: string; s3_path?: string }>('/api/cv/train', {
                method: 'POST',
                body: {
                    task: taskType,
                    model: modelName,
                    optimizer,
                    dataset_path: datasetPath,
                    dataset_format: datasetFormat,
                    epochs,
                    image_size: imageSize,
                    batch_size: batchSize,
                    learning_rate: learningRate,
                    train_pct: trainPct,
                    val_pct: valPct,
                    test_pct: testPct,
                    save_local: saveLocal,
                    upload_to_s3: uploadToS3,
                    s3_model_path: s3ModelPath,
                    custom_model_name: customModelName,
                },
            });

            setTrainResult({ ok: true, data: result });
        } catch (err) {
            setTrainResult({ ok: false, data: { error: (err as Error).message } });
        } finally {
            setTraining(false);
        }
    };

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
                    ? 'CV Training Service Online'
                    : 'CV Training Service Offline - Start with python main.py'}
            </div>

            {/* ── Task Type ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
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
                                    ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-300'
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

            {/* ── Model & Dataset ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
                    <Cpu className="w-4 h-4" />
                    Model Configuration
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
                                        {m.label} - {m.description}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>

                    <Field label="Dataset Path" hint="Absolute path to your dataset folder">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="/path/to/dataset"
                                value={datasetPath}
                                onChange={(e) => setDatasetPath(e.target.value)}
                            />
                            <button
                                type="button"
                                className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-xl transition-colors"
                                title="Browse (not supported in browser)"
                            >
                                <FolderOpen className="w-4 h-4 text-slate-300" />
                            </button>
                        </div>
                    </Field>

                    <Field label="Dataset Format">
                        <div className="relative">
                            <select
                                value={datasetFormat}
                                onChange={(e) => setDatasetFormat(e.target.value)}
                                className={`${inputClass} appearance-none pr-8`}
                            >
                                {DATASET_FORMATS.map((f) => (
                                    <option key={f.value} value={f.value}>
                                        {f.label} - {f.description}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>

                    <Field label="Custom Model Name" hint="Optional name for the saved model">
                        <input
                            type="text"
                            className={inputClass}
                            placeholder="my_cv_model"
                            value={customModelName}
                            onChange={(e) => setCustomModelName(e.target.value)}
                        />
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Training Parameters ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
                    <Settings className="w-4 h-4" />
                    Training Parameters
                </h3>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Epochs">
                            <input
                                type="number"
                                min="1"
                                max="1000"
                                value={epochs}
                                onChange={(e) => setEpochs(parseInt(e.target.value) || 10)}
                                className={inputClass}
                            />
                        </Field>
                        <Field label="Image Size">
                            <input
                                type="number"
                                min="32"
                                max="1024"
                                step="32"
                                value={imageSize}
                                onChange={(e) => setImageSize(parseInt(e.target.value) || 224)}
                                className={inputClass}
                            />
                        </Field>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Batch Size">
                            <input
                                type="number"
                                min="1"
                                max="256"
                                value={batchSize}
                                onChange={(e) => setBatchSize(parseInt(e.target.value) || 32)}
                                className={inputClass}
                            />
                        </Field>
                        <Field label="Learning Rate">
                            <input
                                type="number"
                                min="0.00001"
                                max="1"
                                step="0.0001"
                                value={learningRate}
                                onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0.001)}
                                className={inputClass}
                            />
                        </Field>
                    </div>

                    <Field label="Optimizer">
                        <div className="relative">
                            <select
                                value={optimizer}
                                onChange={(e) => setOptimizer(e.target.value)}
                                className={`${inputClass} appearance-none pr-8`}
                            >
                                {OPTIMIZERS.map((o) => (
                                    <option key={o.value} value={o.value}>
                                        {o.label} - {o.description}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </Field>

                    <Field label="Train / Validation / Test Split">
                        <div className="grid grid-cols-3 gap-2">
                            <div>
                                <input
                                    type="number"
                                    min="0.1"
                                    max="0.9"
                                    step="0.05"
                                    value={trainPct}
                                    onChange={(e) => setTrainPct(parseFloat(e.target.value))}
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
                                    value={valPct}
                                    onChange={(e) => setValPct(parseFloat(e.target.value))}
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
                                    value={testPct}
                                    onChange={(e) => setTestPct(parseFloat(e.target.value))}
                                    className={`${inputClass} text-center text-xs`}
                                />
                                <p className="text-xs text-slate-500 text-center mt-1">Test</p>
                            </div>
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Save Options ── */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
                    Save Options
                </h3>

                <div className="space-y-3">
                    <label className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-xl hover:bg-slate-800/60 cursor-pointer transition-colors">
                        <input
                            type="checkbox"
                            checked={saveLocal}
                            onChange={(e) => setSaveLocal(e.target.checked)}
                            className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500"
                        />
                        <HardDrive className="w-4 h-4 text-slate-400" />
                        <div>
                            <span className="text-sm text-slate-300">Save Locally</span>
                            <p className="text-xs text-slate-500">Save model to local filesystem</p>
                        </div>
                    </label>

                    <label className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors ${
                        s3Configured
                            ? 'bg-slate-800/40 hover:bg-slate-800/60'
                            : 'bg-slate-800/20 opacity-60 cursor-not-allowed'
                    }`}>
                        <input
                            type="checkbox"
                            checked={uploadToS3}
                            onChange={(e) => setUploadToS3(e.target.checked)}
                            disabled={!s3Configured}
                            className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500"
                        />
                        <Cloud className="w-4 h-4 text-slate-400" />
                        <div>
                            <span className="text-sm text-slate-300">Upload to S3</span>
                            <p className="text-xs text-slate-500">
                                {s3Configured
                                    ? 'Upload model to configured S3 bucket'
                                    : 'Configure S3 credentials first'}
                            </p>
                        </div>
                    </label>

                    {uploadToS3 && s3Configured && (
                        <Field label="S3 Model Path" hint="Path within the bucket (e.g., models/cv/)">
                            <input
                                type="text"
                                className={inputClass}
                                placeholder="models/cv/"
                                value={s3ModelPath}
                                onChange={(e) => setS3ModelPath(e.target.value)}
                            />
                        </Field>
                    )}
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* ── Train & Results ── */}
            <section className="space-y-3">
                <button
                    type="button"
                    onClick={handleTrain}
                    disabled={training || !datasetPath || !cvServiceAlive}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                    {training ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {training ? 'Training...' : 'Start Training'}
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
                        model_name: modelName,
                        dataset_path: datasetPath,
                        dataset_format: datasetFormat,
                        epochs,
                        image_size: imageSize,
                        batch_size: batchSize,
                        learning_rate: learningRate,
                        optimizer,
                        train_pct: trainPct,
                        val_pct: valPct,
                        test_pct: testPct,
                        save_local: saveLocal,
                        upload_to_s3: uploadToS3,
                        s3_model_path: s3ModelPath,
                        custom_model_name: customModelName,
                    })}
                    className="w-full py-3 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-600 hover:from-cyan-600 hover:via-blue-600 hover:to-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" />
                    Save Configuration
                </button>
            </section>
        </div>
    );
};

export default CVTrainConfig;
