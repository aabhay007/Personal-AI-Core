'use client';

import React from 'react';

export function Skeleton({
  className = '',
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`relative overflow-hidden rounded-md bg-zinc-800/40 before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/[0.05] before:to-transparent ${className}`}
      {...props}
    />
  );
}

/**
 * Skeleton loader for the conversation list in the sidebar.
 */
export function ConversationListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-1.5 p-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-zinc-900/40 border border-zinc-800/40"
        >
          <Skeleton className="h-3.5 w-3.5 rounded shrink-0" />
          <Skeleton className="h-3 w-3/4 rounded" />
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton loader displayed when switching conversations or loading chat history.
 */
export function ChatMessageSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 animate-in fade-in duration-300">
      {/* Simulated User Message */}
      <div className="flex gap-3 max-w-2xl ml-auto flex-row-reverse">
        <Skeleton className="h-7 w-7 rounded-xl shrink-0" />
        <div className="rounded-2xl px-4 py-3 bg-zinc-800/60 border border-zinc-700/40 space-y-2 w-64">
          <Skeleton className="h-3 w-full rounded" />
          <Skeleton className="h-3 w-4/5 rounded" />
        </div>
      </div>

      {/* Simulated Assistant Message */}
      <div className="flex gap-3 max-w-2xl mr-auto">
        <Skeleton className="h-7 w-7 rounded-xl shrink-0" />
        <div className="rounded-2xl px-4 py-3.5 bg-zinc-900/60 border border-zinc-800/60 space-y-3 w-96">
          {/* Tool badge placeholder */}
          <div className="flex items-center gap-2 pb-2 border-b border-zinc-800/50">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-3 w-36 rounded" />
          </div>
          <Skeleton className="h-3 w-full rounded" />
          <Skeleton className="h-3 w-5/6 rounded" />
          <Skeleton className="h-3 w-3/4 rounded" />
          <div className="flex justify-between pt-1">
            <Skeleton className="h-2 w-12 rounded" />
            <Skeleton className="h-2 w-16 rounded" />
          </div>
        </div>
      </div>

      {/* Simulated User Message 2 */}
      <div className="flex gap-3 max-w-2xl ml-auto flex-row-reverse">
        <Skeleton className="h-7 w-7 rounded-xl shrink-0" />
        <div className="rounded-2xl px-4 py-3 bg-zinc-800/60 border border-zinc-700/40 space-y-1.5 w-48">
          <Skeleton className="h-3 w-full rounded" />
        </div>
      </div>

      {/* Simulated Assistant Message 2 */}
      <div className="flex gap-3 max-w-2xl mr-auto">
        <Skeleton className="h-7 w-7 rounded-xl shrink-0" />
        <div className="rounded-2xl px-4 py-3.5 bg-zinc-900/60 border border-zinc-800/60 space-y-2.5 w-80">
          <Skeleton className="h-3 w-full rounded" />
          <Skeleton className="h-3 w-2/3 rounded" />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for Document knowledge base table.
 */
export function DocumentTableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/60"
        >
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-xl" />
            <div className="space-y-1.5">
              <Skeleton className="h-3.5 w-44 rounded" />
              <Skeleton className="h-2.5 w-24 rounded" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-7 w-7 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton loader for code viewers or repository file trees.
 */
export function CodeViewerSkeleton() {
  return (
    <div className="p-4 space-y-2.5 font-mono">
      <Skeleton className="h-3 w-1/4 rounded" />
      <Skeleton className="h-3 w-1/2 rounded" />
      <Skeleton className="h-3 w-3/4 rounded" />
      <Skeleton className="h-3 w-2/5 rounded" />
      <Skeleton className="h-3 w-4/5 rounded" />
      <Skeleton className="h-3 w-3/5 rounded" />
      <Skeleton className="h-3 w-1/3 rounded" />
    </div>
  );
}

/**
 * Skeleton loader for tasks cards.
 */
export function TaskCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/60 space-y-2.5"
        >
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-40 rounded" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-3 w-3/4 rounded" />
          <div className="flex items-center gap-3 pt-2">
            <Skeleton className="h-2.5 w-20 rounded" />
            <Skeleton className="h-2.5 w-16 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
