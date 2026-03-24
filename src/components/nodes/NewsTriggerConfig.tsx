import React, { useState } from 'react';
import { CheckCircle2, Search, Globe, Newspaper, ExternalLink } from 'lucide-react';

interface NewsTriggerConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
    <div>
        <label className={labelClass}>{label}</label>
        {children}
        {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
);

interface Article {
    title: string;
    url: string;
    source: string;
    published: string;
}

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const NewsTriggerConfig: React.FC<NewsTriggerConfigProps> = ({ initialData, onSave }) => {
    const [query, setQuery] = useState((initialData.query as string) || '');
    const [language, setLanguage] = useState((initialData.language as string) || 'en');

    const [articles, setArticles] = useState<Article[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleTestSearch = async () => {
        const trimmed = query.trim();
        if (!trimmed) {
            setError('Please enter a search query first.');
            setArticles([]);
            return;
        }

        setLoading(true);
        setError(null);
        setArticles([]);

        try {
            const res = await fetch(
                `${BACKEND_URL}/api/news/preview?q=${encodeURIComponent(trimmed)}&lang=${encodeURIComponent(language)}`
            );
            if (!res.ok) throw new Error(`Server returned ${res.status}`);
            const data = await res.json();
            if (!data.articles || data.articles.length === 0) {
                setError('No articles found for this query. Try a different keyword.');
            } else {
                setArticles(data.articles);
            }
        } catch (e: any) {
            setError(`Failed to fetch news: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-full" />News Tracking Setup
                </h3>
                <div className="space-y-4">
                    <Field label="Search Query" hint='Keywords to track (e.g. "OpenAI" OR "Anthropic funding")'>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="e.g. AI startup funding"
                                value={query}
                                onChange={(e) => {
                                    setQuery(e.target.value);
                                    setArticles([]);
                                    setError(null);
                                }}
                            />
                        </div>
                    </Field>

                    <Field label="Language/Region" hint="Two-letter language code (default: en)">
                        <div className="relative">
                            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9 font-mono uppercase`}
                                placeholder="en"
                                maxLength={2}
                                value={language}
                                onChange={(e) => setLanguage(e.target.value.toLowerCase())}
                            />
                        </div>
                    </Field>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Live Test Section */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-indigo-400 to-purple-500 rounded-full" />Live Preview
                </h3>
                <p className="text-xs text-slate-500 mb-3">
                    Fetch real headlines from Google News to verify your query before saving.
                </p>

                <button
                    onClick={handleTestSearch}
                    disabled={loading}
                    className="w-full px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mb-3"
                >
                    <Newspaper className="w-4 h-4" />
                    {loading ? 'Fetching live headlines...' : 'Fetch Live Headlines'}
                </button>

                {error && (
                    <div className="text-xs font-medium text-red-400 p-3 rounded-lg bg-slate-800 border border-red-500/30 mb-3">
                        {error}
                    </div>
                )}

                {articles.length > 0 && (
                    <div className="space-y-2">
                        {articles.map((article, i) => (
                            <a
                                key={i}
                                href={article.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-start gap-3 p-3 bg-slate-800/80 border border-slate-700/50 hover:border-blue-500/40 rounded-xl transition-all group"
                            >
                                <div className="flex-1 min-w-0">
                                    <p className="text-xs font-semibold text-slate-100 group-hover:text-blue-300 transition-colors leading-snug">
                                        {article.title}
                                    </p>
                                    <p className="text-xs text-slate-500 mt-1 truncate">
                                        {article.source}
                                        {article.published ? ` · ${new Date(article.published).toLocaleDateString()} ${new Date(article.published).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}` : ''}
                                    </p>
                                </div>
                                <ExternalLink className="w-3.5 h-3.5 text-slate-600 group-hover:text-blue-400 flex-shrink-0 mt-0.5 transition-colors" />
                            </a>
                        ))}
                    </div>
                )}
            </section>

            <div className="h-px bg-slate-700/50" />

            <section>
                <button
                    type="button"
                    onClick={() => onSave({ query, language })}
                    className="w-full py-3 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 hover:from-blue-600 hover:via-indigo-600 hover:to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default NewsTriggerConfig;
