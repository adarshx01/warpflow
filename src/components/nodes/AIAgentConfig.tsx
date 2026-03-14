import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Key, Loader2, ShieldCheck, RotateCcw } from 'lucide-react';
import { api } from '../../lib/api';
import { checkSecretExists, setSecret, deleteSecret, type SecretKey } from '../../lib/secrets';

type Provider = 'gemini' | 'openai';

interface ModelInfo {
  id: string;
  name: string;
  description: string;
}

interface AIAgentConfigProps {
  initialData: Record<string, unknown>;
  onSave: (data: Record<string, unknown>) => void;
}

const inputClass =
  'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/50 focus:border-fuchsia-500/50 transition-all';

const providerSecretKey = (provider: Provider): SecretKey =>
  provider === 'openai' ? 'agent_openai_api_key' : 'agent_gemini_api_key';

const AIAgentConfig: React.FC<AIAgentConfigProps> = ({ initialData, onSave }) => {
  const [provider, setProvider] = useState<Provider>((initialData.aiProvider as Provider) ?? 'gemini');
  const [model, setModel] = useState((initialData.aiModel as string) ?? '');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);

  // API key state — the actual value never leaves the backend after being saved once
  const [keyExists, setKeyExists] = useState(false);
  const [newKey, setNewKey] = useState('');       // input when adding / resetting a key
  const [enteringKey, setEnteringKey] = useState(false); // show the input field?

  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);

  const providerName = useMemo(() => (provider === 'openai' ? 'OpenAI' : 'Gemini'), [provider]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setStatus(null);
    setNewKey('');
    setEnteringKey(false);

    (async () => {
      try {
        const [modelList, exists] = await Promise.all([
          api<ModelInfo[]>(`/api/${provider}/models`).catch(() => [] as ModelInfo[]),
          checkSecretExists(providerSecretKey(provider)),
        ]);

        if (!mounted) return;
        setModels(modelList);
        setKeyExists(exists);

        // If no key is saved yet, show the input so the user can add one right away
        if (!exists) setEnteringKey(true);

        const initialModel = (initialData.aiModel as string) ?? '';
        if (initialModel && modelList.some((m) => m.id === initialModel)) {
          setModel(initialModel);
        } else if (modelList.length > 0) {
          setModel(modelList[0].id);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => { mounted = false; };
  }, [provider, initialData.aiModel]);

  const handleSaveKey = async () => {
    if (!newKey.trim()) return;
    setSaving(true);
    setStatus(null);
    try {
      await setSecret(providerSecretKey(provider), newKey.trim());
      setKeyExists(true);
      setEnteringKey(false);
      setNewKey('');
      setStatus({ ok: true, message: 'API key saved securely on the server.' });
    } catch (err) {
      setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to save API key' });
    } finally {
      setSaving(false);
    }
  };

  const handleResetKey = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await deleteSecret(providerSecretKey(provider));
      setKeyExists(false);
      setEnteringKey(true);
      setNewKey('');
      setStatus({ ok: true, message: 'API key removed. Enter a new key below.' });
    } catch (err) {
      setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to remove API key' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    setStatus(null);
    try {
      onSave({ aiProvider: provider, aiModel: model });
      setStatus({ ok: true, message: 'Agent configuration saved.' });
    } catch (err) {
      setStatus({ ok: false, message: err instanceof Error ? err.message : 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Provider */}
      <section className="space-y-4">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Agent Provider</h3>
        <div className="relative">
          <select
            className={`${inputClass} appearance-none pr-8`}
            value={provider}
            onChange={(e) => setProvider(e.target.value as Provider)}
          >
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>
      </section>

      {/* Model */}
      <section className="space-y-4">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Agent Model</h3>
        <div className="relative">
          <select
            className={`${inputClass} appearance-none pr-8`}
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={loading}
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
            {models.length === 0 && <option value="">Loading models...</option>}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>
      </section>

      {/* API Key — value NEVER shown after save, only existence status */}
      <section className="space-y-3">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Agent API Key</h3>

        {keyExists && !enteringKey ? (
          <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
            <div className="flex items-center gap-2 text-emerald-300 text-sm">
              <ShieldCheck className="w-4 h-4" />
              <span>{providerName} API key is saved securely</span>
            </div>
            <button
              type="button"
              onClick={handleResetKey}
              disabled={saving}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-500/10"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                className={`${inputClass} pl-9`}
                placeholder={`Paste your ${providerName} API key`}
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSaveKey}
                disabled={saving || !newKey.trim()}
                className="flex-1 py-2 bg-fuchsia-600 hover:bg-fuchsia-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                Save API Key
              </button>
              {keyExists && (
                <button
                  type="button"
                  onClick={() => { setEnteringKey(false); setNewKey(''); }}
                  className="px-3 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors rounded-xl hover:bg-slate-700/40"
                >
                  Cancel
                </button>
              )}
            </div>
            <p className="text-xs text-slate-500">
              The key is encrypted and stored on the server. It will never be sent back to your browser.
            </p>
          </div>
        )}
      </section>

      {/* Status */}
      {status && (
        <div className={`p-3 rounded-xl border text-sm flex items-center gap-2 ${status.ok ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
          {status.ok ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {status.message}
        </div>
      )}

      {/* Save Config */}
      <button
        type="button"
        onClick={handleSaveConfig}
        disabled={saving || loading || !model}
        className="w-full py-3 bg-gradient-to-r from-purple-500 via-fuchsia-500 to-pink-500 hover:from-purple-600 hover:via-fuchsia-600 hover:to-pink-600 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Save Agent Configuration
      </button>
    </div>
  );
};

export default AIAgentConfig;

