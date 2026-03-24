import React from 'react';
import { X } from 'lucide-react';
import GoogleDocsConfig from './nodes/GoogleDocsConfig';
import GoogleDriveConfig from './nodes/GoogleDriveConfig';
import GmailConfig from './nodes/GmailConfig';
import GoogleSheetsConfig from './nodes/GoogleSheetsConfig';
import GoogleFormsConfig from './nodes/GoogleFormsConfig';
import OpenAIConfig from './nodes/OpenAIConfig';
import GeminiConfig from './nodes/GeminiConfig';
import AIAgentConfig from './nodes/AIAgentConfig';
import ContextStoreConfig from './nodes/ContextStoreConfig';
// ML Training nodes
import DataPrepConfig from './nodes/DataPrepConfig';
import SupervisedTrainConfig from './nodes/SupervisedTrainConfig';
import UnsupervisedTrainConfig from './nodes/UnsupervisedTrainConfig';
import ModelInferenceConfig from './nodes/ModelInferenceConfig';
// Computer Vision nodes
import CVTrainConfig from './nodes/CVTrainConfig';
import CVInferenceConfig from './nodes/CVInferenceConfig';
// Communication & Database nodes
import TwilioConfig from './nodes/TwilioConfig';
import ElevenLabsConfig from './nodes/ElevenLabsConfig';
import PostgreSQLConfig from './nodes/PostgreSQLConfig';
// Trigger nodes
import ManualTriggerConfig from './nodes/ManualTriggerConfig';
import ScheduleConfig from './nodes/ScheduleConfig';
import WebhookConfig from './nodes/WebhookConfig';
import EmailTriggerConfig from './nodes/EmailTriggerConfig';
import NewsTriggerConfig from './nodes/NewsTriggerConfig';
// Communication nodes
import SlackConfig from './nodes/SlackConfig';
import TelegramConfig from './nodes/TelegramConfig';
import S3Config from './nodes/S3Config';

interface Node {
    id: string;
    type: string;
    name: string;
    icon: string;
    color: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
}

interface NodeConfigModalProps {
    node: Node | null;
    onClose: () => void;
    onSave: (data: Record<string, unknown>) => void;
}

const NodeConfigModal: React.FC<NodeConfigModalProps> = ({ node, onClose, onSave }) => {
    if (!node) return null;

    const renderConfigPanel = () => {
        const handleSave = (data: Record<string, unknown>) => { onSave(data); onClose(); };
        switch (node.type) {
            case 'google-docs':
                return <GoogleDocsConfig initialData={node.data} onSave={handleSave} />;
            case 'google-drive':
                return <GoogleDriveConfig initialData={node.data} onSave={handleSave} />;
            case 'gmail':
                return <GmailConfig initialData={node.data} onSave={handleSave} />;
            case 'google-sheets':
                return <GoogleSheetsConfig initialData={node.data} onSave={handleSave} />;
            case 'google-forms':
                return <GoogleFormsConfig initialData={node.data} onSave={handleSave} />;
            case 'openai':
                return <OpenAIConfig initialData={node.data} onSave={handleSave} />;
            case 'gemini':
                return <GeminiConfig initialData={node.data} onSave={handleSave} />;
            case 'ai-agent':
                return <AIAgentConfig initialData={node.data} onSave={handleSave} />;
            case 'context-store':
                return <ContextStoreConfig initialData={node.data} onSave={handleSave} />;
            // ML Training nodes
            case 'data-prep':
                return <DataPrepConfig initialData={node.data} onSave={handleSave} />;
            case 'supervised-train':
                return <SupervisedTrainConfig initialData={node.data} onSave={handleSave} />;
            case 'unsupervised-train':
                return <UnsupervisedTrainConfig initialData={node.data} onSave={handleSave} />;
            case 'model-inference':
                return <ModelInferenceConfig initialData={node.data} onSave={handleSave} />;
            // Computer Vision nodes
            case 'cv-train':
                return <CVTrainConfig initialData={node.data} onSave={handleSave} />;
            case 'cv-inference':
                return <CVInferenceConfig initialData={node.data} onSave={handleSave} />;
            // Communication & Database nodes
            case 'twilio':
                return <TwilioConfig initialData={node.data} onSave={handleSave} />;
            case 'elevenlabs':
                return <ElevenLabsConfig initialData={node.data} onSave={handleSave} />;
            case 'postgresql':
                return <PostgreSQLConfig initialData={node.data} onSave={handleSave} />;
            // Trigger nodes
            case 'manual-trigger':
                return <ManualTriggerConfig initialData={node.data} onSave={handleSave} />;
            case 'schedule':
                return <ScheduleConfig initialData={node.data} onSave={handleSave} />;
            case 'webhook':
                return <WebhookConfig initialData={node.data} onSave={handleSave} nodeId={node.id} />;
            case 'email-trigger':
                return <EmailTriggerConfig initialData={node.data} onSave={handleSave} />;
            case 'news-trigger':
                return <NewsTriggerConfig initialData={node.data} onSave={handleSave} />;
            // Communication nodes
            case 'slack':
                return <SlackConfig initialData={node.data} onSave={handleSave} />;
            case 'telegram':
                return <TelegramConfig initialData={node.data} onSave={handleSave} />;
            case 's3':
            case 'aws':
                return <S3Config initialData={node.data} onSave={handleSave} />;
            default:
                return (
                    <div className="flex flex-col items-center justify-center h-48 text-center gap-3">
                        <div className="text-4xl">🔧</div>
                        <p className="text-slate-400 text-sm">
                            No configuration panel available for <span className="text-slate-200 font-medium">{node.name}</span> yet.
                        </p>
                    </div>
                );
        }
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                onClick={onClose}
            />

            {/* Slide-over panel */}
            <div className="fixed right-0 top-0 h-full w-[480px] bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-l border-slate-700/60 shadow-2xl z-50 flex flex-col overflow-hidden">

                {/* Header */}
                <div className="flex-shrink-0 px-6 py-5 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-xl">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${node.color} flex items-center justify-center text-xl shadow-lg ring-2 ring-white/10`}>
                                {node.icon}
                            </div>
                            <div>
                                <h2 className="text-base font-bold text-slate-100">{node.name}</h2>
                                <p className="text-xs text-slate-500 mt-0.5">Node Configuration</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="w-9 h-9 bg-slate-800/80 hover:bg-slate-700 border border-slate-700/50 rounded-xl flex items-center justify-center transition-all hover:scale-105 active:scale-95"
                        >
                            <X className="w-4 h-4 text-slate-400" />
                        </button>
                    </div>
                </div>

                {/* Body — scrollable */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                    {renderConfigPanel()}
                </div>
            </div>
        </>
    );
};

export default NodeConfigModal;
