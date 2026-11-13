'use client';

import React, { useEffect, useState } from 'react';
import { HealthResponse } from '@/types/api';
import { fetchHealth } from '@/services/api';
import { Activity, CheckCircle2, AlertTriangle, RefreshCw, Server, Database, Layers, ArrowRight } from 'lucide-react';

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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              AI
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-white">Personal AI Core</h1>
              <p className="text-xs text-slate-400">Foundation Platform • Phase 0</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Phase 0 Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Backend Connectivity Status Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <Server className="h-5 w-5 text-indigo-400" />
              <h2 className="text-base font-medium text-white">Backend Health & Connectivity</h2>
            </div>
            <button
              onClick={checkConnection}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors border border-slate-700 disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh Status
            </button>
          </div>

          {loading && !health ? (
            <div className="py-8 text-center text-sm text-slate-400">
              Checking backend connection at <code className="text-indigo-300">/health</code>...
            </div>
          ) : error ? (
            <div className="rounded-lg bg-rose-950/40 border border-rose-800/60 p-4 text-sm text-rose-300 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Backend Unreachable</p>
                <p className="text-xs text-rose-400/80 mt-1">{error}</p>
                <p className="text-xs text-slate-400 mt-2">
                  Ensure the FastAPI backend is running via{' '}
                  <code className="text-slate-200 bg-slate-800 px-1 py-0.5 rounded">
                    uvicorn app.main:app --port 8000
                  </code>
                </p>
              </div>
            </div>
          ) : health ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
                <p className="text-xs text-slate-400 font-medium">Service Status</p>
                <div className="mt-2 flex items-center gap-2">
                  {health.status === 'healthy' ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      <span className="text-sm font-semibold text-emerald-400 uppercase tracking-wider">
                        {health.status}
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-4 w-4 text-amber-400" />
                      <span className="text-sm font-semibold text-amber-400 uppercase tracking-wider">
                        {health.status}
                      </span>
                    </>
                  )}
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
                <p className="text-xs text-slate-400 font-medium">Database Layer</p>
                <div className="mt-2 flex items-center gap-2">
                  <Database className="h-4 w-4 text-slate-400" />
                  <span
                    className={`text-sm font-semibold ${
                      health.database.connected ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {health.database.connected ? 'Connected' : 'Offline (Mock)'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1 truncate">
                  {health.database.message || 'Neon PostgreSQL'}
                </p>
              </div>

              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
                <p className="text-xs text-slate-400 font-medium">Environment</p>
                <div className="mt-2 text-sm font-semibold text-slate-200 capitalize">
                  {health.environment}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">v{health.version}</p>
              </div>

              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
                <p className="text-xs text-slate-400 font-medium">API Documentation</p>
                <a
                  href="http://localhost:8000/api/v1/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Swagger UI <ArrowRight className="h-3.5 w-3.5" />
                </a>
                <p className="text-[11px] text-slate-500 mt-1">/api/v1/docs</p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Modular Monolith Architecture Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-indigo-400">
              <Layers className="h-4 w-4" />
              <h3 className="text-sm font-medium text-white">Next.js Frontend</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              TypeScript App Router with Tailwind CSS. Ready for Phase 1 Authentication views and chat interface.
            </p>
            <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800">
              <span>Port: 3000</span>
              <span className="text-emerald-400">Scaffolded</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-indigo-400">
              <Activity className="h-4 w-4" />
              <h3 className="text-sm font-medium text-white">FastAPI Backend</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Python 3.12+ modular backend with Pydantic v2, async SQLAlchemy 2.x, Alembic, and pytest test suite.
            </p>
            <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800">
              <span>Port: 8000</span>
              <span className="text-emerald-400">Tested & Verified</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-indigo-400">
              <Database className="h-4 w-4" />
              <h3 className="text-sm font-medium text-white">Neon PostgreSQL</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Schema migrations managed via Alembic async template. Configured for pgvector embeddings and multi-tenancy.
            </p>
            <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800">
              <span>Driver: asyncpg</span>
              <span className="text-slate-400">Ready for Phase 1 Models</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500">
        Personal AI Core • Engineering Master Plan V1 • Modular Monolith Architecture
      </footer>
    </div>
  );
}
