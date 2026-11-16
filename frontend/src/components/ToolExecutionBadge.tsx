'use client';

import React, { useState } from 'react';
import {
  FileText,
  Calculator,
  Clock,
  FolderTree,
  FileCode,
  Search,
  Database,
  Terminal,
  Wrench,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface ToolExecutionEvent {
  tool_name: string;
  arguments?: Record<string, any>;
  result?: any;
  status: 'running' | 'done';
}

function getToolMeta(toolName: string) {
  switch (toolName) {
    case 'document_search':
      return {
        label: 'Knowledge Base Search',
        icon: FileText,
        color: 'text-violet-400',
        bg: 'bg-violet-500/10 border-violet-500/20',
      };
    case 'calculator':
      return {
        label: 'Calculator',
        icon: Calculator,
        color: 'text-cyan-400',
        bg: 'bg-cyan-500/10 border-cyan-500/20',
      };
    case 'get_current_datetime':
    case 'datetime_tool':
      return {
        label: 'System Clock',
        icon: Clock,
        color: 'text-amber-400',
        bg: 'bg-amber-500/10 border-amber-500/20',
      };
    case 'repo_file_tree':
      return {
        label: 'Repository File Tree',
        icon: FolderTree,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10 border-emerald-500/20',
      };
    case 'repo_code_search':
      return {
        label: 'Repository Code Search',
        icon: Search,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10 border-emerald-500/20',
      };
    case 'repo_read_file':
      return {
        label: 'Repository File Reader',
        icon: FileCode,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10 border-emerald-500/20',
      };
    case 'db_metadata_inspector':
      return {
        label: 'Database Inspector',
        icon: Database,
        color: 'text-blue-400',
        bg: 'bg-blue-500/10 border-blue-500/20',
      };
    case 'db_query_tool':
      return {
        label: 'Safe SQL Query',
        icon: Terminal,
        color: 'text-blue-400',
        bg: 'bg-blue-500/10 border-blue-500/20',
      };
    default:
      return {
        label: toolName,
        icon: Wrench,
        color: 'text-indigo-400',
        bg: 'bg-indigo-500/10 border-indigo-500/20',
      };
  }
}

export function ToolExecutionBadge({ event }: { event: ToolExecutionEvent }) {
  const [expanded, setExpanded] = useState(false);
  const meta = getToolMeta(event.tool_name);
  const Icon = meta.icon;

  const rawResult = event.result?.result ?? event.result;
  const isSuccess = event.result?.success !== false && !event.result?.error;
  const errorMessage = event.result?.error || (!isSuccess ? 'Tool execution encountered an error' : null);

  // Summarize the outcome
  let summary = '';
  if (event.status === 'running') {
    const q = event.arguments?.query || event.arguments?.expression || event.arguments?.table_name || '';
    summary = q ? `Executing query "${q}"...` : 'Invoking tool...';
  } else if (!isSuccess) {
    summary = 'Execution failed';
  } else if (rawResult?.results && Array.isArray(rawResult.results)) {
    summary = `${rawResult.results.length} excerpts retrieved`;
  } else if (typeof rawResult === 'object' && rawResult !== null) {
    summary = 'Completed successfully';
  } else if (rawResult !== undefined && rawResult !== null) {
    summary = String(rawResult).slice(0, 60);
  } else {
    summary = 'Completed';
  }

  return (
    <div className="rounded-xl border border-white/[0.08] bg-zinc-900/70 overflow-hidden text-xs my-2 transition-all">
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between px-3.5 py-2.5 cursor-pointer hover:bg-white/[0.03] transition-colors gap-2"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`h-6 w-6 rounded-lg flex items-center justify-center shrink-0 border ${meta.bg}`}>
            <Icon className={`h-3.5 w-3.5 ${meta.color}`} />
          </div>

          <div className="flex items-center gap-2 truncate">
            <span className="font-medium text-zinc-200 truncate">{meta.label}</span>
            <span className="text-zinc-500 text-[11px]">•</span>
            <span className={`text-[11px] truncate ${!isSuccess && event.status === 'done' ? 'text-rose-400 font-medium' : 'text-zinc-400'}`}>
              {summary}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {event.status === 'running' ? (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px]">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              <span>Running</span>
            </div>
          ) : isSuccess ? (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px]">
              <CheckCircle2 className="h-3 w-3" />
              <span>Success</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px]">
              <AlertCircle className="h-3 w-3" />
              <span>Failed</span>
            </div>
          )}

          <button
            type="button"
            className="text-zinc-400 hover:text-zinc-200 p-0.5 transition-colors"
            aria-label={expanded ? 'Collapse details' : 'Expand details'}
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 py-3 border-t border-white/[0.06] bg-black/30 space-y-3 font-mono text-[11px]">
          {/* Input Arguments */}
          {event.arguments && Object.keys(event.arguments).length > 0 && (
            <div>
              <p className="text-[10px] text-zinc-400 font-sans uppercase tracking-wider mb-1 font-semibold">
                Arguments
              </p>
              <pre className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 text-zinc-300 overflow-x-auto">
                {JSON.stringify(event.arguments, null, 2)}
              </pre>
            </div>
          )}

          {/* Results / Error */}
          {errorMessage ? (
            <div>
              <p className="text-[10px] text-rose-400 font-sans uppercase tracking-wider mb-1 font-semibold">
                Error Details
              </p>
              <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs font-sans">
                {errorMessage}
              </div>
            </div>
          ) : (
            <div>
              <p className="text-[10px] text-zinc-400 font-sans uppercase tracking-wider mb-1 font-semibold">
                Output
              </p>
              {rawResult?.results && Array.isArray(rawResult.results) ? (
                <div className="space-y-2 font-sans">
                  {rawResult.results.map((r: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between text-[11px] text-zinc-400">
                        <span className="font-medium text-violet-300">{r.filename}</span>
                        <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">
                          p. {r.page_number ?? 1} • match {(Number(r.score) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-zinc-300 text-xs italic leading-relaxed line-clamp-3">
                        &quot;{r.content}&quot;
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <pre className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 text-zinc-300 overflow-x-auto max-h-48">
                  {typeof rawResult === 'string'
                    ? rawResult
                    : JSON.stringify(rawResult, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
