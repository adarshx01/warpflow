import React, { useState } from 'react';
import { CheckCircle2, Key, Hash, Info } from 'lucide-react';

interface SlackConfigProps {
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

const SLACK_OPERATIONS = [
    { group: 'Messaging', ops: ['Send Message', 'Update Message', 'Delete Message', 'Get Permalink', 'Search Messages'] },
    { group: 'Channels', ops: ['List Channels', 'Get Channel Info', 'Get History', 'Get Thread Replies', 'Create Channel', 'Archive Channel', 'Invite Users'] },
    { group: 'Users', ops: ['List Users', 'Get User Info', 'Lookup by Email', 'Set Status'] },
    { group: 'Reactions', ops: ['Add Reaction', 'Remove Reaction', 'Get Reactions'] },
    { group: 'Files', ops: ['Upload File', 'List Files', 'Delete File'] },
    { group: 'Pins', ops: ['Pin Message', 'Unpin Message', 'List Pins'] },
    { group: 'Workspace', ops: ['Get Workspace Info', 'Get Bot Info', 'Add Reminder'] },
];

const SlackConfig: React.FC<SlackConfigProps> = ({ initialData, onSave }) => {
    const [botToken, setBotToken] = useState((initialData.botToken as string) || '');
    const [defaultChannel, setDefaultChannel] = useState((initialData.defaultChannel as string) || '');
    const [showCapabilities, setShowCapabilities] = useState(false);

    return (
        <div className="space-y-6">
            {/* Auth */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-purple-400 to-fuchsia-500 rounded-full" />Authentication
                </h3>
                <div className="space-y-4">
                    <Field
                        label="Bot Token"
                        hint='Create a Slack App at api.slack.com → OAuth & Permissions → copy the "Bot User OAuth Token" (starts with xoxb-)'
                    >
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9 font-mono`}
                                placeholder="xoxb-..."
                                value={botToken}
                                onChange={(e) => setBotToken(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                    </Field>

                    <Field
                        label="Default Channel (optional)"
                        hint="The AI agent will target this channel by default when not instructed otherwise."
                    >
                        <div className="relative">
                            <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="#general or C012AB3CD"
                                value={defaultChannel}
                                onChange={(e) => setDefaultChannel(e.target.value)}
                            />
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Required Scopes */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-fuchsia-400 to-pink-500 rounded-full" />Required Bot Token Scopes
                </h3>
                <div className="p-3 bg-slate-800/60 border border-slate-700/50 rounded-xl text-xs text-slate-400 font-mono leading-relaxed">
                    channels:read, channels:history, channels:write, groups:read, groups:history,
                    chat:write, chat:write.public, files:write, files:read, reactions:write,
                    reactions:read, pins:write, pins:read, users:read, users:read.email,
                    search:read, team:read, reminders:write
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Capabilities */}
            <section>
                <button
                    type="button"
                    onClick={() => setShowCapabilities(!showCapabilities)}
                    className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider hover:text-slate-200 transition-colors w-full mb-3"
                >
                    <Info className="w-3.5 h-3.5" />
                    {showCapabilities ? 'Hide' : 'Show'} All Available Operations
                </button>
                {showCapabilities && (
                    <div className="space-y-3">
                        {SLACK_OPERATIONS.map(({ group, ops }) => (
                            <div key={group}>
                                <p className="text-xs font-bold text-slate-500 uppercase mb-1">{group}</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {ops.map(op => (
                                        <span key={op} className="text-xs px-2 py-0.5 bg-purple-500/10 border border-purple-500/20 text-purple-300 rounded-lg">
                                            {op}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <button
                    type="button"
                    onClick={() => onSave({ botToken, defaultChannel })}
                    disabled={!botToken.trim()}
                    className="w-full py-3 bg-gradient-to-r from-purple-500 via-fuchsia-500 to-pink-500 hover:from-purple-600 hover:via-fuchsia-600 hover:to-pink-600 disabled:opacity-40 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default SlackConfig;
