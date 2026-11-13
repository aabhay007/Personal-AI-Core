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
} from 'lucide-react';

const MODEL_OPTIONS = [
  { provider: 'groq', model: 'llama-3.3-70b-versatile', label: 'Groq: Llama 3.3 70B (Fast & Free)' },
  { provider: 'groq', model: 'llama-3.1-8b-instant', label: 'Groq: Llama 3.1 8B Instant (Ultra-fast)' },
  { provider: 'groq', model: 'mixtral-8x7b-32768', label: 'Groq: Mixtral 8x7B (32k Context)' },
  { provider: 'openai', model: 'gpt-4o', label: 'OpenAI: GPT-4o' },
  { provider: 'openai', model: 'gpt-4o-mini', label: 'OpenAI: GPT-4o Mini' },
];

interface ToolEventItem {
  tool_name: string;
  arguments?: any;
  result?: any;
  status: 'running' | 'done';
}

export default function ChatPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [selectedModelKey, setSelectedModelKey] = useState('groq:llama-3.3-70b-versatile');
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activeToolEvents, setActiveToolEvents] = useState<ToolEventItem[]>([]);

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
        setLoading(false);
      }
    }
    init();
  }, [router]);

  // Load conversations when active workspace changes
  useEffect(() => {
    if (!activeWorkspace) return;
    async function loadConversations() {
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
      }
    }
    loadConversations();
  }, [activeWorkspace]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming, activeToolEvents]);

  const selectConversation = async (conversationId: string) => {
    if (streaming && abortStreamRef.current) {
      abortStreamRef.current();
      setStreaming(false);
    }
    setStreamError(null);
    setActiveToolEvents([]);
    try {
      const details = await getConversation(conversationId);
      setActiveConversation(details);
      setMessages(details.messages || []);
      if (details.model_provider && details.model_name) {
        setSelectedModelKey(`${details.model_provider}:${details.model_name}`);
      }
    } catch (err) {
      console.error('Failed to select conversation', err);
    }
  };

  const handleNewConversation = async () => {
    if (!activeWorkspace) return;
    const [provider, model] = selectedModelKey.split(':');
    try {
      const newConv = await createConversation(activeWorkspace.id, 'New Conversation', provider, model);
      setConversations([newConv, ...conversations]);
      setActiveConversation(newConv);
      setMessages([]);
      setStreamError(null);
      setActiveToolEvents([]);
    } catch (err) {
      console.error('Failed to create conversation', err);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await deleteConversation(conversationId);
      const remaining = conversations.filter((c) => c.id !== conversationId);
      setConversations(remaining);
      if (activeConversation?.id === conversationId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConversation(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation', err);
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

    const [provider, model] = selectedModelKey.split(':');

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
          { tool_name: data.tool_name, arguments: data.arguments, status: 'running' },
        ]);
      },
      onToolResult: (data) => {
        setActiveToolEvents((prev) =>
          prev.map((t) =>
            t.tool_name === data.tool_name ? { ...t, result: data.result, status: 'done' } : t
          )
        );
      },
      onComplete: (data) => {
        setStreaming(false);
        abortStreamRef.current = null;
        if (data.message_id) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempAssistantId
                ? {
                    ...m,
                    id: data.message_id!,
                    token_usage: data.token_usage,
                  }
                : m
            )
          );
        }
      },
      onError: (err: string) => {
        setStreaming(false);
        abortStreamRef.current = null;
        setStreamError(err);
      },
    });

    abortStreamRef.current = cancel;
  };

  const handleStopGeneration = () => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
    }
    setStreaming(false);
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mr-2" />
        <span>Loading workspace...</span>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
        <div>
          {/* Workspace info & New Chat button */}
          <div className="p-4 border-b border-slate-800">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-xs text-white">
                AI
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">{activeWorkspace?.name}</p>
                <p className="text-[10px] text-slate-400">Personal AI Core • V1</p>
              </div>
            </div>

            <button
              onClick={handleNewConversation}
              className="w-full py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2 shadow-sm cursor-pointer mb-2"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Conversation</span>
            </button>

            <div className="grid grid-cols-4 gap-1 mb-2">
              <Link
                href="/documents"
                className="py-1.5 px-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-medium transition-colors flex items-center justify-center gap-1 border border-slate-700/60 truncate"
              >
                <FileText className="h-3 w-3 text-indigo-400 shrink-0" />
                <span className="truncate">Docs</span>
              </Link>
              <Link
                href="/tools"
                className="py-1.5 px-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-medium transition-colors flex items-center justify-center gap-1 border border-slate-700/60 truncate"
              >
                <Wrench className="h-3 w-3 text-indigo-400 shrink-0" />
                <span className="truncate">Tools</span>
              </Link>
              <Link
                href="/integrations"
                className="py-1.5 px-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-medium transition-colors flex items-center justify-center gap-1 border border-slate-700/60 truncate"
              >
                <Database className="h-3 w-3 text-indigo-400 shrink-0" />
                <span className="truncate">Data</span>
              </Link>
              <Link
                href="/repositories"
                className="py-1.5 px-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-medium transition-colors flex items-center justify-center gap-1 border border-slate-700/60 truncate"
              >
                <Code2 className="h-3 w-3 text-indigo-400 shrink-0" />
                <span className="truncate">Repos</span>
              </Link>
            </div>
          </div>

          {/* Conversation list */}
          <div className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-250px)]">
            <p className="text-[11px] font-medium text-slate-400 px-3 py-1.5 uppercase tracking-wider">
              Conversations
            </p>
            {conversations.length === 0 ? (
              <p className="text-xs text-slate-500 px-3 py-2 italic">No conversations yet</p>
            ) : (
              conversations.map((conv) => {
                const isActive = activeConversation?.id === conv.id;
                return (
                  <div
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                      isActive
                        ? 'bg-slate-800 text-white font-medium'
                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate mr-2">
                      <MessageSquare className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                      <span className="truncate">{conv.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-1 transition-opacity cursor-pointer"
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
        <div className="p-3 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <div className="flex items-center gap-2 truncate">
            <div className="h-7 w-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-300">
              <UserIcon className="h-3.5 w-3.5" />
            </div>
            <div className="truncate">
              <p className="text-xs font-medium text-slate-200 truncate">{currentUser?.email}</p>
              <p className="text-[10px] text-slate-400 truncate">{currentUser?.full_name || 'Active'}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-800 transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>

      {/* Main Chat View */}
      <main className="flex-1 flex flex-col h-full bg-slate-950">
        {activeConversation ? (
          <>
            {/* Conversation Header & Model Selector */}
            <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">{activeConversation.title}</h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[11px] text-slate-400">
                    Workspace: <strong className="text-slate-300 font-medium">{activeWorkspace?.name}</strong>
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-[11px] text-indigo-400 font-medium">Tools Enabled (Calculator, DateTime)</span>
                </div>
              </div>

              {/* Model Selector */}
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-slate-400" />
                <select
                  value={selectedModelKey}
                  onChange={(e) => setSelectedModelKey(e.target.value)}
                  disabled={streaming}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
                >
                  {MODEL_OPTIONS.map((opt) => (
                    <option key={`${opt.provider}:${opt.model}`} value={`${opt.provider}:${opt.model}`}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Error Banner */}
            {streamError && (
              <div className="px-6 py-3 bg-rose-950/40 border-b border-rose-800/60 text-xs text-rose-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                  <span>{streamError}</span>
                </div>
                <button
                  onClick={() => setStreamError(null)}
                  className="text-slate-400 hover:text-slate-200 text-xs underline cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 max-w-md mx-auto">
                  <Bot className="h-10 w-10 text-slate-600 mb-3" />
                  <p className="text-sm font-medium text-slate-300">Tool-Augmented AI Assistant</p>
                  <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                    Try asking: <code className="text-indigo-400">&quot;What is 45 * 128?&quot;</code> or{' '}
                    <code className="text-indigo-400">&quot;What is the current time in Tokyo?&quot;</code>
                  </p>
                </div>
              ) : (
                messages.map((msg, index) => {
                  const isUser = msg.role === 'user';
                  const isLast = index === messages.length - 1;
                  const isCurrentStreaming = streaming && isLast && msg.role === 'assistant' && !msg.content;

                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
                    >
                      <div
                        className={`h-7 w-7 rounded-lg shrink-0 flex items-center justify-center text-xs ${
                          isUser
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {isUser ? <UserIcon className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                      </div>
                      <div
                        className={`rounded-xl px-4 py-3 text-xs leading-relaxed max-w-xl ${
                          isUser
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-900 border border-slate-800 text-slate-200 shadow-sm'
                        }`}
                      >
                        {/* Tool Execution Badges during live streaming */}
                        {isLast && activeToolEvents.length > 0 && (
                          <div className="space-y-1.5 mb-2.5 pb-2.5 border-b border-slate-800">
                            {activeToolEvents.map((t, idx) => (
                              <div
                                key={idx}
                                className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-slate-950/80 border border-slate-800 font-mono text-[11px]"
                              >
                                {t.status === 'running' ? (
                                  <>
                                    <Loader2 className="h-3 w-3 animate-spin text-indigo-400" />
                                    <span className="text-indigo-300">
                                      Invoking tool: <strong className="text-white">{t.tool_name}</strong>
                                      ({JSON.stringify(t.arguments || {})})
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                                    <span className="text-slate-300">
                                      {t.tool_name} completed:{' '}
                                      <span className="text-emerald-400">
                                        {JSON.stringify(t.result?.result || t.result || '')}
                                      </span>
                                    </span>
                                  </>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {msg.content ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : isCurrentStreaming ? (
                          <div className="flex items-center gap-1.5 py-1 text-slate-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
                            <span className="text-[11px]">Thinking & computing...</span>
                          </div>
                        ) : null}

                        <div className="flex items-center justify-between gap-3 mt-2 text-[9px] text-slate-500 opacity-75">
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

            {/* Message Input Bar */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/40">
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Ask a question or request a calculation (e.g. 'What is 15% of 850?')..."
                  disabled={streaming}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
                />
                {streaming ? (
                  <button
                    type="button"
                    onClick={handleStopGeneration}
                    className="px-4 py-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <Square className="h-3 w-3 fill-white" />
                    <span>Stop</span>
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!inputValue.trim()}
                    className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shadow-sm"
                  >
                    <Send className="h-3.5 w-3.5" />
                    <span>Send</span>
                  </button>
                )}
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <Layers className="h-12 w-12 text-slate-700 mb-3" />
            <h3 className="text-sm font-semibold text-slate-300">No Conversation Selected</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              Click &quot;New Conversation&quot; in the sidebar to start a new chat thread.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
