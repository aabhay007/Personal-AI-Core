'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { listTools, ToolItem } from '@/services/conversations';
import { Wrench, ArrowLeft, Shield, Clock, CheckCircle2, Terminal } from 'lucide-react';

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchToolsList() {
      try {
        const data = await listTools();
        setTools(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load tools');
      } finally {
        setLoading(false);
      }
    }
    fetchToolsList();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-white">Tool Registry & Sandboxes</h1>
              <p className="text-xs text-slate-400">Available functions for LLM tool-calling</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Wrench className="h-3.5 w-3.5" />
            Phase 3 Active
          </span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-sm">Loading tool registry...</div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-sm text-rose-300">
            {error} (Sign in first)
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {tools.map((tool) => (
              <div
                key={tool.name}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-mono text-xs">
                      fn
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-white font-mono">{tool.name}</h2>
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 mt-0.5">
                        <CheckCircle2 className="h-3 w-3" /> Enabled
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
                    <Clock className="h-3 w-3 text-slate-500" />
                    <span>{tool.timeout_seconds}s timeout</span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{tool.description}</p>

                <div className="pt-2 border-t border-slate-800/80 space-y-2">
                  <p className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                    <Terminal className="h-3 w-3 text-indigo-400" />
                    Input Schema
                  </p>
                  <pre className="bg-slate-950 p-2.5 rounded-lg text-[10px] font-mono text-slate-300 overflow-x-auto border border-slate-800">
                    {JSON.stringify(tool.parameters?.properties || {}, null, 2)}
                  </pre>
                </div>

                <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
                  <Shield className="h-3.5 w-3.5 text-slate-500" />
                  <span>
                    {tool.requires_approval
                      ? 'Requires human confirmation before execution'
                      : 'Sandboxed automated execution'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
