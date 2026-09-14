"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Trash2, Users, Search, AlertCircle, Loader2 } from "lucide-react";
import { personasApi, TargetPersona } from "@/lib/api";

export default function PersonasCard() {
  const [personas, setPersonas] = useState<TargetPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [label, setLabel] = useState("");
  const [keywords, setKeywords] = useState("");
  const [maxProfiles, setMaxProfiles] = useState(150);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPersonas = useCallback(async () => {
    try {
      const res = await personasApi.list();
      setPersonas(res.personas);
    } catch (e) {
      console.warn("Could not load personas:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPersonas(); }, [loadPersonas]);

  const handleAdd = async () => {
    if (!label.trim() || !keywords.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const res = await personasApi.create({ label: label.trim(), search_keywords: keywords.trim(), max_profiles: maxProfiles });
      if (res.success && res.persona) {
        setPersonas((prev) => [...prev, res.persona!]);
        setLabel("");
        setKeywords("");
        setMaxProfiles(150);
        setAdding(false);
      } else {
        setError("Failed to create persona.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await personasApi.delete(id);
      setPersonas((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      console.warn("Delete failed:", e);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="bg-[#151C25] border border-zinc-800/60 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-violet-500/15 flex items-center justify-center">
            <Users size={14} className="text-violet-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-100">Target Personas</p>
            <p className="text-[10px] text-zinc-500">Who AI likes &amp; comments on LinkedIn</p>
          </div>
        </div>
        <button
          onClick={() => setAdding(true)}
          className="flex items-center gap-1.5 h-7 px-3 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-all"
        >
          <Plus size={12} />
          Add Persona
        </button>
      </div>

      {/* Add form */}
      {adding && (
        <div className="px-5 py-4 bg-violet-500/5 border-b border-violet-500/20 space-y-3">
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-zinc-400">Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. AI Startup Founders"
              className="w-full h-8 px-3 rounded-lg bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-zinc-400">LinkedIn Search Keywords</label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g. AI startup founder CEO SaaS"
              className="w-full h-8 px-3 rounded-lg bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-zinc-400">Max Profiles to Target ({maxProfiles})</label>
            <input
              type="range"
              min={10}
              max={500}
              step={10}
              value={maxProfiles}
              onChange={(e) => setMaxProfiles(Number(e.target.value))}
              className="w-full accent-violet-500"
            />
          </div>
          {error && (
            <div className="flex items-center gap-2 text-rose-400 text-xs">
              <AlertCircle size={12} />
              {error}
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={saving || !label.trim() || !keywords.trim()}
              className="flex-1 h-8 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-xs font-medium transition-all flex items-center justify-center gap-1.5"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              {saving ? "Saving…" : "Save Persona"}
            </button>
            <button
              onClick={() => { setAdding(false); setError(null); }}
              className="h-8 px-4 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 text-xs transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <div className="divide-y divide-zinc-800/40">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-zinc-600 text-xs gap-2">
            <Loader2 size={14} className="animate-spin" />
            Loading personas…
          </div>
        ) : personas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-center px-5">
            <Search size={22} className="text-zinc-600" />
            <p className="text-xs text-zinc-500">No personas yet</p>
            <p className="text-[11px] text-zinc-600 max-w-xs">
              Add a persona to tell the AI which LinkedIn profiles to target for likes &amp; comments
            </p>
          </div>
        ) : (
          personas.map((p) => (
            <div key={p.id} className="flex items-center gap-3 px-5 py-3 group hover:bg-zinc-800/30 transition-colors">
              <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                <Users size={12} className="text-violet-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-zinc-200 truncate">{p.label}</p>
                <p className="text-[10px] text-zinc-500 truncate">{p.search_keywords}</p>
              </div>
              <span className="text-[10px] text-zinc-600 shrink-0">{p.max_profiles} max</span>
              <button
                onClick={() => handleDelete(p.id)}
                disabled={deletingId === p.id}
                className="opacity-0 group-hover:opacity-100 ml-1 w-6 h-6 rounded-md hover:bg-rose-500/15 flex items-center justify-center text-zinc-600 hover:text-rose-400 transition-all"
              >
                {deletingId === p.id ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
