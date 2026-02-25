import React, { useState, useRef, useEffect } from 'react';
import { Plus, Play, Trash2, ZoomIn, ZoomOut, Maximize2, Save, Download, Search, ChevronDown, Grid, Settings, Copy, LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import NodeConfigModal from '../components/NodeConfigModal';

interface NodeType {
  id: string;
  name: string;
  icon: string;
  color: string;
  category: string;
}

interface Node {
  id: string;
  type: string;
  name: string;
  icon: string;
  color: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

interface Connection {
  id: string;
  from: string;
  to: string;
}

const nodeTypes: NodeType[] = [
  // Triggers
  { id: 'manual-trigger', name: 'Manual Trigger', icon: '⚡', color: 'from-yellow-400 via-orange-400 to-red-500', category: 'Triggers' },
  { id: 'schedule', name: 'Schedule', icon: '⏰', color: 'from-blue-400 via-indigo-400 to-purple-500', category: 'Triggers' },
  { id: 'webhook', name: 'Webhook', icon: '🔗', color: 'from-cyan-400 via-teal-400 to-green-500', category: 'Triggers' },
  { id: 'email-trigger', name: 'Email Trigger', icon: '📨', color: 'from-pink-400 via-rose-400 to-red-500', category: 'Triggers' },

  // AI & ML
  { id: 'openai', name: 'OpenAI', icon: '🧠', color: 'from-emerald-400 via-teal-400 to-cyan-500', category: 'AI & ML' },
  { id: 'anthropic', name: 'Anthropic Claude', icon: '🤖', color: 'from-orange-400 via-amber-400 to-yellow-500', category: 'AI & ML' },
  { id: 'huggingface', name: 'HuggingFace', icon: '🤗', color: 'from-yellow-400 via-orange-400 to-amber-500', category: 'AI & ML' },
  { id: 'ai-agent', name: 'AI Agent', icon: '👾', color: 'from-purple-400 via-fuchsia-400 to-pink-500', category: 'AI & ML' },
  { id: 'text-analysis', name: 'Text Analysis', icon: '📝', color: 'from-blue-400 via-cyan-400 to-teal-500', category: 'AI & ML' },
  { id: 'image-gen', name: 'Image Generation', icon: '🎨', color: 'from-pink-400 via-purple-400 to-indigo-500', category: 'AI & ML' },

  // Communication
  { id: 'slack', name: 'Slack', icon: '💬', color: 'from-purple-400 via-pink-400 to-rose-500', category: 'Communication' },
  { id: 'discord', name: 'Discord', icon: '🎮', color: 'from-indigo-400 via-purple-400 to-pink-500', category: 'Communication' },
  { id: 'teams', name: 'Microsoft Teams', icon: '👥', color: 'from-blue-400 via-indigo-400 to-purple-500', category: 'Communication' },
  { id: 'telegram', name: 'Telegram', icon: '✈️', color: 'from-cyan-400 via-blue-400 to-indigo-500', category: 'Communication' },
  { id: 'email', name: 'Email', icon: '📧', color: 'from-red-400 via-pink-400 to-rose-500', category: 'Communication' },
  { id: 'sms', name: 'SMS', icon: '💌', color: 'from-green-400 via-emerald-400 to-teal-500', category: 'Communication' },

  // Data & Storage
  { id: 'postgresql', name: 'PostgreSQL', icon: '🐘', color: 'from-blue-500 via-indigo-500 to-blue-600', category: 'Data & Storage' },
  { id: 'mongodb', name: 'MongoDB', icon: '🍃', color: 'from-green-500 via-emerald-500 to-teal-600', category: 'Data & Storage' },
  { id: 'redis', name: 'Redis', icon: '⚡', color: 'from-red-500 via-orange-500 to-amber-600', category: 'Data & Storage' },
  { id: 'mysql', name: 'MySQL', icon: '🐬', color: 'from-blue-400 via-cyan-400 to-teal-500', category: 'Data & Storage' },
  { id: 'google-sheets', name: 'Google Sheets', icon: '📊', color: 'from-green-400 via-emerald-400 to-green-500', category: 'Data & Storage' },
  { id: 'airtable', name: 'Airtable', icon: '📋', color: 'from-yellow-400 via-orange-400 to-red-500', category: 'Data & Storage' },
  { id: 'csv', name: 'CSV', icon: '📄', color: 'from-slate-400 via-gray-400 to-zinc-500', category: 'Data & Storage' },

  // Logic & Flow
  { id: 'if-condition', name: 'IF Condition', icon: '🔀', color: 'from-amber-400 via-orange-400 to-red-500', category: 'Logic & Flow' },
  { id: 'switch', name: 'Switch', icon: '🔄', color: 'from-purple-400 via-violet-400 to-indigo-500', category: 'Logic & Flow' },
  { id: 'loop', name: 'Loop', icon: '🔁', color: 'from-cyan-400 via-blue-400 to-indigo-500', category: 'Logic & Flow' },
  { id: 'merge', name: 'Merge', icon: '🔗', color: 'from-green-400 via-teal-400 to-cyan-500', category: 'Logic & Flow' },
  { id: 'split', name: 'Split', icon: '✂️', color: 'from-pink-400 via-rose-400 to-red-500', category: 'Logic & Flow' },
  { id: 'wait', name: 'Wait', icon: '⏸️', color: 'from-blue-400 via-indigo-400 to-purple-500', category: 'Logic & Flow' },

  // Data Processing
  { id: 'transform', name: 'Transform Data', icon: '⚙️', color: 'from-teal-400 via-cyan-400 to-blue-500', category: 'Data Processing' },
  { id: 'filter', name: 'Filter', icon: '🔍', color: 'from-indigo-400 via-purple-400 to-pink-500', category: 'Data Processing' },
  { id: 'aggregate', name: 'Aggregate', icon: '📊', color: 'from-orange-400 via-amber-400 to-yellow-500', category: 'Data Processing' },
  { id: 'sort', name: 'Sort', icon: '↕️', color: 'from-green-400 via-emerald-400 to-teal-500', category: 'Data Processing' },
  { id: 'json', name: 'JSON', icon: '{ }', color: 'from-yellow-400 via-amber-400 to-orange-500', category: 'Data Processing' },

  // APIs & Services
  { id: 'http', name: 'HTTP Request', icon: '🌐', color: 'from-green-400 via-emerald-400 to-teal-500', category: 'APIs & Services' },
  { id: 'rest-api', name: 'REST API', icon: '🔌', color: 'from-blue-400 via-cyan-400 to-teal-500', category: 'APIs & Services' },
  { id: 'graphql', name: 'GraphQL', icon: '◆', color: 'from-pink-400 via-fuchsia-400 to-purple-500', category: 'APIs & Services' },
  { id: 'stripe', name: 'Stripe', icon: '💳', color: 'from-indigo-400 via-purple-400 to-violet-500', category: 'APIs & Services' },
  { id: 'github', name: 'GitHub', icon: '🐙', color: 'from-slate-500 via-gray-500 to-zinc-600', category: 'APIs & Services' },
  { id: 'aws', name: 'AWS', icon: '☁️', color: 'from-orange-400 via-amber-400 to-yellow-500', category: 'APIs & Services' },

  // Analytics
  { id: 'google-analytics', name: 'Google Analytics', icon: '📈', color: 'from-orange-400 via-red-400 to-pink-500', category: 'Analytics' },
  { id: 'mixpanel', name: 'Mixpanel', icon: '📊', color: 'from-purple-400 via-fuchsia-400 to-pink-500', category: 'Analytics' },
  { id: 'segment', name: 'Segment', icon: '🎯', color: 'from-green-400 via-emerald-400 to-teal-500', category: 'Analytics' },

  // Google Workspace
  { id: 'google-docs', name: 'Google Docs', icon: '📄', color: 'from-blue-400 via-indigo-400 to-blue-600', category: 'Google Workspace' },
];

const WorkflowBuilder = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<string | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [configNode, setConfigNode] = useState<Node | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const categories = ['All', ...new Set(nodeTypes.map(n => n.category))];

  const filteredNodes = nodeTypes.filter(node => {
    const matchesSearch = node.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || node.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleDragStart = (e: React.DragEvent, type: string) => {
    e.dataTransfer.setData('application/reactflow', type);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();

    const type = e.dataTransfer.getData('application/reactflow');
    if (!type) return;

    const nodeType = nodeTypes.find(n => n.id === type);
    if (!nodeType) return;

    const canvasRect = canvasRef.current?.getBoundingClientRect();
    if (!canvasRect) return;

    // Calculate position relative to the canvas, accounting for zoom and pan
    const x = (e.clientX - canvasRect.left - pan.x * zoom) / zoom;
    const y = (e.clientY - canvasRect.top - pan.y * zoom) / zoom;

    const newNode: Node = {
      id: `node-${Date.now()}`,
      type,
      name: nodeType.name,
      icon: nodeType.icon,
      color: nodeType.color,
      position: { x, y },
      data: {}
    };
    setNodes([...nodes, newNode]);
  };

  const addNode = (type: string) => {
    const nodeType = nodeTypes.find(n => n.id === type);
    if (!nodeType) return;

    const canvasRect = canvasRef.current?.getBoundingClientRect();
    const centerX = canvasRect ? (canvasRect.width / 2 - 100) / zoom - pan.x : 1200;
    const centerY = canvasRect ? (canvasRect.height / 2 - 60) / zoom - pan.y : 200;

    const newNode: Node = {
      id: `node-${Date.now()}`,
      type,
      name: nodeType.name,
      icon: nodeType.icon,
      color: nodeType.color,
      position: { x: centerX, y: centerY + nodes.length * 20 },
      data: {}
    };
    setNodes([...nodes, newNode]);
  };

  const deleteNode = (nodeId: string) => {
    setNodes(nodes.filter(n => n.id !== nodeId));
    setConnections(connections.filter(c => c.from !== nodeId && c.to !== nodeId));
    setSelectedNode(null);
  };

  const updateNodeData = (nodeId: string, data: Record<string, unknown>) => {
    setNodes(nodes.map(n => n.id === nodeId ? { ...n, data } : n));
  };

  const startConnection = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConnecting(nodeId);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setMousePosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
  };

  const endConnection = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (connecting && connecting !== nodeId) {
      // Check if connection already exists
      const connectionExists = connections.some(
        c => (c.from === connecting && c.to === nodeId) || (c.from === nodeId && c.to === connecting)
      );

      if (!connectionExists) {
        const newConnection = {
          id: `conn-${Date.now()}`,
          from: connecting,
          to: nodeId
        };
        setConnections([...connections, newConnection]);
      }
    }
    setConnecting(null);
  };

  const startDrag = (nodeId: string, e: React.MouseEvent) => {
    if (e.target instanceof Element && e.target.closest('.node-control')) return;
    setIsDragging(nodeId);
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;
    setDragStart({
      x: (e.clientX - pan.x * zoom) / zoom - node.position.x,
      y: (e.clientY - pan.y * zoom) / zoom - node.position.y
    });
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.min(Math.max(0.1, zoom * delta), 2);
    setZoom(newZoom);
  };

  const startPan = (e: React.MouseEvent) => {
    if (e.target === canvasRef.current || (e.target instanceof Element && e.target.closest('svg'))) {
      setIsPanning(true);
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  };

  const zoomIn = () => setZoom(Math.min(zoom * 1.2, 2));
  const zoomOut = () => setZoom(Math.max(zoom * 0.8, 0.1));
  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      // Update mouse position for connecting line
      if (connecting) {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect) {
          setMousePosition({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
          });
        }
      }

      if (isDragging && dragStart) {
        const node = nodes.find(n => n.id === isDragging);
        if (node) {
          setNodes(nodes.map(n =>
            n.id === isDragging
              ? { ...n, position: { x: (e.clientX - pan.x * zoom) / zoom - dragStart.x, y: (e.clientY - pan.y * zoom) / zoom - dragStart.y } }
              : n
          ));
        }
      }

      if (isPanning && panStart) {
        const dx = (e.clientX - panStart.x) / zoom;
        const dy = (e.clientY - panStart.y) / zoom;
        setPan({
          x: pan.x + dx,
          y: pan.y + dy
        });
        setPanStart({ x: e.clientX, y: e.clientY });
      }
    };

    const handleUp = () => {
      setIsDragging(null);
      setConnecting(null);
      setIsPanning(false);
    };

    if (isDragging || isPanning || connecting) {
      document.addEventListener('mousemove', handleMove);
      document.addEventListener('mouseup', handleUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
  }, [isDragging, isPanning, connecting, dragStart, panStart, nodes, pan, zoom]);

  const getNodeOutputPosition = (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    return {
      x: (node.position.x + 220) * zoom + pan.x * zoom,
      y: (node.position.y + 111.5) * zoom + pan.y * zoom
    };
  };

  const getNodeInputPosition = (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    return {
      x: node.position.x * zoom + pan.x * zoom,
      y: (node.position.y + 111.5) * zoom + pan.y * zoom
    };
  };

  const runWorkflow = () => {
    setIsRunning(true);
    setTimeout(() => setIsRunning(false), 2000);
  };

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-2xl border-b border-slate-700/50 shadow-2xl shadow-black/20">
        <div className="px-8 py-5 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              {/* <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                <span className="text-white font-bold text-xl">⚡</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
                  WarpFlow Builder
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">Build intelligent automations</p>
              </div> */}
              <img src="/warpflow-logo-small-cropped.png" alt="WarpFlow Logo" className="h-10 filter invert object-contain" />
            </div>

            <div className="flex items-center gap-3 ml-8">
              <button
                onClick={runWorkflow}
                disabled={nodes.length === 0}
                className="group px-6 py-2.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600 text-white rounded-xl font-semibold flex items-center gap-2.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:scale-105 active:scale-95 relative overflow-hidden"
              >
                {isRunning && (
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
                )}
                <div className="relative z-10 flex items-center gap-2.5">
                  {isRunning ? (
                    <div className="relative w-5 h-5">
                      <div className="absolute inset-0 border-3 border-white/30 rounded-full"></div>
                      <div className="absolute inset-0 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                      <div className="absolute inset-0 border-3 border-white/50 border-b-transparent rounded-full animate-spin-reverse"></div>
                    </div>
                  ) : (
                    <div className="relative">
                      <Play className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" fill="currentColor" />
                    </div>
                  )}
                  <span>{isRunning ? 'Running...' : 'Run Workflow'}</span>
                </div>
              </button>

              <button className="px-4 py-2.5 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 rounded-xl font-medium flex items-center gap-2 transition-all border border-slate-700/50 hover:border-slate-600 shadow-lg">
                <Save className="w-4 h-4" />
                Save
              </button>

              <button className="px-4 py-2.5 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 rounded-xl font-medium flex items-center gap-2 transition-all border border-slate-700/50 hover:border-slate-600 shadow-lg">
                <Download className="w-4 h-4" />
                Export
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></div>
                <span className="text-sm text-slate-300 font-medium">{nodes.length}</span>
                <span className="text-xs text-slate-500">nodes</span>
              </div>
              <div className="w-px h-4 bg-slate-700"></div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple-400"></div>
                <span className="text-sm text-slate-300 font-medium">{connections.length}</span>
                <span className="text-xs text-slate-500">connections</span>
              </div>
            </div>

            {/* User info and logout */}
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-medium text-slate-200">{user?.name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2.5 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 rounded-xl font-medium flex items-center gap-2 transition-all border border-slate-700/50 hover:border-slate-600 shadow-lg"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar Toggle Button (when closed) */}
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-6 left-6 z-30 w-11 h-11 bg-slate-800/90 backdrop-blur-xl hover:bg-slate-700/90 border border-slate-700/50 rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-105 active:scale-95"
            title="Open Node Library"
          >
            <PanelLeftOpen className="w-5 h-5 text-slate-300" />
          </button>
        )}

        {/* Sidebar */}
        <div
          className={`bg-gradient-to-b from-slate-900/50 via-slate-900/30 to-slate-900/50 backdrop-blur-xl border-r border-slate-700/50 flex flex-col shadow-2xl transition-all duration-300 ease-in-out z-20 ${isSidebarOpen ? 'w-80 translate-x-0' : 'w-0 -translate-x-full opacity-0 overflow-hidden'
            }`}
        >
          <div className="p-6 border-b border-slate-700/50 flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Grid className="w-4 h-4 text-cyan-400" />
                Node Library
              </h2>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
                title="Close Sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Search */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search nodes..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-800/80 border border-slate-700/50 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
              />
            </div>

            {/* Category Filter */}
            <div className="relative">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700/50 rounded-xl text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all appearance-none cursor-pointer"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {categories.filter(cat => cat !== 'All' && filteredNodes.some(n => n.category === cat)).map(category => {
              const categoryNodes = filteredNodes.filter(n => n.category === category);
              if (categoryNodes.length === 0) return null;

              return (
                <div key={category}>
                  <h3 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider flex items-center gap-2">
                    <div className="w-1 h-4 bg-gradient-to-b from-cyan-400 to-purple-500 rounded-full"></div>
                    {category}
                  </h3>
                  <div className="space-y-2">
                    {categoryNodes.map(node => (
                      <div
                        key={node.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, node.id)}
                        className="w-full p-3.5 bg-gradient-to-br from-slate-800/80 to-slate-800/40 hover:from-slate-700/80 hover:to-slate-700/40 border border-slate-700/50 hover:border-slate-600/80 rounded-xl flex items-center gap-3.5 transition-all group hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl cursor-grab active:cursor-grabbing"
                      >
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${node.color} flex items-center justify-center text-xl group-hover:scale-110 transition-transform shadow-lg ring-2 ring-white/10`}>
                          {node.icon}
                        </div>
                        <div className="flex-1 text-left">
                          <span className="text-sm font-semibold text-slate-100 block">{node.name}</span>
                          <span className="text-xs text-slate-500">{node.category}</span>
                        </div>
                        <button
                          onClick={() => addNode(node.id)}
                          className="p-1.5 hover:bg-slate-600/50 rounded-lg transition-colors"
                          title="Add to canvas"
                        >
                          <Plus className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 relative overflow-hidden">
          {/* Zoom Controls */}
          <div className="absolute top-6 right-6 z-20 flex flex-col gap-2">
            <button
              onClick={zoomIn}
              className="w-11 h-11 bg-slate-800/90 backdrop-blur-xl hover:bg-slate-700/90 border border-slate-700/50 rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-105 active:scale-95"
            >
              <ZoomIn className="w-5 h-5 text-slate-300" />
            </button>
            <button
              onClick={zoomOut}
              className="w-11 h-11 bg-slate-800/90 backdrop-blur-xl hover:bg-slate-700/90 border border-slate-700/50 rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-105 active:scale-95"
            >
              <ZoomOut className="w-5 h-5 text-slate-300" />
            </button>
            <button
              onClick={resetView}
              className="w-11 h-11 bg-slate-800/90 backdrop-blur-xl hover:bg-slate-700/90 border border-slate-700/50 rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-105 active:scale-95"
            >
              <Maximize2 className="w-5 h-5 text-slate-300" />
            </button>
            <div className="w-11 px-2 py-2 bg-slate-800/90 backdrop-blur-xl border border-slate-700/50 rounded-xl text-center">
              <span className="text-xs font-semibold text-slate-300">{Math.round(zoom * 100)}%</span>
            </div>
          </div>

          <div
            ref={canvasRef}
            className="w-full h-full cursor-move"
            onWheel={handleWheel}
            onMouseDown={startPan}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            style={{
              backgroundImage: `radial-gradient(circle, rgba(100, 116, 139, 0.15) 1px, transparent 1px)`,
              backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
              backgroundPosition: `${pan.x * zoom}px ${pan.y * zoom}px`
            }}
          >
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
              <defs>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <linearGradient id="connecting-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" style={{ stopColor: '#06b6d4', stopOpacity: 0.8 }} />
                  <stop offset="50%" style={{ stopColor: '#3b82f6', stopOpacity: 0.8 }} />
                  <stop offset="100%" style={{ stopColor: '#8b5cf6', stopOpacity: 0.8 }} />
                </linearGradient>
              </defs>

              {/* Existing connections */}
              {connections.map(conn => {
                const from = getNodeOutputPosition(conn.from);
                const to = getNodeInputPosition(conn.to);
                const midX = (from.x + to.x) / 2;

                return (
                  <g key={conn.id}>
                    <defs>
                      <linearGradient id={`gradient-${conn.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style={{ stopColor: '#06b6d4', stopOpacity: 0.8 }} />
                        <stop offset="50%" style={{ stopColor: '#3b82f6', stopOpacity: 0.8 }} />
                        <stop offset="100%" style={{ stopColor: '#8b5cf6', stopOpacity: 0.8 }} />
                      </linearGradient>
                    </defs>
                    <path
                      d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                      fill="none"
                      stroke={`url(#gradient-${conn.id})`}
                      strokeWidth="3"
                      filter="url(#glow)"
                    />
                    <circle
                      cx={from.x}
                      cy={from.y}
                      r="5"
                      fill="#06b6d4"
                      className="animate-pulse"
                    />
                    <circle
                      cx={to.x}
                      cy={to.y}
                      r="5"
                      fill="#8b5cf6"
                    />
                  </g>
                );
              })}

              {/* Active connecting line while dragging */}
              {connecting && (
                <g>
                  <path
                    d={`M ${getNodeOutputPosition(connecting).x} ${getNodeOutputPosition(connecting).y} L ${mousePosition.x} ${mousePosition.y}`}
                    fill="none"
                    stroke="url(#connecting-gradient)"
                    strokeWidth="3"
                    strokeDasharray="8 4"
                    filter="url(#glow)"
                    className="animate-pulse"
                  />
                  <circle
                    cx={getNodeOutputPosition(connecting).x}
                    cy={getNodeOutputPosition(connecting).y}
                    r="6"
                    fill="#06b6d4"
                    className="animate-ping"
                  />
                  <circle
                    cx={getNodeOutputPosition(connecting).x}
                    cy={getNodeOutputPosition(connecting).y}
                    r="6"
                    fill="#06b6d4"
                  />
                  <circle
                    cx={mousePosition.x}
                    cy={mousePosition.y}
                    r="6"
                    fill="#8b5cf6"
                    className="animate-pulse"
                  />
                </g>
              )}
            </svg>

            {nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center">
                  <div className="text-8xl mb-6 animate-bounce">🚀</div>
                  <h3 className="text-2xl font-bold text-slate-200 mb-3">Start Building Your Workflow</h3>
                  <p className="text-slate-400 text-lg">Select a node from the sidebar to begin your automation journey</p>
                  <div className="mt-8 flex items-center justify-center gap-4">
                    <div className="px-4 py-2 bg-slate-800/50 rounded-xl border border-slate-700/50 text-sm text-slate-400">
                      Scroll to zoom
                    </div>
                    <div className="px-4 py-2 bg-slate-800/50 rounded-xl border border-slate-700/50 text-sm text-slate-400">
                      Drag canvas to pan
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div
              style={{
                transform: `translate(${pan.x * zoom}px, ${pan.y * zoom}px) scale(${zoom})`,
                transformOrigin: '0 0',
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none'
              }}
            >
              {nodes.map(node => (
                <div
                  key={node.id}
                  className={`absolute select-none group ${selectedNode === node.id ? 'z-20' : 'z-10'}`}
                  style={{
                    left: node.position.x,
                    top: node.position.y,
                    pointerEvents: 'auto'
                  }}
                  onMouseDown={(e) => startDrag(node.id, e)}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNode(node.id);
                  }}
                >
                  <div className={`relative bg-gradient-to-br from-slate-800/95 to-slate-900/95 backdrop-blur-2xl border-2 rounded-2xl shadow-2xl transition-all cursor-move ${selectedNode === node.id
                    ? 'border-cyan-400 shadow-cyan-500/30 scale-105 ring-4 ring-cyan-500/20'
                    : 'border-slate-700/50 hover:border-slate-600 hover:shadow-slate-700/20'
                    }`} style={{ width: '220px' }}>

                    {/* Node Header */}
                    <div className={`h-24 rounded-t-2xl bg-gradient-to-br ${node.color} flex items-center justify-center relative overflow-hidden`}>
                      <div className="absolute inset-0 bg-black/10 backdrop-blur-sm"></div>
                      <div className="absolute inset-0 opacity-30">
                        <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                      </div>
                      <div className="text-5xl relative z-10 drop-shadow-lg">{node.icon}</div>

                      {/* Control Buttons */}
                      <div className="absolute top-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const duplicate = {
                              ...node,
                              id: `node-${Date.now()}`,
                              position: { x: node.position.x + 30, y: node.position.y + 30 }
                            };
                            setNodes([...nodes, duplicate]);
                          }}
                          className="node-control w-8 h-8 bg-blue-500/90 hover:bg-blue-500 backdrop-blur-xl rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-110 active:scale-95"
                        >
                          <Copy className="w-4 h-4 text-white" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteNode(node.id);
                          }}
                          className="node-control w-8 h-8 bg-red-500/90 hover:bg-red-500 backdrop-blur-xl rounded-xl flex items-center justify-center transition-all shadow-lg hover:scale-110 active:scale-95"
                        >
                          <Trash2 className="w-4 h-4 text-white" />
                        </button>
                      </div>

                      {/* Status Indicator */}
                      {isRunning && (
                        <div className="absolute top-3 left-3">
                          <div className="w-3 h-3 bg-green-400 rounded-full animate-ping absolute"></div>
                          <div className="w-3 h-3 bg-green-400 rounded-full relative"></div>
                        </div>
                      )}
                    </div>

                    {/* Node Content */}
                    <div className="p-5">
                      <h3 className="font-bold text-slate-100 mb-1.5 text-base">{node.name}</h3>
                      <p className="text-xs text-slate-400 mb-3">{node.type.split('-').join(' ')}</p>

                      {/* Node Stats */}
                      <div className="flex items-center gap-3 pt-3 border-t border-slate-700/50">
                        <div className="flex items-center gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-cyan-400"></div>
                          <span className="text-xs text-slate-400">Ready</span>
                        </div>
                        <div className="w-px h-3 bg-slate-700"></div>
                        <button
                          className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1 transition-colors"
                          onClick={(e) => { e.stopPropagation(); setConfigNode(node); }}
                        >
                          <Settings className="w-3 h-3" />
                          Configure
                        </button>
                      </div>
                    </div>

                    {/* Connection Points */}
                    <button
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        startConnection(node.id, e);
                      }}
                      onMouseUp={(e) => endConnection(node.id, e)}
                      className="node-control absolute -right-4 top-[111.5px] transform -translate-y-1/2 w-8 h-8 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-500 border-4 border-slate-900 rounded-full flex items-center justify-center hover:scale-125 transition-all shadow-xl shadow-cyan-500/30 cursor-pointer z-30 hover:rotate-90"
                      title="Connect to another node"
                    >
                      <Plus className="w-5 h-5 text-white" strokeWidth={3} />
                    </button>

                    <div
                      onMouseUp={(e) => endConnection(node.id, e)}
                      className="node-control absolute -left-4 top-[111.5px] transform -translate-y-1/2 w-8 h-8 bg-gradient-to-br from-purple-500 via-pink-500 to-rose-500 border-4 border-slate-900 rounded-full hover:scale-125 transition-all shadow-xl shadow-purple-500/30 z-30 flex items-center justify-center"
                      title="Connection point"
                    >
                      <div className="w-3 h-3 rounded-full bg-white"></div>
                    </div>

                    {/* Hover Glow Effect */}
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-cyan-500/0 to-purple-500/0 group-hover:from-cyan-500/5 group-hover:to-purple-500/5 transition-all pointer-events-none"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="bg-slate-900/50 backdrop-blur-xl border-t border-slate-800/50 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
            <span>Connected</span>
          </div>
          <div>Zoom: {Math.round(zoom * 100)}%</div>
          <div>Position: X: {Math.round(pan.x)}, Y: {Math.round(pan.y)}</div>
        </div>
        <div className="text-xs text-slate-500">
          Press Space + Drag to pan · Scroll to zoom · Click node to select
        </div>
      </div>

      {/* Node Config Modal */}
      {configNode && (
        <NodeConfigModal
          node={configNode}
          onClose={() => setConfigNode(null)}
          onSave={(data) => {
            updateNodeData(configNode.id, data);
            setConfigNode(null);
          }}
        />
      )}
    </div>
  );
};

export default WorkflowBuilder;