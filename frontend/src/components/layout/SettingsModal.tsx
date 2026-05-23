import React, { useState, useEffect } from 'react';
import { Settings, X, Package, RefreshCw, AlertTriangle, ToggleLeft, ToggleRight } from 'lucide-react';

interface ModuleConfig {
  name: string;
  description?: string;
  version?: string;
  enabled: boolean;
  api_prefix?: string;
  _dir?: string;
  _loaded?: boolean;
}

export const SettingsModal: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const [modules, setModules] = useState<ModuleConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setDirty(false);
    fetch('/api/modules/all')
      .then((r) => r.json() as Promise<ModuleConfig[]>)
      .then(setModules)
      .catch(() => setModules([]))
      .finally(() => setLoading(false));
  }, [open]);

  const toggleModule = async (dirName: string, enabled: boolean) => {
    setToggling(dirName);
    try {
      const res = await fetch(`/api/modules/${dirName}/enabled`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (res.ok) {
        setModules((prev) => prev.map((m) => (m._dir === dirName ? { ...m, enabled } : m)));
        setDirty(true);
      }
    } finally {
      setToggling(null);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#0c0a14] border border-purple-500/30 rounded-lg w-[480px] max-h-[75vh] flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 shrink-0">
          <div className="flex items-center gap-2">
            <Settings className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-[10px] font-black uppercase tracking-widest text-purple-300">System Settings</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-white transition-colors rounded hover:bg-white/5">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-3">

          {/* Section: Modules */}
          <div className="flex items-center gap-1.5 mb-2">
            <Package className="w-3 h-3 text-purple-400" />
            <span className="text-[9px] font-black uppercase tracking-widest text-zinc-300">Backend Modules</span>
            <span className="text-[8px] font-mono text-zinc-600 ml-auto">restart required for changes</span>
          </div>

          {dirty && (
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded mb-3">
              <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
              <span className="text-[9px] font-mono text-amber-300">Restart the backend server for module changes to take effect.</span>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-zinc-600">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span className="text-[9px] font-mono">Loading modules...</span>
            </div>
          ) : modules.length === 0 ? (
            <div className="text-center py-10 text-[9px] text-zinc-600 font-mono">No modules found in backend/modules/</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {modules.map((mod) => {
                const key = mod._dir || mod.name;
                const isToggling = toggling === key;
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-3 px-3 py-2.5 border rounded transition-colors ${
                      mod.enabled ? 'bg-white/3 border-white/8' : 'bg-black/20 border-white/5 opacity-60'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-bold text-zinc-100 truncate">{mod.name}</span>
                        {mod.version && (
                          <span className="text-[8px] font-mono text-zinc-600 shrink-0">v{mod.version}</span>
                        )}
                        {mod._loaded && (
                          <span className="text-[7px] font-mono text-green-400 bg-green-500/10 border border-green-500/20 px-1 py-0.5 rounded shrink-0">RUNNING</span>
                        )}
                      </div>
                      {mod.description && (
                        <p className="text-[9px] text-zinc-500 truncate">{mod.description}</p>
                      )}
                      {mod.api_prefix && (
                        <span className="text-[8px] font-mono text-zinc-700">{mod.api_prefix}</span>
                      )}
                    </div>

                    {/* Toggle switch */}
                    <button
                      onClick={() => void toggleModule(key, !mod.enabled)}
                      disabled={isToggling}
                      className="shrink-0 transition-opacity disabled:opacity-50"
                      title={mod.enabled ? 'Disable module' : 'Enable module'}
                    >
                      {isToggling ? (
                        <RefreshCw className="w-4 h-4 text-zinc-500 animate-spin" />
                      ) : mod.enabled ? (
                        <ToggleRight className="w-6 h-6 text-purple-400" />
                      ) : (
                        <ToggleLeft className="w-6 h-6 text-zinc-600" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
