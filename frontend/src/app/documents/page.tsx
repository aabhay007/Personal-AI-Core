'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { DocumentItem } from '@/types/document';
import { Workspace } from '@/types/auth';
import { getMe } from '@/services/auth';
import { listWorkspaces } from '@/services/conversations';
import { listDocuments, uploadDocument, deleteDocument } from '@/services/documents';
import { useToast } from '@/components/Toast';
import { ConfirmModal } from '@/components/ConfirmModal';
import { DocumentTableSkeleton } from '@/components/Skeleton';
import {
  FileText,
  UploadCloud,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileCheck,
  Loader2,
} from 'lucide-react';

export default function DocumentsPage() {
  const router = useRouter();
  const toast = useToast();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Delete modal state
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
    async function loadDocs() {
      setLoading(true);
      try {
        const list = await listDocuments(activeWorkspace!.id);
        setDocuments(list);
      } catch (err) {
        console.error('Failed to load documents', err);
        toast.error('Failed to load documents');
      } finally {
        setLoading(false);
      }
    }
    loadDocs();
  }, [activeWorkspace]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !activeWorkspace) return;

    const file = files[0];
    setUploading(true);
    setUploadError(null);

    try {
      const doc = await uploadDocument(activeWorkspace.id, file);
      setDocuments((prev) => [doc, ...prev]);
      toast.success(`Successfully uploaded "${file.name}"`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(msg);
      toast.error(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deleteTargetId);
      setDocuments((prev) => prev.filter((d) => d.id !== deleteTargetId));
      toast.success('Document deleted');
    } catch (err) {
      console.error('Failed to delete document', err);
      toast.error('Failed to delete document');
    } finally {
      setIsDeleting(false);
      setDeleteTargetId(null);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-[#090a0f] text-zinc-100 flex flex-col font-sans">
      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteTargetId)}
        title="Delete Document"
        message="Are you sure you want to delete this document? Its text chunks and semantic vector index will be permanently removed."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />

      {/* Header */}
      <header className="border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="p-2 text-zinc-400 hover:text-white rounded-xl hover:bg-white/[0.05] transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">Knowledge Engine & RAG</h1>
              <p className="text-xs text-zinc-400">Upload documents for semantic vector search and source citations</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <FileCheck className="h-3.5 w-3.5" />
              FastEmbed RAG Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Upload Zone Card */}
        <div className="bg-[#0d1017] border border-white/[0.08] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-medium text-white">Ingest New Document</h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Supported formats: <strong className="text-zinc-200">PDF, TXT, Markdown, DOCX</strong>. Chunked and indexed with dense vectors.
              </p>
            </div>
            {workspaces.length > 1 && (
              <select
                value={activeWorkspace?.id}
                onChange={(e) => {
                  const ws = workspaces.find((w) => w.id === e.target.value);
                  if (ws) setActiveWorkspace(ws);
                }}
                className="bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
              >
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    Workspace: {ws.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {uploadError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-950/40 border border-rose-800/40 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{uploadError}</span>
            </div>
          )}

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-white/[0.1] hover:border-indigo-500/60 rounded-2xl p-8 text-center cursor-pointer transition-all bg-white/[0.02] hover:bg-white/[0.04] group"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.txt,.md,.markdown,.docx"
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center">
              <div className="h-12 w-12 rounded-xl bg-indigo-600/10 group-hover:bg-indigo-600/20 text-indigo-400 flex items-center justify-center mb-3 transition-colors shadow-inner">
                {uploading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
                ) : (
                  <UploadCloud className="h-6 w-6" />
                )}
              </div>
              <p className="text-sm font-medium text-zinc-200">
                {uploading ? 'Processing, chunking & embedding document...' : 'Click to select or drag and drop a file'}
              </p>
              <p className="text-xs text-zinc-500 mt-1">Automatic recursive chunking and 384-dim dense vector generation</p>
            </div>
          </div>
        </div>

        {/* Ingested Documents Table */}
        <div className="bg-[#0d1017] border border-white/[0.08] rounded-2xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Indexed Documents ({documents.length})</h3>
            <span className="text-xs text-zinc-400 font-mono">Workspace: {activeWorkspace?.name || 'Default'}</span>
          </div>

          {loading ? (
            <div className="p-6">
              <DocumentTableSkeleton rows={3} />
            </div>
          ) : documents.length === 0 ? (
            <div className="py-14 text-center text-zinc-500 text-xs">
              <FileText className="h-9 w-9 mx-auto text-zinc-700 mb-2.5" />
              <p className="text-zinc-400 font-medium">No documents uploaded to this workspace yet</p>
              <p className="text-zinc-600 mt-1">Upload a PDF or TXT file above to enable semantic search in chat.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.06]">
              {documents.map((doc) => (
                <div key={doc.id} className="px-6 py-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center gap-3.5 truncate mr-4">
                    <div className="h-9 w-9 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-400 shrink-0">
                      <FileText className="h-4 w-4 text-indigo-400" />
                    </div>
                    <div className="truncate">
                      <p className="text-xs font-medium text-white truncate">{doc.filename}</p>
                      <div className="flex items-center gap-2 text-[10px] text-zinc-400 mt-0.5">
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    {doc.processing_status === 'completed' ? (
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" /> Indexed
                      </span>
                    ) : doc.processing_status === 'processing' ? (
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
                        <Clock className="h-3 w-3 animate-spin" /> Processing
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded-full border border-rose-500/20">
                        <AlertCircle className="h-3 w-3" /> Failed
                      </span>
                    )}

                    <button
                      onClick={() => setDeleteTargetId(doc.id)}
                      className="p-1.5 text-zinc-400 hover:text-rose-400 rounded-lg hover:bg-white/[0.05] transition-colors cursor-pointer"
                      title="Delete document"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
