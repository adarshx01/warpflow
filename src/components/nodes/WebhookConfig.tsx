import React, { useState } from 'react';
import { CheckCircle2, Copy, Link as LinkIcon, AlertCircle, Key, Terminal } from 'lucide-react';

interface WebhookConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
    nodeId: string;
    flowId?: string; // Will be passed from parent if workflow exists
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const WebhookConfig: React.FC<WebhookConfigProps> = ({ onSave, initialData, flowId }) => {
    // If flowId is provided (workflow is saved), use it. Otherwise, use a placeholder.
    const displayId = flowId || 'SAVE_WORKFLOW_FIRST';
    const webhookUrl = `${window.location.origin}/api/webhooks/${displayId}`;
    
    const [secretToken, setSecretToken] = useState<string>((initialData.secretToken as string) || '');
    const [copiedUrl, setCopiedUrl] = useState(false);
    const [copiedCurl, setCopiedCurl] = useState(false);

    const handleCopy = (text: string, setCopied: React.Dispatch<React.SetStateAction<boolean>>) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const curlCommand = `curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json"${secretToken ? ` \\
  -H "X-WarpCore-Signature: ${secretToken}"` : ''} \\
  -d '{"example_key": "example_value"}'`;

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-teal-500 rounded-full" />Webhook URL
                </h3>
                <div className="space-y-4">
                    <div className="relative">
                        <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            readOnly
                            className={`${inputClass} pl-9 pr-12 font-mono text-xs`}
                            value={webhookUrl}
                        />
                        <button
                            onClick={() => handleCopy(webhookUrl, setCopiedUrl)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-cyan-400 bg-slate-800 rounded-lg transition-colors group"
                            title="Copy URL"
                            disabled={!flowId}
                        >
                            {copiedUrl ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </section>

            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-teal-400 to-emerald-500 rounded-full" />Security
                </h3>
                <Field 
                    label="Secret Token" 
                    hint="If provided, requests must include this token in the 'X-WarpCore-Signature' header to be accepted."
                >
                    <div className="relative">
                        <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            className={`${inputClass} pl-9`}
                            placeholder="e.g. supers3cr3t"
                            value={secretToken}
                            onChange={(e) => setSecretToken(e.target.value)}
                        />
                    </div>
                </Field>
            </section>

            <section>
                 <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-slate-500 to-slate-700 rounded-full" />Example cURL
                </h3>
                <div className="relative bg-[#0d1117] border border-slate-700/50 rounded-xl p-3">
                     <Terminal className="absolute left-3 top-3.5 w-4 h-4 text-slate-500" />
                     <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap pl-8">
                         {curlCommand}
                     </pre>
                     <button
                        onClick={() => handleCopy(curlCommand, setCopiedCurl)}
                        className="absolute right-2 top-2 p-1.5 text-slate-400 hover:text-cyan-400 bg-slate-800/80 rounded-lg transition-colors group"
                        title="Copy cURL"
                        disabled={!flowId}
                    >
                        {copiedCurl ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                </div>
            </section>

            {!flowId && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-blue-300">
                        <strong>Action Required:</strong> You must <strong>save the workflow</strong> first to generate the actual execution URL and use the cURL command.
                    </div>
                </div>
            )}

            <div className="h-px bg-slate-700/50" />

            <section>
                <button 
                    type="button" 
                    onClick={() => onSave({ secretToken })}
                    className="w-full py-3 bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 hover:from-cyan-600 hover:via-teal-600 hover:to-emerald-600 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default WebhookConfig;
