'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { User, Workspace, Conversation, Message } from '@/types/auth';
import { getMe, logout } from '@/services/auth';
import {
  listWorkspaces,
  listConversations,
  createConversation,
  getConversation,
  addMessage,
  deleteConversation,
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
} from 'lucide-react';

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
  const [sending, setSending] = useState(false);
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

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const selectConversation = async (conversationId: string) => {
    try {
      const details = await getConversation(conversationId);
      setActiveConversation(details);
      setMessages(details.messages || []);
    } catch (err) {
      console.error('Failed to select conversation', err);
    }
  };

  const handleNewConversation = async () => {
    if (!activeWorkspace) return;
    try {
      const newConv = await createConversation(activeWorkspace.id, 'New Conversation');
      setConversations([newConv, ...conversations]);
      setActiveConversation(newConv);
      setMessages([]);
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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !activeConversation || sending) return;

    const userText = inputValue.trim();
    setInputValue('');
    setSending(true);

    try {
      // 1. Persist user message
      const userMsg = await addMessage(activeConversation.id, 'user', userText);
      setMessages((prev) => [...prev, userMsg]);

      // 2. Persist assistant confirmation (Phase 1 verification response)
      const assistantMsg = await addMessage(
        activeConversation.id,
        'assistant',
        `[Phase 1 Active] Received and persisted: "${userText}". Full LLM streaming orchestration activates in Phase 2.`
      );
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Failed to send message', err);
    } finally {
      setSending(false);
    }
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
                <p className="text-[10px] text-slate-400">Workspace Isolation Enabled</p>
              </div>
            </div>

            <button
              onClick={handleNewConversation}
              className="w-full py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2 shadow-sm cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Conversation</span>
            </button>
          </div>

          {/* Conversation list */}
          <div className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-210px)]">
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
            {/* Conversation Header */}
            <div className="px-6 py-3.5 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">{activeConversation.title}</h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
                    <Sparkles className="h-3 w-3 text-indigo-400" />
                    {activeConversation.model_provider} / {activeConversation.model_name}
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-[11px] text-slate-500">
                    Workspace: {activeWorkspace?.name}
                  </span>
                </div>
              </div>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 max-w-sm mx-auto">
                  <Bot className="h-10 w-10 text-slate-600 mb-3" />
                  <p className="text-sm font-medium text-slate-300">Conversation Initialized</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Send a message below. Conversations and messages are persisted in Neon PostgreSQL.
                  </p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === 'user';
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
                        className={`rounded-xl px-4 py-2.5 text-xs leading-relaxed max-w-xl ${
                          isUser
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-900 border border-slate-800 text-slate-200'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        <span className="block text-[9px] text-slate-400 mt-1.5 opacity-75">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
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
                  placeholder="Type a message..."
                  disabled={sending}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!inputValue.trim() || sending}
                  className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shadow-sm"
                >
                  {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  <span>Send</span>
                </button>
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
