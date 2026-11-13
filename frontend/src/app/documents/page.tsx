'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { DocumentItem } from '@/types/document';
import { Workspace } from '@/types/auth';
import { getMe } from '@/services/auth';
import { listWorkspaces } from '@/services/conversations';
import { listDocuments, uploadDocument, deleteDocument } from '@/services/documents';
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
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      try {
        const list = await listDocuments(activeWorkspace!.id);
        setDocuments(list);
      } catch (err) {
        console.error('Failed to load documents', err);
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
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document and its semantic index?')) return;
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err) {
      console.error('Failed to delete document', err);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mr-2" />
        <span>Loading knowledge engine...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-white">Knowledge Engine & RAG</h1>
              <p className="text-xs text-slate-400">Upload documents for semantic vector search and source citations</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <FileCheck className="h-3.5 w-3.5" />
              Phase 4 Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Upload Zone Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-medium text-white">Ingest New Document</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Supported formats: <strong className="text-slate-300">PDF, TXT, Markdown, DOCX</strong>. Chunked and indexed with FastEmbed.
              </p>
            </div>
            {workspaces.length > 1 && (
              <select
                value={activeWorkspace?.id}
                onChange={(e) => {
                  const ws = workspaces.find((w) => w.id === e.target.value);
                  if (ws) setActiveWorkspace(ws);
                }}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
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
            <div className="mb-4 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{uploadError}</span>
            </div>
          )}

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-800 hover:border-indigo-500/60 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-950/40 group"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.txt,.md,.markdown,.docx"
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center">
              <div className="h-12 w-12 rounded-xl bg-indigo-600/10 group-hover:bg-indigo-600/20 text-indigo-400 flex items-center justify-center mb-3 transition-colors">
                {uploading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
                ) : (
                  <UploadCloud className="h-6 w-6" />
                )}
              </div>
              <p className="text-sm font-medium text-slate-200">
                {uploading ? 'Processing & embedding document...' : 'Click to select or drag and drop a file'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Automatic recursive chunking and 384-dim dense vector generation</p>
            </div>
          </div>
        </div>

        {/* Ingested Documents Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Indexed Documents ({documents.length})</h3>
            <span className="text-xs text-slate-500 font-mono">Workspace: {activeWorkspace?.name}</span>
          </div>

          {documents.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              <FileText className="h-8 w-8 mx-auto text-slate-700 mb-2" />
              No documents uploaded to this workspace yet. Upload one above to enable RAG in chat!
            </div>
          ) : (
            <div className="divide-y divide-slate-800/80">
              {documents.map((doc) => (
                <div key={doc.id} className="px-6 py-3.5 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                  <div className="flex items-center gap-3 truncate mr-4">
                    <div className="h-8 w-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="truncate">
                      <p className="text-xs font-medium text-white truncate">{doc.filename}</p>
                      <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-0.5">
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    {doc.processing_status === 'completed' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" /> Indexed
                      </span>
                    ) : doc.processing_status === 'processing' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        <Clock className="h-3 w-3 animate-spin" /> Processing
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                        <AlertCircle className="h-3 w-3" /> Failed
                      </span>
                    )}

                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-400 rounded-md hover:bg-slate-800 transition-colors cursor-pointer"
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
