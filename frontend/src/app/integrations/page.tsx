'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Integration,
  IntegrationCreate,
  IntegrationTestResponse,
  SchemaMetadata,
} from '@/types/integration';
import { Workspace } from '@/types/auth';
import { getMe } from '@/services/auth';
import { listWorkspaces } from '@/services/conversations';
import {
  listIntegrations,
  createIntegration,
  deleteIntegration,
  testUnsavedConnection,
  testSavedIntegration,
  getIntegrationSchemas,
} from '@/services/integrations';
import {
  Database,
  Plus,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Table,
  Key,
  ShieldCheck,
  Server,
  Layers,
  X,
} from 'lucide-react';

export default function IntegrationsPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isSchemaOpen, setIsSchemaOpen] = useState(false);
  const [schemaData, setSchemaData] = useState<SchemaMetadata | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);

  // Form states
  const [formType, setFormType] = useState<'postgres' | 'sqlite'>('postgres');
  const [formName, setFormName] = useState('');
  const [formHost, setFormHost] = useState('');
  const [formPort, setFormPort] = useState('5432');
  const [formDatabase, setFormDatabase] = useState('');
  const [formUsername, setFormUsername] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formSslMode, setFormSslMode] = useState('prefer');
  const [formApprovedTables, setFormApprovedTables] = useState('');

  // Test states
  const [testingUnsaved, setTestingUnsaved] = useState(false);
  const [testResult, setTestResult] = useState<IntegrationTestResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Card action states
  const [testingId, setTestingId] = useState<string | null>(null);
  const [cardTestResults, setCardTestResults] = useState<Record<string, IntegrationTestResponse>>({});

  useEffect(() => {
    async function init() {
      try {
        await getMe();
        const wsList = await listWorkspaces();
        setWorkspaces(wsList);
        if (wsList.length > 0) {
          setActiveWorkspace(wsList[0]);
        }
      } catch {
        router.push('/login');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [router]);

  useEffect(() => {
    if (!activeWorkspace) return;
    loadIntegrations();
  }, [activeWorkspace]);

  async function loadIntegrations() {
    if (!activeWorkspace) return;
    try {
      const list = await listIntegrations(activeWorkspace.id);
      setIntegrations(list);
    } catch (err) {
      console.error('Failed to load integrations', err);
    }
  }

  async function handleTestUnsaved() {
    setTestingUnsaved(true);
    setTestResult(null);
    setSaveError(null);
    try {
      const res = await testUnsavedConnection({
        integration_type: formType,
        host: formHost || undefined,
        port: formPort ? parseInt(formPort, 10) : undefined,
        database: formDatabase || undefined,
        username: formUsername || undefined,
        password: formPassword || undefined,
        ssl_mode: formSslMode,
      });
      setTestResult(res);
    } catch (err: unknown) {
      setTestResult({
        success: false,
        latency_ms: 0,
        error: err instanceof Error ? err.message : 'Connection test failed',
      });
    } finally {
      setTestingUnsaved(false);
    }
  }

  async function handleSaveIntegration(e: React.FormEvent) {
    e.preventDefault();
    if (!activeWorkspace) return;
    setSaving(true);
    setSaveError(null);

    const approvedTables = formApprovedTables
      ? formApprovedTables
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
      : undefined;

    const payload: IntegrationCreate = {
      name: formName,
      integration_type: formType,
      host: formHost || undefined,
      port: formPort ? parseInt(formPort, 10) : undefined,
      database: formDatabase || undefined,
      username: formUsername || undefined,
      password: formPassword || undefined,
      ssl_mode: formSslMode,
      approved_tables: approvedTables,
    };

    try {
      await createIntegration(activeWorkspace.id, payload);
      setIsConnectOpen(false);
      resetForm();
      await loadIntegrations();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save integration');
    } finally {
      setSaving(false);
    }
  }

  function resetForm() {
    setFormName('');
    setFormHost('');
    setFormPort('5432');
    setFormDatabase('');
    setFormUsername('');
    setFormPassword('');
    setFormSslMode('prefer');
    setFormApprovedTables('');
    setTestResult(null);
    setSaveError(null);
  }

  async function handleTestSaved(id: string) {
    setTestingId(id);
    try {
      const res = await testSavedIntegration(id);
      setCardTestResults((prev) => ({ ...prev, [id]: res }));
    } catch (err: unknown) {
      setCardTestResults((prev) => ({
        ...prev,
        [id]: {
          success: false,
          latency_ms: 0,
          error: err instanceof Error ? err.message : 'Test failed',
        },
      }));
    } finally {
      setTestingId(null);
    }
  }

  async function handleInspectSchema(id: string) {
    setIsSchemaOpen(true);
    setSchemaLoading(true);
    setSchemaData(null);
    try {
      const data = await getIntegrationSchemas(id);
      setSchemaData(data);
    } catch (err) {
      console.error('Failed to load schema', err);
    } finally {
      setSchemaLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Are you sure you want to disconnect this database integration?')) return;
    try {
      await deleteIntegration(id);
      setIntegrations((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      console.error('Failed to delete integration', err);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mr-2" />
        <span>Loading integrations...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-600/20 rounded-lg text-indigo-400">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white">Database Integrations</h1>
              <p className="text-xs text-slate-400">
                Safe, read-only SQL connectors with schema introspection and allowlist enforcement
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {workspaces.length > 1 && (
            <select
              value={activeWorkspace?.id}
              onChange={(e) => {
                const ws = workspaces.find((w) => w.id === e.target.value);
                if (ws) setActiveWorkspace(ws);
              }}
              className="bg-slate-800 text-xs text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => {
              resetForm();
              setIsConnectOpen(true);
            }}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Connect Database</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-6xl w-full mx-auto space-y-6">
        {/* Security Alert Banner */}
        <div className="bg-slate-900/60 border border-indigo-500/30 rounded-xl p-4 flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-medium text-slate-200">Zero-Trust Read-Only Architecture</p>
            <p className="text-slate-400 leading-relaxed">
              AI Core enforces strict security boundaries on all database integrations. All queries are strictly
              parameterized read-only <code className="text-indigo-300">SELECT</code> operations capped at 100 rows.
              Arbitrary SQL execution, data mutations, and raw credential disclosures to the LLM are forbidden.
            </p>
          </div>
        </div>

        {/* Integrations List */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Connected Databases ({integrations.length})
          </h2>

          {integrations.length === 0 ? (
            <div className="border border-dashed border-slate-800 rounded-xl p-12 text-center bg-slate-900/30">
              <Server className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-300 font-medium">No database connections configured</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
                Connect a PostgreSQL database (e.g. Neon, Supabase, AWS RDS) or a local SQLite file to enable safe data
                retrieval tools for your AI assistant.
              </p>
              <button
                onClick={() => {
                  resetForm();
                  setIsConnectOpen(true);
                }}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium inline-flex items-center gap-1.5 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Connect Database</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {integrations.map((item) => {
                const cardTest = cardTestResults[item.id];
                const isTesting = testingId === item.id;

                return (
                  <div
                    key={item.id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-colors shadow-sm"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                            <Database className="h-4 w-4" />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-white">{item.name}</h3>
                            <span className="text-[10px] text-slate-400 font-mono uppercase bg-slate-800 px-1.5 py-0.5 rounded">
                              {item.integration_type}
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={() => handleDelete(item.id)}
                          className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                          title="Disconnect database"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>

                      {/* Connection details */}
                      <div className="space-y-1.5 my-3 text-xs text-slate-300 font-mono bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
                        {item.integration_type === 'sqlite' ? (
                          <div className="truncate">
                            <span className="text-slate-500">File: </span>
                            <span className="text-slate-200">{item.database}</span>
                          </div>
                        ) : (
                          <>
                            <div className="truncate">
                              <span className="text-slate-500">Host: </span>
                              <span className="text-slate-200">
                                {item.host}:{item.port}
                              </span>
                            </div>
                            <div className="truncate">
                              <span className="text-slate-500">Database: </span>
                              <span className="text-slate-200">{item.database}</span>
                            </div>
                            <div className="truncate">
                              <span className="text-slate-500">User: </span>
                              <span className="text-slate-200">{item.username || 'default'}</span>
                            </div>
                          </>
                        )}
                        <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800/60 font-sans">
                          <span className="text-slate-500">SSL Mode:</span>
                          <span className="text-slate-300 font-mono">{item.ssl_mode}</span>
                        </div>
                      </div>

                      {/* Approved tables tag */}
                      <div className="mb-3 text-xs">
                        <span className="text-slate-400 text-[11px]">Approved Tables: </span>
                        {item.approved_tables && item.approved_tables.length > 0 ? (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {item.approved_tables.map((t) => (
                              <span
                                key={t}
                                className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded font-mono"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-amber-400 text-[11px]">All tables accessible (read-only)</span>
                        )}
                      </div>

                      {/* Card Test status */}
                      {cardTest && (
                        <div
                          className={`mb-3 p-2 rounded-lg text-xs flex items-center gap-2 ${
                            cardTest.success
                              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                              : 'bg-red-500/10 border border-red-500/20 text-red-300'
                          }`}
                        >
                          {cardTest.success ? (
                            <>
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                              <span className="truncate">
                                Connected ({cardTest.latency_ms}ms) • {cardTest.version?.slice(0, 35)}
                              </span>
                            </>
                          ) : (
                            <>
                              <AlertCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />
                              <span className="truncate">{cardTest.error || 'Connection failed'}</span>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Card Actions */}
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                      <button
                        onClick={() => handleInspectSchema(item.id)}
                        className="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                      >
                        <Layers className="h-3.5 w-3.5 text-indigo-400" />
                        <span>Inspect Schema</span>
                      </button>

                      <button
                        onClick={() => handleTestSaved(item.id)}
                        disabled={isTesting}
                        className="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                      >
                        {isTesting ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5 text-slate-400" />
                        )}
                        <span>Test</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Connect Database Modal */}
      {isConnectOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Connect Database</h3>
              </div>
              <button
                onClick={() => setIsConnectOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveIntegration} className="p-5 space-y-4 overflow-y-auto">
              {/* Type Switcher */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Database Type</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setFormType('postgres')}
                    className={`py-2 px-3 rounded-lg text-xs font-medium border text-center transition-colors ${
                      formType === 'postgres'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    PostgreSQL
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormType('sqlite')}
                    className={`py-2 px-3 rounded-lg text-xs font-medium border text-center transition-colors ${
                      formType === 'sqlite'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    SQLite (Local / Testing)
                  </button>
                </div>
              </div>

              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Integration Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Analytics Warehouse"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {formType === 'postgres' ? (
                <>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-slate-300 mb-1">Host</label>
                      <input
                        type="text"
                        required
                        placeholder="ep-fancy-pool.neon.tech or localhost"
                        value={formHost}
                        onChange={(e) => setFormHost(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Port</label>
                      <input
                        type="number"
                        required
                        value={formPort}
                        onChange={(e) => setFormPort(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Database Name</label>
                    <input
                      type="text"
                      required
                      placeholder="neondb or postgres"
                      value={formDatabase}
                      onChange={(e) => setFormDatabase(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Username</label>
                      <input
                        type="text"
                        placeholder="readonly_user"
                        value={formUsername}
                        onChange={(e) => setFormUsername(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={formPassword}
                        onChange={(e) => setFormPassword(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">SSL Mode</label>
                    <select
                      value={formSslMode}
                      onChange={(e) => setFormSslMode(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="require">require (Cloud / Neon / Supabase)</option>
                      <option value="prefer">prefer (Default)</option>
                      <option value="disable">disable (Local dev only)</option>
                    </select>
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Database File Path</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ./sample_data.db"
                    value={formDatabase}
                    onChange={(e) => setFormDatabase(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Approved Tables */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Approved Tables Allowlist <span className="text-slate-500">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="orders, products, customers (leave blank for all)"
                  value={formApprovedTables}
                  onChange={(e) => setFormApprovedTables(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Comma-separated list of tables the AI is authorized to introspect and query.
                </p>
              </div>

              {/* Test feedback */}
              {testResult && (
                <div
                  className={`p-3 rounded-lg text-xs flex items-start gap-2 ${
                    testResult.success
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                      : 'bg-red-500/10 border border-red-500/20 text-red-300'
                  }`}
                >
                  {testResult.success ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium">Connection successful ({testResult.latency_ms}ms)</p>
                        <p className="text-[11px] text-emerald-400/80 truncate">{testResult.version}</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium">Connection failed</p>
                        <p className="text-[11px] text-red-400/80">{testResult.error}</p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {saveError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{saveError}</span>
                </div>
              )}

              {/* Modal footer buttons */}
              <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleTestUnsaved}
                  disabled={testingUnsaved}
                  className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {testingUnsaved ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5 text-slate-400" />
                  )}
                  <span>Test Connection</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsConnectOpen(false)}
                    className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg text-xs font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    <span>Save Integration</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Schema Inspector Modal */}
      {isSchemaOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">
                  Database Schema: {schemaData?.integration_name || 'Loading...'}
                </h3>
              </div>
              <button
                onClick={() => setIsSchemaOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              {schemaLoading ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-400">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mb-2" />
                  <span className="text-xs">Introspecting database tables and columns...</span>
                </div>
              ) : !schemaData || schemaData.tables.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No tables found or accessible in this schema.
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
                    <span>
                      Total Accessible Tables: <strong className="text-white">{schemaData.tables.length}</strong>
                    </span>
                    <span className="font-mono text-[11px] bg-slate-800 px-2 py-0.5 rounded">
                      Type: {schemaData.integration_type}
                    </span>
                  </div>

                  {schemaData.tables.map((t) => (
                    <div
                      key={t.table_name}
                      className="border border-slate-800 bg-slate-950/60 rounded-xl overflow-hidden"
                    >
                      <div className="bg-slate-850 px-4 py-2.5 flex items-center gap-2 border-b border-slate-800">
                        <Table className="h-3.5 w-3.5 text-indigo-400" />
                        <span className="text-xs font-semibold text-white font-mono">{t.table_name}</span>
                        <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded font-mono">
                          {t.schema}
                        </span>
                        <span className="text-[10px] text-slate-500 ml-auto">{t.columns.length} columns</span>
                      </div>

                      <div className="p-3 overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="text-slate-500 border-b border-slate-800/80 text-[11px]">
                              <th className="pb-1.5 font-medium">Column</th>
                              <th className="pb-1.5 font-medium">Type</th>
                              <th className="pb-1.5 font-medium">Nullable</th>
                              <th className="pb-1.5 font-medium">Key</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/40 text-slate-300">
                            {t.columns.map((c) => (
                              <tr key={c.name} className="hover:bg-slate-800/30">
                                <td className="py-1.5 font-medium text-slate-200">{c.name}</td>
                                <td className="py-1.5 text-indigo-300 text-[11px]">{c.data_type}</td>
                                <td className="py-1.5 text-slate-400 text-[11px]">
                                  {c.is_nullable ? 'NULL' : 'NOT NULL'}
                                </td>
                                <td className="py-1.5">
                                  {c.is_primary_key && (
                                    <span className="inline-flex items-center gap-1 text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.2 rounded">
                                      <Key className="h-2.5 w-2.5" />
                                      PK
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
