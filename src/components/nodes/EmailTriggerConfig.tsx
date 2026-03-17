import React, { useState } from 'react';
import { CheckCircle2, Mail, Type, Users, FlaskConical } from 'lucide-react';

interface EmailTriggerConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const EmailTriggerConfig: React.FC<EmailTriggerConfigProps> = ({ initialData, onSave }) => {
    const [subjectMatch, setSubjectMatch] = useState((initialData.subjectMatch as string) || '');
    const [bodyMatch, setBodyMatch] = useState((initialData.bodyMatch as string) || '');
    const [senderMatch, setSenderMatch] = useState((initialData.senderMatch as string) || '');
    
    // Testing states
    const [testBody, setTestBody] = useState('');
    const [testResult, setTestResult] = useState<{ matches: boolean; error?: string } | null>(null);

    const handleTestMatch = () => {
        if (!bodyMatch) {
            setTestResult({ matches: true }); // Empty regex matches everything implicitly
            return;
        }
        
        try {
            const regex = new RegExp(bodyMatch, 'i');
            const matches = regex.test(testBody);
            setTestResult({ matches });
        } catch (e) {
            setTestResult({ matches: false, error: 'Invalid Regular Expression' });
        }
    };

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-pink-400 to-rose-500 rounded-full" />Email Matching Rules
                </h3>
                <div className="space-y-4">
                    <Field label="Subject Contains" hint="Trigger only if the subject contains this text (optional)">
                        <div className="relative">
                            <Type className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="e.g. Invoice, Support Ticket"
                                value={subjectMatch}
                                onChange={(e) => setSubjectMatch(e.target.value)}
                            />
                        </div>
                    </Field>

                    <Field label="Body Match (Regex/Keywords)" hint="Trigger only if the body contains specific data you are looking for">
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9 font-mono`}
                                placeholder="e.g. ERROR_CODE_\\d+"
                                value={bodyMatch}
                                onChange={(e) => {
                                    setBodyMatch(e.target.value);
                                    setTestResult(null); // Reset test on change
                                }}
                            />
                        </div>
                    </Field>
                    
                    <Field label="Sender Email (From)" hint="Trigger only if sent from exactly this email (optional)">
                        <div className="relative">
                            <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="hello@example.com"
                                value={senderMatch}
                                onChange={(e) => setSenderMatch(e.target.value)}
                            />
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                 <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-rose-400 to-red-500 rounded-full" />Test Body Match
                </h3>
                <p className="text-xs text-slate-500 mb-3">
                    Paste a sample email body to test if your regex correctly matches it before saving.
                </p>
                <div className="space-y-3">
                    <textarea
                        className="w-full h-24 px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500/50 transition-all resize-y"
                        placeholder="Sample email body text here..."
                        value={testBody}
                        onChange={(e) => {
                            setTestBody(e.target.value);
                            setTestResult(null);
                        }}
                    />
                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleTestMatch}
                            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-2"
                        >
                            <FlaskConical className="w-4 h-4" /> Run Test
                        </button>
                        {testResult && (
                            <div className={`text-xs font-bold px-3 py-1.5 rounded bg-slate-800 border ${
                                testResult.error 
                                    ? 'text-red-400 border-red-500/30' 
                                    : testResult.matches 
                                        ? 'text-emerald-400 border-emerald-500/30' 
                                        : 'text-amber-400 border-amber-500/30'
                            }`}>
                                {testResult.error || (testResult.matches ? '✓ Match Found!' : '✗ No Match')}
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <button 
                    type="button" 
                    onClick={() => onSave({ subjectMatch, bodyMatch, senderMatch })}
                    className="w-full py-3 bg-gradient-to-r from-pink-500 via-rose-500 to-red-500 hover:from-pink-600 hover:via-rose-600 hover:to-red-600 text-white font-bold rounded-xl shadow-lg shadow-pink-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default EmailTriggerConfig;
