import React, { useState } from 'react';
import { CheckCircle2, Zap, FileJson } from 'lucide-react';

interface ManualTriggerConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const ManualTriggerConfig: React.FC<ManualTriggerConfigProps> = ({ initialData, onSave }) => {
    // We default to empty JSON object string if there's no payload yet
    const defaultPayload = initialData.payload 
        ? JSON.stringify(initialData.payload, null, 2) 
        : '{\n  \n}';
        
    const [payloadStr, setPayloadStr] = useState<string>(defaultPayload);
    const [error, setError] = useState<string | null>(null);

    const handleSave = () => {
        let payload = {};
        if (payloadStr.trim() !== '') {
            try {
                payload = JSON.parse(payloadStr);
                setError(null);
            } catch (err) {
                setError('Invalid JSON payload');
                return; // Stop save if invalid JSON
            }
        }
        onSave({ payload });
    };

    return (
        <div className="space-y-6">
            <section className="flex flex-col items-center justify-center p-6 text-center bg-slate-800/50 rounded-2xl border border-slate-700/50">
                <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 via-orange-400 to-red-500 rounded-full flex items-center justify-center text-white mb-4 shadow-lg shadow-orange-500/20">
                    <Zap className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-slate-200 mb-2">Manual Trigger</h3>
                <p className="text-sm text-slate-400">
                    Click the "Run Workflow" button in the top bar to execute this flow immediately.
                </p>
                <p className="text-xs text-slate-500 mt-4">
                    Once the workflow is saved, you can also trigger it via the external API shortcut on your phone.
                </p>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-yellow-400 to-orange-500 rounded-full" />Test Payload
                </h3>
                <p className="text-xs text-slate-500 mb-3">
                    Optionally define a JSON payload to simulate incoming data when running manually.
                </p>
                <div className="relative">
                    <FileJson className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                    <textarea
                        className={`w-full h-32 pl-9 pr-3.5 py-2.5 bg-slate-800/80 border ${error ? 'border-red-500/50 focus:ring-red-500/50' : 'border-slate-700/60 focus:ring-yellow-500/50 focus:border-yellow-500/50'} rounded-xl text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all resize-y`}
                        placeholder={'{\n  "key": "value"\n}'}
                        value={payloadStr}
                        onChange={(e) => {
                            setPayloadStr(e.target.value);
                            if (error) setError(null);
                        }}
                    />
                </div>
                {error && <p className="text-xs text-red-400 mt-2 flex items-center gap-1"><span>⚠️</span> {error}</p>}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <button 
                    type="button" 
                    onClick={handleSave}
                    className="w-full py-3 bg-gradient-to-r from-yellow-500 via-orange-500 to-red-500 hover:from-yellow-600 hover:via-orange-600 hover:to-red-600 text-white font-bold rounded-xl shadow-lg shadow-orange-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default ManualTriggerConfig;
