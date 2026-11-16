'use client';

import React, { useEffect, useState } from 'react';
import { HealthResponse } from '@/types/api';
import { fetchHealth } from '@/services/api';
import { Activity, CheckCircle2, AlertTriangle, RefreshCw, Server, Database, Layers, ArrowRight, Sparkles } from 'lucide-react';
import { Skeleton } from '@/components/Skeleton';
import Link from 'next/link';

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkConnection = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unknown error connecting to backend');
      }
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  return (
    <div className="min-h-screen bg-[#090a0f] text-zinc-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
              AI
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight text-white">Personal AI Core</h1>
              <p className="text-xs text-zinc-400">Developer Intelligence Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="px-4 py-2 rounded-xl text-xs font-medium bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white transition-all shadow-md shadow-indigo-950/40"
            >
              Open Assistant
            </Link>
            <Link
              href="/login"
              className="px-4 py-2 rounded-xl text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] text-zinc-200 border border-white/[0.08] transition-colors"
            >
              Sign In
            </Link>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Platform Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Backend Connectivity Status Card */}
        <div className="bg-[#0d1017] border border-white/[0.08] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <Server className="h-5 w-5 text-indigo-400" />
              <h2 className="text-base font-medium text-white">Backend Health & Engine Status</h2>
            </div>
            <button
              onClick={checkConnection}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] text-zinc-200 transition-colors border border-white/[0.08] disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {loading && !health ? (
            <div className="py-6 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 w-full rounded-xl" />
                ))}
              </div>
            </div>
          ) : error ? (
            <div className="rounded-2xl bg-rose-950/40 border border-rose-800/40 p-4 text-sm text-rose-300 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Backend Unreachable</p>
                <p className="text-xs text-rose-400/80 mt-1">{error}</p>
                <p className="text-xs text-zinc-400 mt-2">
                  Ensure the FastAPI backend is running via{' '}
                  <code className="text-zinc-200 bg-white/[0.08] px-1.5 py-0.5 rounded font-mono text-[11px]">
                    uvicorn app.main:app --port 8000
                  </code>
                </p>
              </div>
            </div>
          ) : health ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                <p className="text-xs text-zinc-400 font-medium">Service Status</p>
                <div className="flex items-center gap-2 mt-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  <span className="text-base font-semibold capitalize text-white">{health.status}</span>
                </div>
                <p className="text-[10px] text-zinc-500 mt-1">Status: Active</p>
              </div>

              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                <p className="text-xs text-zinc-400 font-medium">Database (PostgreSQL)</p>
                <div className="flex items-center gap-2 mt-2">
                  <Database
                    className={`h-5 w-5 ${
                      health.database.connected ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  />
                  <span className="text-base font-semibold capitalize text-white">
                    {health.database.connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <p className="text-[10px] text-zinc-500 mt-1">
                  {health.database.message || 'Operational'}
                </p>
              </div>

              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                <p className="text-xs text-zinc-400 font-medium">Platform Version</p>
                <div className="flex items-center gap-2 mt-2">
                  <Activity className="h-5 w-5 text-indigo-400" />
                  <span className="text-base font-semibold text-white">v{health.version}</span>
                </div>
                <p className="text-[10px] text-zinc-500 mt-1">Environment: {health.environment}</p>
              </div>

              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                <p className="text-xs text-zinc-400 font-medium">Architectural Core</p>
                <div className="flex items-center gap-2 mt-2">
                  <Layers className="h-5 w-5 text-violet-400" />
                  <span className="text-base font-semibold text-white">Modular Core</span>
                </div>
                <p className="text-[10px] text-zinc-500 mt-1">Workspaces & Isolated DBs</p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Action Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/chat"
            className="group bg-[#0d1017] border border-white/[0.08] hover:border-indigo-500/50 rounded-2xl p-6 transition-all shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-105 transition-transform">
                <Sparkles className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Chat & Tool Calling</h3>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                Interact with the autonomous assistant with live tool execution, RAG context, and AST line-level code citations.
              </p>
            </div>
            <div className="mt-5 flex items-center gap-1.5 text-xs text-indigo-400 font-medium group-hover:translate-x-1 transition-transform">
              <span>Launch Chat</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </Link>

          <Link
            href="/documents"
            className="group bg-[#0d1017] border border-white/[0.08] hover:border-violet-500/50 rounded-2xl p-6 transition-all shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4 group-hover:scale-105 transition-transform">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Knowledge Engine & RAG</h3>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                Upload PDFs, markdown, and documentation. Automatically indexed using dense ONNX vector embeddings.
              </p>
            </div>
            <div className="mt-5 flex items-center gap-1.5 text-xs text-violet-400 font-medium group-hover:translate-x-1 transition-transform">
              <span>Manage Documents</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </Link>

          <Link
            href="/repositories"
            className="group bg-[#0d1017] border border-white/[0.08] hover:border-emerald-500/50 rounded-2xl p-6 transition-all shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-105 transition-transform">
                <Database className="h-5 w-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Code & Database Tools</h3>
              <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                Connect GitHub repositories and databases for safe schema inspection and semantic codebase navigation.
              </p>
            </div>
            <div className="mt-5 flex items-center gap-1.5 text-xs text-emerald-400 font-medium group-hover:translate-x-1 transition-transform">
              <span>Explore Connectors</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}
