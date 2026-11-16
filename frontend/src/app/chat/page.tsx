'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { User, Workspace, Conversation, Message } from '@/types/auth';
import { getMe, logout } from '@/services/auth';
import {
  listWorkspaces,
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  streamChatMessage,
} from '@/services/conversations';
import { useToast } from '@/components/Toast';
import { ConfirmModal } from '@/components/ConfirmModal';
import {
  ConversationListSkeleton,
  ChatMessageSkeleton,
} from '@/components/Skeleton';
import { ToolExecutionBadge, ToolExecutionEvent } from '@/components/ToolExecutionBadge';
import { MarkdownMessage } from '@/components/MarkdownMessage';
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  LogOut,
  Layers,
  Bot,
  User as UserIcon,
  Loader2,
  Sparkles,
  Square,
  Cpu,
  AlertCircle,
  Wrench,
  CheckCircle2,
  FileText,
  Database,
  Code2,
  Workflow,
} from 'lucide-react';

const MODEL_OPTIONS = [
  { provider: 'groq', model: 'qwen/qwen3.8-27b', label: 'Groq: Qwen 3.8 27B (Fast & High Intelligence)' },
  { provider: 'groq', model: 'llama-3.1-8b-instant', label: 'Groq: Llama 3.1 8B Instant (Ultra-fast)' },
  { provider: 'groq', model: 'mixtral-8x7b-32768', label: 'Groq: Mixtral 8x7B (32k Context)' },
  { provider: 'openai', model: 'gpt-4o', label: 'OpenAI: GPT-4o' },
  { provider: 'openai', model: 'gpt-4o-mini', label: 'OpenAI: GPT-4o Mini' },
];

const DEFAULT_MODEL_KEY = `${MODEL_OPTIONS[0].provider}:${MODEL_OPTIONS[0].model}`;

function parseModelKey(key: string): { provider: string; model: string } {
  const colonIndex = key.indexOf(':');
  if (colonIndex === -1) {
    return { provider: 'groq', model: key };
  }
  return {
    provider: key.slice(0, colonIndex),
    model: key.slice(colonIndex + 1),
  };
}

export default function ChatPage() {
  const router = useRouter();
  const toast = useToast();

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  
  // Loading states
  const [initialLoading, setInitialLoading] = useState(true);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [isConversationLoading, setIsConversationLoading] = useState(false);
  const [loadingConvId, setLoadingConvId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  
  // Delete modal state
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [selectedModelKey, setSelectedModelKey] = useState(DEFAULT_MODEL_KEY);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activeToolEvents, setActiveToolEvents] = useState<ToolExecutionEvent[]>([]);

  const abortStreamRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initial authentication & workspace loading
  useEffect(() => {
    async function init() {
      try {
        const user = await getMe();
        setCurrentUser(user);

        const wsList = await listWorkspaces();
        setWorkspaces(wsList);
        if (wsList.length > 0) {
          setActiveWorkspace(wsList[0]);
        }
      } catch {
        router.push('/login');
      } finally {
        setInitialLoading(false);
      }
    }
    init();
  }, [router]);

  // Load conversations when active workspace changes
  useEffect(() => {
    if (!activeWorkspace) return;
    async function loadConversations() {
      setConversationsLoading(true);
      try {
        const list = await listConversations(activeWorkspace!.id);
        setConversations(list);
        if (list.length > 0) {
          selectConversation(list[0].id);
        } else {
          setActiveConversation(null);
          setMessages([]);
        }
      } catch (err) {
        console.error('Failed to load conversations', err);
        toast.error('Failed to load workspace conversations');
      } finally {
        setConversationsLoading(false);
      }
    }
    loadConversations();
  }, [activeWorkspace]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming, activeToolEvents, isConversationLoading]);

  const selectConversation = async (conversationId: string) => {
    if (streaming && abortStreamRef.current) {
      abortStreamRef.current();
      setStreaming(false);
    }
    setStreamError(null);
    setActiveToolEvents([]);
    setIsConversationLoading(true);
    setLoadingConvId(conversationId);

    try {
      const details = await getConversation(conversationId);
      setActiveConversation(details);
      setMessages(details.messages || []);
      if (details.model_provider && details.model_name) {
        let provider = details.model_provider;
        let model = details.model_name;

        // Normalize legacy or deprecated model names
        if (model === 'llama-3.3-70b-versatile' || model === 'qwen3.8-27b' || model === 'qwen-3.8-27b') {
          provider = 'groq';
          model = 'qwen/qwen3.8-27b';
        }

        const exists = MODEL_OPTIONS.some(
          (opt) => opt.provider === provider && opt.model === model
        );

        if (exists) {
          setSelectedModelKey(`${provider}:${model}`);
        } else {
          setSelectedModelKey(DEFAULT_MODEL_KEY);
        }
      } else {
        setSelectedModelKey(DEFAULT_MODEL_KEY);
      }
    } catch (err) {
      console.error('Failed to select conversation', err);
      toast.error('Could not open conversation');
    } finally {
      setIsConversationLoading(false);
      setLoadingConvId(null);
    }
  };

  const handleNewConversation = async () => {
    if (!activeWorkspace) return;
    const { provider, model } = parseModelKey(selectedModelKey);
    try {
      const newConv = await createConversation(activeWorkspace.id, 'New Conversation', provider, model);
      setConversations([newConv, ...conversations]);
      setActiveConversation(newConv);
      setMessages([]);
      setStreamError(null);
      setActiveToolEvents([]);
      toast.success('New conversation created');
    } catch (err) {
      console.error('Failed to create conversation', err);
      toast.error('Failed to create conversation');
    }
  };

  const triggerDeleteConfirm = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    setDeleteTargetId(conversationId);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await deleteConversation(deleteTargetId);
      const remaining = conversations.filter((c) => c.id !== deleteTargetId);
      setConversations(remaining);
      if (activeConversation?.id === deleteTargetId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConversation(null);
          setMessages([]);
        }
      }
      toast.success('Conversation deleted');
    } catch (err) {
      console.error('Failed to delete conversation', err);
      toast.error('Failed to delete conversation');
    } finally {
      setIsDeleting(false);
      setDeleteTargetId(null);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !activeConversation || streaming) return;

    const userText = inputValue.trim();
    setInputValue('');
    setStreamError(null);
    setStreaming(true);
    setActiveToolEvents([]);

    const { provider, model } = parseModelKey(selectedModelKey);

    // 1. Optimistically display user message
    const tempUserMsg: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: activeConversation.id,
      role: 'user',
      content: userText,
      created_at: new Date().toISOString(),
    };

    // 2. Optimistically prepare placeholder assistant message
    const tempAssistantId = `temp-assistant-${Date.now()}`;
    const tempAssistantMsg: Message = {
      id: tempAssistantId,
      conversation_id: activeConversation.id,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg, tempAssistantMsg]);

    // 3. Initiate SSE stream
    const cancel = streamChatMessage({
      conversationId: activeConversation.id,
      prompt: userText,
      provider,
      model,
      onDelta: (delta: string) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === tempAssistantId ? { ...m, content: m.content + delta } : m
          )
        );
      },
      onToolStart: (data) => {
        setActiveToolEvents((prev) => [
          ...prev,
          {
            tool_name: data.tool_name,
            arguments: data.arguments,
            status: 'running',
          },
        ]);
      },
      onToolResult: (data) => {
        setActiveToolEvents((prev) =>
          prev.map((t) =>
            t.tool_name === data.tool_name && t.status === 'running'
              ? { ...t, result: data.result, status: 'done' }
              : t
          )
        );
      },
      onComplete: (data) => {
        setStreaming(false);
        abortStreamRef.current = null;
        if (data.message_id) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempAssistantId ? { ...m, id: data.message_id! } : m
            )
          );
        }
      },
      onError: (errMsg: string) => {
        setStreaming(false);
        abortStreamRef.current = null;
        setStreamError(errMsg);
        toast.error(errMsg);
      },
    });

    abortStreamRef.current = cancel;
  };

  const handleStopGeneration = () => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
      setStreaming(false);
      toast.info('Generation cancelled');
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="flex h-screen bg-[#090a0f] text-zinc-100 overflow-hidden font-sans">
      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteTargetId)}
        title="Delete Conversation"
        message="Are you sure you want to delete this conversation? All chat messages and tool logs will be permanently deleted."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />

      {/* Sidebar */}
      <aside className="w-72 bg-[#0d1017] border-r border-white/[0.08] flex flex-col justify-between shrink-0 select-none">
        <div>
          {/* Workspace info & New Chat button */}
          <div className="p-4 border-b border-white/[0.08]">
            <div className="flex items-center gap-2.5 mb-3.5">
              <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center font-bold text-xs text-white shadow-md shadow-indigo-500/20">
                AI
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate tracking-tight">
                  {activeWorkspace?.name || 'Workspace'}
                </p>
                <div className="flex items-center gap-1.5 text-[10px] text-zinc-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  <span>Personal AI Core</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleNewConversation}
              className="w-full py-2.5 px-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-2 shadow-sm shadow-indigo-950/40 cursor-pointer mb-3"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Conversation</span>
            </button>

            {/* Quick Navigation Pill Grid */}
            <div className="space-y-1">
              <div className="grid grid-cols-3 gap-1">
                <Link
                  href="/documents"
                  className="py-1.5 px-1 bg-white/[0.03] hover:bg-white/[0.08] text-zinc-300 rounded-lg text-[11px] font-medium transition-all flex items-center justify-center gap-1 border border-white/[0.05]"
                >
                  <FileText className="h-3 w-3 text-indigo-400 shrink-0" />
                  <span>Docs</span>
                </Link>
                <Link
                  href="/tools"
                  className="py-1.5 px-1 bg-white/[0.03] hover:bg-white/[0.08] text-zinc-300 rounded-lg text-[11px] font-medium transition-all flex items-center justify-center gap-1 border border-white/[0.05]"
                >
                  <Wrench className="h-3 w-3 text-indigo-400 shrink-0" />
                  <span>Tools</span>
                </Link>
                <Link
                  href="/integrations"
                  className="py-1.5 px-1 bg-white/[0.03] hover:bg-white/[0.08] text-zinc-300 rounded-lg text-[11px] font-medium transition-all flex items-center justify-center gap-1 border border-white/[0.05]"
                >
                  <Database className="h-3 w-3 text-indigo-400 shrink-0" />
                  <span>Data</span>
                </Link>
              </div>

              <div className="grid grid-cols-2 gap-1">
                <Link
                  href="/repositories"
                  className="py-1.5 px-1 bg-white/[0.03] hover:bg-white/[0.08] text-zinc-300 rounded-lg text-[11px] font-medium transition-all flex items-center justify-center gap-1.5 border border-white/[0.05]"
                >
                  <Code2 className="h-3 w-3 text-indigo-400 shrink-0" />
                  <span>Repos</span>
                </Link>
                <Link
                  href="/tasks"
                  className="py-1.5 px-1 bg-white/[0.03] hover:bg-white/[0.08] text-zinc-300 rounded-lg text-[11px] font-medium transition-all flex items-center justify-center gap-1.5 border border-white/[0.05]"
                >
                  <Workflow className="h-3 w-3 text-indigo-400 shrink-0" />
                  <span>Tasks</span>
                </Link>
              </div>
            </div>
          </div>

          {/* Conversation List Section */}
          <div className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-270px)]">
            <p className="text-[10px] font-semibold text-zinc-500 px-3 py-1.5 uppercase tracking-wider">
              Conversations
            </p>

            {initialLoading || conversationsLoading ? (
              <ConversationListSkeleton count={4} />
            ) : conversations.length === 0 ? (
              <p className="text-xs text-zinc-500 px-3 py-4 italic text-center">
                No conversations yet
              </p>
            ) : (
              conversations.map((conv) => {
                const isActive = activeConversation?.id === conv.id;
                const isLoadingThis = isConversationLoading && loadingConvId === conv.id;

                return (
                  <div
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                      isActive
                        ? 'bg-white/[0.08] text-white font-medium border-l-2 border-indigo-500 shadow-sm'
                        : 'text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate mr-2">
                      {isLoadingThis ? (
                        <Loader2 className="h-3.5 w-3.5 shrink-0 text-indigo-400 animate-spin" />
                      ) : (
                        <MessageSquare
                          className={`h-3.5 w-3.5 shrink-0 transition-colors ${
                            isActive ? 'text-indigo-400' : 'text-zinc-500 group-hover:text-zinc-300'
                          }`}
                        />
                      )}
                      <span className="truncate">{conv.title}</span>
                    </div>

                    <button
                      onClick={(e) => triggerDeleteConfirm(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-1 rounded transition-opacity cursor-pointer text-zinc-500"
                      title="Delete conversation"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="p-3 border-t border-white/[0.08] bg-[#090a0f]/80 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-2.5 truncate">
            <div className="h-8 w-8 rounded-full bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-xs text-zinc-300">
              <UserIcon className="h-3.5 w-3.5" />
            </div>
            <div className="truncate">
              <p className="text-xs font-medium text-zinc-200 truncate">{currentUser?.email || 'User'}</p>
              <p className="text-[10px] text-zinc-400 truncate">{currentUser?.full_name || 'Active'}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-zinc-400 hover:text-rose-400 rounded-lg hover:bg-white/[0.05] transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>

      {/* Main Chat View */}
      <main className="flex-1 flex flex-col h-full bg-[#090a0f]">
        {/* Header Bar */}
        <div className="px-6 py-3 border-b border-white/[0.08] bg-[#0d1017]/60 backdrop-blur flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-tight">
              {activeConversation?.title || 'Personal AI Workspace'}
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[11px] text-zinc-400">
                Workspace: <strong className="text-zinc-200 font-medium">{activeWorkspace?.name || 'Default'}</strong>
              </span>
              <span className="text-zinc-600">•</span>
              <span className="text-[11px] text-indigo-400 font-medium">Tools & RAG Knowledge Active</span>
            </div>
          </div>

          {/* Model Selector */}
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-zinc-400" />
            <select
              value={selectedModelKey}
              onChange={(e) => setSelectedModelKey(e.target.value)}
              disabled={streaming}
              className="bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm hover:border-white/[0.15] transition-colors"
            >
              {MODEL_OPTIONS.map((opt) => (
                <option key={`${opt.provider}:${opt.model}`} value={`${opt.provider}:${opt.model}`}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Error Notification Banner if stream fails */}
        {streamError && (
          <div className="px-6 py-2.5 bg-rose-950/40 border-b border-rose-800/40 text-xs text-rose-300 flex items-center justify-between animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{streamError}</span>
            </div>
            <button
              onClick={() => setStreamError(null)}
              className="text-zinc-400 hover:text-white text-xs underline cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Messages or Skeleton Area */}
        {initialLoading || isConversationLoading ? (
          <ChatMessageSkeleton />
        ) : activeConversation ? (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-500 max-w-md mx-auto py-16">
                <div className="h-12 w-12 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center mb-4 text-indigo-400 shadow-xl">
                  <Bot className="h-6 w-6" />
                </div>
                <h3 className="text-base font-semibold text-zinc-200 tracking-tight">
                  Autonomous Developer Assistant
                </h3>
                <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                  Ask questions about your uploaded documents, codebase repositories, databases, or run calculations.
                </p>
                <div className="mt-5 grid grid-cols-1 gap-2 w-full text-left">
                  <button
                    onClick={() => setInputValue('Search my documents for relevant information')}
                    className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.06] transition-colors text-xs text-zinc-300 text-left flex items-center justify-between group cursor-pointer"
                  >
                    <span>&quot;Search my documents for...&quot;</span>
                    <Sparkles className="h-3.5 w-3.5 text-indigo-400 opacity-60 group-hover:opacity-100" />
                  </button>
                  <button
                    onClick={() => setInputValue('What is 45 * 128?')}
                    className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.06] transition-colors text-xs text-zinc-300 text-left flex items-center justify-between group cursor-pointer"
                  >
                    <span>&quot;What is 45 * 128?&quot;</span>
                    <Sparkles className="h-3.5 w-3.5 text-indigo-400 opacity-60 group-hover:opacity-100" />
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                const isLast = index === messages.length - 1;
                const isCurrentStreaming = streaming && isLast && msg.role === 'assistant' && !msg.content;

                return (
                  <div
                    key={msg.id}
                    className={`flex gap-3.5 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
                  >
                    {/* Avatar */}
                    <div
                      className={`h-7 w-7 rounded-xl shrink-0 flex items-center justify-center text-xs ${
                        isUser
                          ? 'bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-sm shadow-indigo-500/20'
                          : 'bg-white/[0.04] text-zinc-300 border border-white/[0.08]'
                      }`}
                    >
                      {isUser ? <UserIcon className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5 text-indigo-400" />}
                    </div>

                    {/* Message Bubble */}
                    <div
                      className={`rounded-2xl px-4 py-3.5 text-xs leading-relaxed max-w-xl transition-all ${
                        isUser
                          ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-950/40'
                          : 'bg-[#11141e]/90 border border-white/[0.08] text-zinc-200 shadow-sm'
                      }`}
                    >
                      {/* Live Tool Execution Badges during Assistant streaming */}
                      {!isUser && isLast && activeToolEvents.length > 0 && (
                        <div className="space-y-1.5 mb-3 pb-2 border-b border-white/[0.06]">
                          {activeToolEvents.map((t, idx) => (
                            <ToolExecutionBadge key={idx} event={t} />
                          ))}
                        </div>
                      )}

                      {/* Content */}
                      {isUser ? (
                        <p className="whitespace-pre-wrap font-normal">{msg.content}</p>
                      ) : msg.content ? (
                        <MarkdownMessage content={msg.content} />
                      ) : isCurrentStreaming ? (
                        <div className="flex items-center gap-2 py-1 text-zinc-400">
                          <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse"></span>
                          <span className="text-xs">Processing request and tools...</span>
                        </div>
                      ) : null}

                      {/* Footer Info */}
                      <div className="flex items-center justify-between gap-3 mt-2 text-[10px] text-zinc-500">
                        <span>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        {msg.token_usage && typeof msg.token_usage === 'object' && 'total_tokens' in msg.token_usage && (
                          <span className="font-mono text-indigo-400/80">
                            Tokens: {String(msg.token_usage.total_tokens)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-zinc-500">
            <Layers className="h-12 w-12 text-zinc-700 mb-3" />
            <h3 className="text-sm font-semibold text-zinc-300">No Conversation Selected</h3>
            <p className="text-xs text-zinc-500 mt-1 max-w-xs">
              Click &quot;New Conversation&quot; in the sidebar to start a new chat thread.
            </p>
          </div>
        )}

        {/* Message Input Dock */}
        <div className="p-4 border-t border-white/[0.08] bg-[#0d1017]/40 backdrop-blur">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-2.5">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask a question, search documents, or inspect repositories..."
              disabled={streaming}
              className="flex-1 bg-[#131722] border border-white/[0.08] rounded-xl px-4 py-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all disabled:opacity-50 shadow-inner"
            />
            {streaming ? (
              <button
                type="button"
                onClick={handleStopGeneration}
                className="px-4 py-3 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer shadow-md shadow-rose-950/40"
              >
                <Square className="h-3 w-3 fill-white" />
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputValue.trim()}
                className="px-4 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shadow-md shadow-indigo-950/40"
              >
                <Send className="h-3.5 w-3.5" />
                <span>Send</span>
              </button>
            )}
          </form>
        </div>
      </main>
    </div>
  );
}
