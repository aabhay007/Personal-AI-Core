'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  CodeRepository,
  CodeRepositoryCreate,
  RepositoryFile,
  CodeSearchMatch,
} from '@/types/repository';
import { Workspace } from '@/types/auth';
import { getMe } from '@/services/auth';
import { listWorkspaces } from '@/services/conversations';
import {
  listRepositories,
  createRepository,
  deleteRepository,
  syncRepository,
  getRepositoryTree,
  getRepositoryFile,
  searchRepositoryCode,
} from '@/services/repositories';
import { useToast } from '@/components/Toast';
import { ConfirmModal } from '@/components/ConfirmModal';
import { CodeViewerSkeleton, Skeleton } from '@/components/Skeleton';
import {
  GitBranch,
  FolderTree,
  FileCode,
  Search,
  Plus,
  Trash2,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Code2,
  Copy,
  Check,
  X,
  FileText,
} from 'lucide-react';

export default function RepositoriesPage() {
  const router = useRouter();
  const toast = useToast();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [repos, setRepos] = useState<CodeRepository[]>([]);
  const [loading, setLoading] = useState(true);

  // Selected state
  const [selectedRepo, setSelectedRepo] = useState<CodeRepository | null>(null);
  const [fileTree, setFileTree] = useState<string[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<RepositoryFile | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileFilter, setFileFilter] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CodeSearchMatch[]>([]);
  const [searching, setSearching] = useState(false);

  // Sync state
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  // Delete modal state
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Connect Repo Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [owner, setOwner] = useState('');
  const [repoName, setRepoName] = useState('');
  const [defaultBranch, setDefaultBranch] = useState('main');
  const [token, setToken] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Copy state
  const [copied, setCopied] = useState(false);

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
    loadRepos();
  }, [activeWorkspace]);

  async function loadRepos() {
    if (!activeWorkspace) return;
    try {
      const list = await listRepositories(activeWorkspace.id);
      setRepos(list);
      if (list.length > 0 && !selectedRepo) {
        selectRepository(list[0]);
      }
    } catch (err) {
      console.error('Failed to load repositories', err);
      toast.error('Failed to load repositories');
    }
  }

  async function selectRepository(repo: CodeRepository) {
    setSelectedRepo(repo);
    setSelectedFile(null);
    setSearchResults([]);
    setTreeLoading(true);
    try {
      const tree = await getRepositoryTree(repo.id);
      setFileTree(tree);
      if (tree.length > 0) {
        loadFile(repo.id, tree[0]);
      }
    } catch (err) {
      console.error('Failed to load tree', err);
      toast.error('Failed to load file tree');
    } finally {
      setTreeLoading(false);
    }
  }

  async function loadFile(repoId: string, filePath: string) {
    setFileLoading(true);
    try {
      const fileData = await getRepositoryFile(repoId, filePath);
      setSelectedFile(fileData);
    } catch (err) {
      console.error('Failed to load file', err);
      toast.error(`Failed to load file "${filePath}"`);
    } finally {
      setFileLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRepo || !searchQuery.trim()) return;

    setSearching(true);
    try {
      const response = await searchRepositoryCode(selectedRepo.id, searchQuery.trim());
      setSearchResults(response.results);
      if (response.results.length === 0) {
        toast.info('No code matches found for that query');
      }
    } catch (err) {
      console.error('Search failed', err);
      toast.error('Semantic code search failed');
    } finally {
      setSearching(false);
    }
  }

  async function handleSync(repoId: string) {
    setSyncingId(repoId);
    setSyncStatus('Indexing repository files...');
    try {
      const syncRes = await syncRepository(repoId);
      await loadRepos();
      if (selectedRepo?.id === repoId) {
        selectRepository(selectedRepo);
      }
      setSyncStatus(`Successfully indexed ${syncRes.indexed_files} files`);
      toast.success(`Repository synced! ${syncRes.indexed_files} files indexed`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sync failed';
      setSyncStatus(`Sync error: ${msg}`);
      toast.error(`Sync failed: ${msg}`);
    } finally {
      setSyncingId(null);
    }
  }

  async function handleCreateRepo(e: React.FormEvent) {
    e.preventDefault();
    if (!activeWorkspace) return;

    setCreating(true);
    setCreateError(null);
    try {
      const payload: CodeRepositoryCreate = {
        name,
        owner,
        repo_name: repoName,
        default_branch: defaultBranch || 'main',
        token: token || undefined,
      };
      const created = await createRepository(activeWorkspace.id, payload);
      setIsModalOpen(false);
      setName('');
      setOwner('');
      setRepoName('');
      setToken('');
      toast.success(`Connected repository "${created.name}"`);
      await loadRepos();
      selectRepository(created);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect repository';
      setCreateError(msg);
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  }

  async function handleConfirmDelete() {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await deleteRepository(deleteTargetId);
      setRepos((prev) => prev.filter((r) => r.id !== deleteTargetId));
      if (selectedRepo?.id === deleteTargetId) {
        setSelectedRepo(null);
        setSelectedFile(null);
        setFileTree([]);
      }
      toast.success('Repository disconnected');
    } catch (err) {
      console.error('Failed to delete repository', err);
      toast.error('Failed to disconnect repository');
    } finally {
      setIsDeleting(false);
      setDeleteTargetId(null);
    }
  }

  function copyCode() {
    if (!selectedFile?.content) return;
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    toast.success('Code copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  }

  const filteredTree = fileTree.filter((p) =>
    p.toLowerCase().includes(fileFilter.toLowerCase())
  );

  return (
    <div className="h-screen bg-[#090a0f] text-zinc-100 flex flex-col font-sans overflow-hidden">
      {/* Disconnect Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteTargetId)}
        title="Disconnect Repository"
        message="Are you sure you want to disconnect this repository? All vector indices and cached files will be removed from your workspace."
        confirmText="Disconnect"
        isDestructive={true}
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />

      {/* Top Header */}
      <header className="border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-600/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <Code2 className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white tracking-tight">Code Repositories & AST Index</h1>
              <p className="text-xs text-zinc-400">
                Codebase indexing, semantic code search, and file tree exploration
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
              className="bg-[#131722] text-xs text-zinc-200 border border-white/[0.08] rounded-xl px-3 py-1.5 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setIsModalOpen(true)}
            className="px-3.5 py-1.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm shadow-indigo-950/40 cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Connect Repository</span>
          </button>
        </div>
      </header>

      {/* Main Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Repository List & File Tree */}
        <div className="w-80 bg-[#0d1017] border-r border-white/[0.08] flex flex-col shrink-0">
          {/* Repositories Selector */}
          <div className="p-3.5 border-b border-white/[0.08]">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-2">
              Connected Repositories ({repos.length})
            </label>
            {loading ? (
              <div className="space-y-1.5">
                <Skeleton className="h-9 w-full rounded-xl" />
                <Skeleton className="h-9 w-full rounded-xl" />
              </div>
            ) : repos.length === 0 ? (
              <p className="text-xs text-zinc-500 italic py-2 text-center">No repositories connected</p>
            ) : (
              <div className="space-y-1.5">
                {repos.map((r) => {
                  const isSelected = selectedRepo?.id === r.id;
                  const isSyncing = syncingId === r.id;
                  return (
                    <div
                      key={r.id}
                      onClick={() => selectRepository(r)}
                      className={`p-2.5 rounded-xl cursor-pointer transition-all flex items-center justify-between text-xs ${
                        isSelected
                          ? 'bg-white/[0.08] text-white border-l-2 border-indigo-500 shadow-sm'
                          : 'bg-white/[0.02] text-zinc-300 hover:bg-white/[0.05] border border-white/[0.04]'
                      }`}
                    >
                      <div className="truncate mr-2">
                        <p className="font-medium truncate text-white">{r.name}</p>
                        <p className="text-[10px] text-zinc-400 font-mono truncate">
                          {r.owner}/{r.repo_name}
                        </p>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSync(r.id);
                          }}
                          disabled={isSyncing}
                          title="Sync from GitHub"
                          className="p-1 hover:bg-white/[0.08] rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
                        >
                          {isSyncing ? (
                            <Loader2 className="h-3 w-3 animate-spin text-indigo-400" />
                          ) : (
                            <RefreshCw className="h-3 w-3" />
                          )}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTargetId(r.id);
                          }}
                          title="Disconnect"
                          className="p-1 hover:bg-rose-500/20 rounded-lg text-zinc-500 hover:text-rose-400 transition-colors"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* File Tree Explorer */}
          <div className="flex-1 flex flex-col p-3.5 overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                <FolderTree className="h-3.5 w-3.5 text-indigo-400" />
                Files ({filteredTree.length})
              </span>
              {selectedRepo && (
                <span className="text-[10px] font-mono text-zinc-500">
                  {selectedRepo.default_branch}
                </span>
              )}
            </div>

            <div className="mb-2">
              <input
                type="text"
                placeholder="Filter files..."
                value={fileFilter}
                onChange={(e) => setFileFilter(e.target.value)}
                className="w-full bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div className="flex-1 overflow-y-auto space-y-0.5 pr-1 font-mono text-xs">
              {treeLoading ? (
                <div className="space-y-1.5 p-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-5 w-full rounded" />
                  ))}
                </div>
              ) : filteredTree.length === 0 ? (
                <p className="text-[11px] text-zinc-500 italic py-6 text-center">
                  {selectedRepo ? 'No indexed files match' : 'Select a repository'}
                </p>
              ) : (
                filteredTree.map((path) => {
                  const isCurrent = selectedFile?.file_path === path;
                  return (
                    <div
                      key={path}
                      onClick={() => selectedRepo && loadFile(selectedRepo.id, path)}
                      className={`px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors truncate flex items-center gap-2 ${
                        isCurrent
                          ? 'bg-indigo-600/20 text-indigo-300 font-medium border border-indigo-500/30'
                          : 'text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200'
                      }`}
                      title={path}
                    >
                      <FileCode className="h-3 w-3 shrink-0 text-zinc-500" />
                      <span className="truncate">{path}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Center / Right Content: Search & Code Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#090a0f]">
          {/* Top Search & Controls Bar */}
          <div className="p-3 border-b border-white/[0.08] bg-[#0d1017]/40 backdrop-blur flex items-center justify-between gap-4">
            <form onSubmit={handleSearch} className="flex-1 flex items-center gap-2.5 max-w-xl">
              <div className="relative flex-1">
                <Search className="h-3.5 w-3.5 absolute left-3.5 top-2.5 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Semantic code search (e.g. 'JWT token verification', 'health route')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#131722] border border-white/[0.08] rounded-xl pl-9 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={searching || !selectedRepo}
                className="px-3.5 py-1.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-sm cursor-pointer"
              >
                {searching ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
                <span>Search</span>
              </button>
            </form>

            {syncStatus && (
              <span className="text-xs text-indigo-300 truncate max-w-sm">{syncStatus}</span>
            )}
          </div>

          {/* Code Search Matches Drawer (if any) */}
          {searchResults.length > 0 && (
            <div className="bg-[#0d1017]/90 border-b border-white/[0.08] p-3.5 max-h-48 overflow-y-auto space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300">
                  Search Results ({searchResults.length} matches)
                </span>
                <button
                  onClick={() => setSearchResults([])}
                  className="text-zinc-500 hover:text-white text-xs cursor-pointer"
                >
                  Clear
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {searchResults.map((m, idx) => (
                  <div
                    key={idx}
                    onClick={() => selectedRepo && loadFile(selectedRepo.id, m.file_path)}
                    className="p-2.5 bg-black/40 border border-white/[0.08] hover:border-indigo-500/50 rounded-xl cursor-pointer transition-colors text-xs font-mono"
                  >
                    <div className="flex items-center justify-between text-[11px] text-indigo-400 mb-1">
                      <span className="truncate">{m.file_path}</span>
                      <span className="text-zinc-400">
                        L{m.start_line}-L{m.end_line} ({Math.round(m.similarity_score * 100)}%)
                      </span>
                    </div>
                    <pre className="text-[11px] text-zinc-300 truncate whitespace-pre-wrap line-clamp-2">
                      {m.content}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* File Viewer Main Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {selectedFile ? (
              <>
                <div className="px-5 py-2.5 border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur flex items-center justify-between font-mono text-xs">
                  <div className="flex items-center gap-2 text-zinc-300">
                    <FileCode className="h-4 w-4 text-indigo-400" />
                    <span className="font-semibold text-white">{selectedFile.file_path}</span>
                    <span className="text-zinc-500">
                      ({selectedFile.line_count} lines • {Math.round(selectedFile.size_bytes / 1024)} KB)
                    </span>
                  </div>

                  <button
                    onClick={copyCode}
                    className="flex items-center gap-1.5 px-3 py-1 bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 hover:text-white border border-white/[0.08] rounded-xl text-xs transition-colors cursor-pointer"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <div className="flex-1 overflow-auto p-4 font-mono text-xs text-zinc-200 bg-[#07080c]">
                  {fileLoading ? (
                    <CodeViewerSkeleton />
                  ) : (
                    <table className="w-full border-collapse">
                      <tbody>
                        {selectedFile.content?.split('\n').map((line, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.03] leading-5">
                            <td className="w-12 select-none text-right pr-4 text-zinc-600 font-mono text-[11px]">
                              {idx + 1}
                            </td>
                            <td className="whitespace-pre font-mono text-zinc-200">
                              {line || ' '}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 text-xs p-8 text-center">
                <Code2 className="h-12 w-12 text-zinc-700 mb-3" />
                <p className="font-medium text-zinc-400">No file selected</p>
                <p className="text-zinc-600 max-w-sm mt-1">
                  Select a file from the repository tree on the left or run a semantic code search.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connect Repository Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Connect GitHub Repository</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRepo} className="p-5 space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Friendly Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Personal AI Core"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">Owner / Org</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. google"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">Repository Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. personal-ai-core"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Default Branch</label>
                <input
                  type="text"
                  placeholder="main or master"
                  value={defaultBranch}
                  onChange={(e) => setDefaultBranch(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Personal Access Token (PAT) <span className="text-zinc-500">(Optional for public repos)</span>
                </label>
                <input
                  type="password"
                  placeholder="ghp_••••••••••••••••••••••••••••••••••••"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[10px] text-zinc-500 mt-1">
                  Required for private repositories. Encrypted with AES-256 at rest.
                </p>
              </div>

              {createError && (
                <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="py-2 px-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer shadow-md shadow-indigo-950/40"
                >
                  {creating && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span>Connect</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
