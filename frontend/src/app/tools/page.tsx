'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { listTools, ToolItem } from '@/services/conversations';
import { Skeleton } from '@/components/Skeleton';
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
    <div className="min-h-screen bg-[#090a0f] text-zinc-100 flex flex-col font-sans">
      <header className="border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="p-2 text-zinc-400 hover:text-white rounded-xl hover:bg-white/[0.05] transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">Tool Registry & Sandboxes</h1>
              <p className="text-xs text-zinc-400">Available functions and safe execution engines for LLM tool-calling</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Wrench className="h-3.5 w-3.5" />
            Sandboxed Tools Active
          </span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-[#0d1017] border border-white/[0.08] rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Skeleton className="h-9 w-9 rounded-xl" />
                    <div className="space-y-1.5">
                      <Skeleton className="h-4 w-32 rounded" />
                      <Skeleton className="h-2.5 w-16 rounded" />
                    </div>
                  </div>
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
                <Skeleton className="h-3 w-full rounded" />
                <Skeleton className="h-3 w-4/5 rounded" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/40 text-xs text-rose-300">
            {error} (Sign in first)
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {tools.map((tool) => (
              <div
                key={tool.name}
                className="bg-[#0d1017] border border-white/[0.08] rounded-2xl p-5 space-y-4 hover:border-white/[0.15] transition-all shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-mono text-xs font-semibold shadow-inner">
                      fn
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-white font-mono">{tool.name}</h2>
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 mt-0.5">
                        <CheckCircle2 className="h-3 w-3" /> Enabled
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 bg-black/40 px-2.5 py-1 rounded-full border border-white/[0.06]">
                    <Clock className="h-3 w-3 text-zinc-500" />
                    <span>{tool.timeout_seconds}s timeout</span>
                  </div>
                </div>

                <p className="text-xs text-zinc-300 leading-relaxed">{tool.description}</p>

                <div className="pt-2 border-t border-white/[0.06] space-y-2">
                  <p className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Terminal className="h-3 w-3 text-indigo-400" />
                    Input Schema
                  </p>
                  <pre className="bg-[#08090d] p-3 rounded-xl text-[10px] font-mono text-zinc-300 overflow-x-auto border border-white/[0.06]">
                    {JSON.stringify(tool.parameters?.properties || {}, null, 2)}
                  </pre>
                </div>

                <div className="flex items-center gap-2 pt-1 text-[11px] text-zinc-500">
                  <Shield className="h-3.5 w-3.5 text-zinc-500" />
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
