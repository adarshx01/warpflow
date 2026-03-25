import React, { useState, useEffect } from 'react';
import { FolderOpen, Plus, Trash2, X, Loader2, FileJson, Upload } from 'lucide-react';
import { api } from '../lib/api';

interface WorkflowListItem {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  node_count: number;
  connection_count: number;
  created_at: string;
  updated_at: string;
}

interface WorkflowSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (workflowId: string) => void;
  onNew: () => void;
  onImport: (file: File) => void;
  currentWorkflowId?: string | null;
}

const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({
  isOpen,
  onClose,
  onSelect,
  onNew,
  onImport,
  currentWorkflowId,
}) => {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadWorkflows();
    }
  }, [isOpen]);

  const loadWorkflows = async () => {
    setIsLoading(true);
    try {
      const data = await api<WorkflowListItem[]>('/api/workflows');
      setWorkflows(data);
    } catch (err) {
      console.error('Failed to load workflows:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteWorkflow = async (id: string) => {
    try {
      await api(`/api/workflows/${id}`, { method: 'DELETE' });
      setWorkflows(workflows.filter(w => w.id !== id));
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete workflow:', err);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImport(file);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/50 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <FolderOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">Your Workflows</h2>
              <p className="text-sm text-slate-400">Select a workflow to edit or create a new one</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Actions */}
        <div className="flex gap-3 p-4 border-b border-slate-700/50">
          <button
            onClick={() => { onNew(); onClose(); }}
            className="flex-1 px-4 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-all shadow-lg"
          >
            <Plus className="w-5 h-5" />
            New Workflow
          </button>
          <label className="flex-1 px-4 py-3 bg-slate-700/50 hover:bg-slate-700/80 text-slate-200 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer border border-slate-600/50">
            <Upload className="w-5 h-5" />
            Import JSON
            <input
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>

        {/* Workflow List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
            </div>
          ) : workflows.length === 0 ? (
            <div className="text-center py-12">
              <FileJson className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">No workflows yet</p>
              <p className="text-slate-500 text-sm">Create your first workflow to get started</p>
            </div>
          ) : (
            workflows.map(workflow => (
              <div
                key={workflow.id}
                className={`p-4 rounded-xl border transition-all cursor-pointer group ${
                  currentWorkflowId === workflow.id
                    ? 'bg-cyan-500/10 border-cyan-500/50'
                    : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                }`}
                onClick={() => { onSelect(workflow.id); onClose(); }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-slate-100">{workflow.name}</h3>
                      {workflow.is_active && (
                        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Active
                        </span>
                      )}
                      {currentWorkflowId === workflow.id && (
                        <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 text-xs rounded-full">
                          Current
                        </span>
                      )}
                    </div>
                    {workflow.description && (
                      <p className="text-sm text-slate-400 mt-1">{workflow.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                      <span>{workflow.node_count} nodes</span>
                      <span>{workflow.connection_count} connections</span>
                      <span>Updated {new Date(workflow.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {deleteConfirm === workflow.id ? (
                      <>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteWorkflow(workflow.id); }}
                          className="px-3 py-1.5 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 transition-colors"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }}
                          className="px-3 py-1.5 bg-slate-600 text-white text-sm rounded-lg hover:bg-slate-500 transition-colors"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(workflow.id); }}
                        className="p-2 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-colors"
                        title="Delete workflow"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowSelector;
