import React, { useState, useEffect } from 'react';
import { CheckCircle2, Clock, CalendarDays } from 'lucide-react';

interface ScheduleConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

type PresetType = 'minutes' | 'hourly' | 'daily' | 'weekly' | 'custom';

const presetMap = {
    '*/15 * * * *': 'Every 15 minutes',
    '0 * * * *': 'Every hour',
    '0 9 * * *': 'Every day at 9:00 AM',
    '0 9 * * 1': 'Every Monday at 9:00 AM',
};

const ScheduleConfig: React.FC<ScheduleConfigProps> = ({ initialData, onSave }) => {
    const defaultCron = (initialData.cron as string) || '* * * * *';
    const [cron, setCron] = useState(defaultCron);
    const [mode, setMode] = useState<'preset' | 'custom'>('preset');

    // Auto-detect if current cron is a preset
    useEffect(() => {
        if (cron in presetMap) {
            setMode('preset');
        } else if (cron !== '* * * * *') {
            setMode('custom');
        }
    }, [cron]);

    return (
        <div className="space-y-6">
            <section>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                        <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-purple-500 rounded-full" />Schedule Details
                    </h3>
                    <div className="flex bg-slate-800 rounded-lg p-1 border border-slate-700">
                        <button
                            onClick={() => setMode('preset')}
                            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${mode === 'preset' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Presets
                        </button>
                        <button
                            onClick={() => setMode('custom')}
                            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${mode === 'custom' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Custom
                        </button>
                    </div>
                </div>

                {mode === 'preset' ? (
                    <div className="space-y-3">
                        <Field label="Choose a Schedule">
                            <div className="grid grid-cols-1 gap-2">
                                {Object.entries(presetMap).map(([expr, label]) => (
                                    <button
                                        key={expr}
                                        onClick={() => setCron(expr)}
                                        className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-all ${
                                            cron === expr 
                                                ? 'bg-purple-500/20 border-purple-500 text-purple-100 ring-1 ring-purple-500/50' 
                                                : 'bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
                                        }`}
                                    >
                                        <CalendarDays className={`w-4 h-4 ${cron === expr ? 'text-purple-400' : 'text-slate-500'}`} />
                                        <span className="text-sm font-medium">{label}</span>
                                    </button>
                                ))}
                            </div>
                        </Field>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <Field label="Cron Expression" hint="format: minute hour day month day_of_week">
                            <div className="relative">
                                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    className={`${inputClass} pl-9 font-mono`}
                                    placeholder="0 9 * * *"
                                    value={cron}
                                    onChange={(e) => setCron(e.target.value)}
                                />
                            </div>
                        </Field>
                    </div>
                )}
                
                <div className="mt-4 p-4 bg-[#0d1117] rounded-xl border border-slate-700/50 flex flex-col items-center">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">Raw Expression</span>
                    <span className="text-lg font-mono text-purple-400 tracking-wider bg-purple-500/10 px-3 py-1 rounded-lg border border-purple-500/20">{cron}</span>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <button 
                    type="button" 
                    onClick={() => onSave({ cron })}
                    className="w-full py-3 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 hover:from-blue-600 hover:via-indigo-600 hover:to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default ScheduleConfig;
