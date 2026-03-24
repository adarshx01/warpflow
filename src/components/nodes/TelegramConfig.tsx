import React, { useState } from 'react';
import { CheckCircle2, Key, Hash, Info } from 'lucide-react';

interface TelegramConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

const TELEGRAM_OPERATIONS = [
    { group: 'Messaging', ops: ['Send Message', 'Edit Message', 'Delete Message', 'Forward Message', 'Copy Message', 'Pin Message', 'Unpin Message'] },
    { group: 'Media', ops: ['Send Photo', 'Send Document', 'Send Audio', 'Send Video', 'Send Animation', 'Send Sticker', 'Send Location', 'Send Poll'] },
    { group: 'Chat Management', ops: ['Get Chat', 'Get Member Count', 'Get Member', 'Ban Member', 'Unban Member', 'Restrict Member', 'Promote Member', 'Set Title', 'Set Description', 'Leave Chat', 'Export Invite Link'] },
    { group: 'Bot Info', ops: ['Get Me', 'Get Commands', 'Set Commands'] },
    { group: 'Files', ops: ['Get File (+ Download URL)'] },
    { group: 'Webhooks', ops: ['Set Webhook', 'Delete Webhook', 'Get Webhook Info'] },
    { group: 'Callbacks', ops: ['Answer Callback Query'] },
];

const TelegramConfig: React.FC<TelegramConfigProps> = ({ initialData, onSave }) => {
    const [botToken, setBotToken] = useState((initialData.botToken as string) || '');
    const [defaultChatId, setDefaultChatId] = useState((initialData.defaultChatId as string) || '');
    const [showCapabilities, setShowCapabilities] = useState(false);

    return (
        <div className="space-y-6">
            {/* Auth */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-sky-400 to-blue-500 rounded-full" />
                    Authentication
                </h3>
                <div className="space-y-4">
                    <Field
                        label="Bot Token"
                        hint="Get this from @BotFather on Telegram → /newbot. Format: 123456789:ABCDefGhIJKlmN..."
                    >
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9 font-mono`}
                                placeholder="123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ"
                                value={botToken}
                                onChange={(e) => setBotToken(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                    </Field>

                    <Field
                        label="Default Chat ID"
                        hint="The chat, group, or channel your bot should target by default. Get it via @userinfobot or from the Telegram API."
                    >
                        <div className="relative">
                            <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="-1001234567890 or @mychannel"
                                value={defaultChatId}
                                onChange={(e) => setDefaultChatId(e.target.value)}
                            />
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Setup guide */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />
                    Quick Setup
                </h3>
                <ol className="space-y-2 text-xs text-slate-400">
                    <li className="flex gap-2"><span className="text-sky-400 font-bold">1.</span>Open Telegram → search <span className="text-sky-300 font-mono">@BotFather</span></li>
                    <li className="flex gap-2"><span className="text-sky-400 font-bold">2.</span>Send <span className="text-sky-300 font-mono">/newbot</span> → choose a name and username</li>
                    <li className="flex gap-2"><span className="text-sky-400 font-bold">3.</span>Copy the bot token and paste it above</li>
                    <li className="flex gap-2"><span className="text-sky-400 font-bold">4.</span>Add your bot to the target chat as <span className="text-sky-300">Administrator</span></li>
                    <li className="flex gap-2"><span className="text-sky-400 font-bold">5.</span>Get your Chat ID from <span className="text-sky-300 font-mono">@userinfobot</span> or Telegram Web URL</li>
                </ol>
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
                        {TELEGRAM_OPERATIONS.map(({ group, ops }) => (
                            <div key={group}>
                                <p className="text-xs font-bold text-slate-500 uppercase mb-1">{group}</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {ops.map(op => (
                                        <span key={op} className="text-xs px-2 py-0.5 bg-sky-500/10 border border-sky-500/20 text-sky-300 rounded-lg">
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
                    onClick={() => onSave({ botToken, defaultChatId })}
                    disabled={!botToken.trim()}
                    className="w-full py-3 bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-500 hover:from-sky-600 hover:via-blue-600 hover:to-indigo-600 disabled:opacity-40 text-white font-bold rounded-xl shadow-lg shadow-sky-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default TelegramConfig;
