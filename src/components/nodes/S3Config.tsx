import React, { useState } from 'react';
import { CheckCircle2, Key, Database, Globe, Info, ChevronDown } from 'lucide-react';

interface S3ConfigProps {
    initialData: Record<string, unknown>;
    onSave: (data: Record<string, unknown>) => void;
}

const inputClass = 'w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all';
const labelClass = 'block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider';

const AWS_REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1', 'eu-north-1', 'eu-south-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
    'ap-south-1', 'ap-east-1', 'sa-east-1', 'ca-central-1', 'me-south-1', 'af-south-1',
];

const S3_OPERATIONS = [
    { group: 'Objects', ops: ['Upload Text/File', 'Download as Text', 'Delete Object', 'Copy Object', 'Move Object', 'Get Object Metadata'] },
    { group: 'Listing', ops: ['List Objects (with prefix)', 'List All Buckets'] },
    { group: 'Presigned URLs', ops: ['Generate Presigned GET URL', 'Generate Presigned POST (upload)'] },
    { group: 'Bucket Management', ops: ['Create Bucket', 'Delete Bucket', 'Get Bucket Location'] },
    { group: 'Access Control', ops: ['Get Object ACL', 'Set Object ACL (private/public-read)'] },
    { group: 'Versioning', ops: ['Get Versioning Status', 'Enable/Suspend Versioning', 'List Object Versions'] },
    { group: 'Tags', ops: ['Get Object Tags', 'Set Object Tags', 'Delete Object Tags'] },
    { group: 'Static Website', ops: ['Configure Website Hosting', 'Get Website Config', 'Remove Website Config'] },
];

const S3Config: React.FC<S3ConfigProps> = ({ initialData, onSave }) => {
    const [accessKey, setAccessKey] = useState((initialData.accessKey as string) || '');
    const [secretKey, setSecretKey] = useState((initialData.secretKey as string) || '');
    const [defaultBucket, setDefaultBucket] = useState((initialData.defaultBucket as string) || '');
    const [region, setRegion] = useState((initialData.region as string) || 'us-east-1');
    const [showCapabilities, setShowCapabilities] = useState(false);

    return (
        <div className="space-y-6">
            {/* Auth */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-orange-400 to-amber-500 rounded-full" />
                    AWS Credentials
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className={labelClass}>Access Key ID</label>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9 font-mono`}
                                placeholder="AKIAIOSFODNN7EXAMPLE"
                                value={accessKey}
                                onChange={(e) => setAccessKey(e.target.value)}
                                autoComplete="off"
                            />
                        </div>
                    </div>

                    <div>
                        <label className={labelClass}>Secret Access Key</label>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="password"
                                className={`${inputClass} pl-9 font-mono`}
                                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                                value={secretKey}
                                onChange={(e) => setSecretKey(e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>
                        <p className="text-xs text-slate-500 mt-1.5">
                            Create an IAM user in AWS Console → attach <span className="text-orange-400 font-mono">AmazonS3FullAccess</span> policy
                        </p>
                    </div>

                    <div>
                        <label className={labelClass}>Default Bucket</label>
                        <div className="relative">
                            <Database className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                className={`${inputClass} pl-9`}
                                placeholder="my-warpflow-bucket"
                                value={defaultBucket}
                                onChange={(e) => setDefaultBucket(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <label className={labelClass}>AWS Region</label>
                        <div className="relative">
                            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <select
                                className={`${inputClass} pl-9 appearance-none cursor-pointer`}
                                value={region}
                                onChange={(e) => setRegion(e.target.value)}
                            >
                                {AWS_REGIONS.map(r => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                        </div>
                    </div>
                </div>
            </section>

            <div className="h-px bg-slate-700/50" />

            {/* Quick Setup */}
            <section>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-amber-400 to-yellow-500 rounded-full" />
                    Quick Setup
                </h3>
                <ol className="space-y-2 text-xs text-slate-400">
                    <li className="flex gap-2"><span className="text-orange-400 font-bold">1.</span>Go to <span className="text-orange-300">AWS Console → IAM → Users → Create User</span></li>
                    <li className="flex gap-2"><span className="text-orange-400 font-bold">2.</span>Attach permission: <span className="text-orange-300 font-mono">AmazonS3FullAccess</span></li>
                    <li className="flex gap-2"><span className="text-orange-400 font-bold">3.</span>Create Access Key → choose <span className="text-orange-300">Application running outside AWS</span></li>
                    <li className="flex gap-2"><span className="text-orange-400 font-bold">4.</span>Copy the Access Key ID and Secret, paste them above</li>
                    <li className="flex gap-2"><span className="text-orange-400 font-bold">5.</span>Create or choose a bucket in the same region</li>
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
                        {S3_OPERATIONS.map(({ group, ops }) => (
                            <div key={group}>
                                <p className="text-xs font-bold text-slate-500 uppercase mb-1">{group}</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {ops.map(op => (
                                        <span key={op} className="text-xs px-2 py-0.5 bg-orange-500/10 border border-orange-500/20 text-orange-300 rounded-lg">
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
                    onClick={() => onSave({ accessKey, secretKey, defaultBucket, region })}
                    disabled={!accessKey.trim() || !secretKey.trim()}
                    className="w-full py-3 bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-500 hover:from-orange-600 hover:via-amber-600 hover:to-yellow-600 disabled:opacity-40 text-white font-bold rounded-xl shadow-lg shadow-orange-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                >
                    <CheckCircle2 className="w-5 h-5" /> Save Configuration
                </button>
            </section>
        </div>
    );
};

export default S3Config;
