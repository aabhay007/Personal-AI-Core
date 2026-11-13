'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AgentTask, AgentStep, AgentTaskCreate } from '@/types/task';
import { Workspace } from '@/types/auth';
import { getMe } from '@/services/auth';
import { listWorkspaces } from '@/services/conversations';
import {
  listTasks,
  createTask,
  getTask,
  runTask,
  approveStep,
  rejectStep,
} from '@/services/tasks';
import {
  Workflow,
  Plus,
  Play,
  RotateCw,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldAlert,
  Loader2,
  ChevronDown,
  ChevronRight,
  Terminal,
  Check,
  X,
  Sparkles,
  Layers,
} from 'lucide-react';

export default function TasksPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<AgentTask | null>(null);
  const [loading, setLoading] = useState(true);

  // Execution states
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [approvingStepId, setApprovingStepId] = useState<string | null>(null);
  const [rejectingStepId, setRejectingStepId] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskGoal, setTaskGoal] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

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
    loadTasks();
  }, [activeWorkspace]);

  async function loadTasks() {
    if (!activeWorkspace) return;
    try {
      const list = await listTasks(activeWorkspace.id);
      setTasks(list);
      if (list.length > 0 && !selectedTask) {
        selectTask(list[0].id);
      }
    } catch (err) {
      console.error('Failed to load tasks', err);
    }
  }

  async function selectTask(taskId: string) {
    try {
      const details = await getTask(taskId);
      setSelectedTask(details);
    } catch (err) {
      console.error('Failed to get task', err);
    }
  }

  async function handleRunTask(taskId: string) {
    setRunningTaskId(taskId);
    try {
      const updated = await runTask(taskId);
      setSelectedTask(updated);
      await loadTasks();
    } catch (err) {
      console.error('Task execution failed', err);
    } finally {
      setRunningTaskId(null);
    }
  }

  async function handleApproveStep(taskId: string, stepId: string) {
    setApprovingStepId(stepId);
    try {
      const updated = await approveStep(taskId, stepId);
      setSelectedTask(updated);
      await loadTasks();
    } catch (err) {
      console.error('Approval failed', err);
    } finally {
      setApprovingStepId(null);
    }
  }

  async function handleRejectStep(taskId: string, stepId: string) {
    const reason = prompt('Please specify a rejection reason:', 'Security policy rejection');
    if (!reason) return;
    setRejectingStepId(stepId);
    try {
      const updated = await rejectStep(taskId, stepId, reason);
      setSelectedTask(updated);
      await loadTasks();
    } catch (err) {
      console.error('Rejection failed', err);
    } finally {
      setRejectingStepId(null);
    }
  }

  async function handleCreateTask(e: React.FormEvent) {
    e.preventDefault();
    if (!activeWorkspace) return;
    setCreating(true);
    setCreateError(null);

    const payload: AgentTaskCreate = {
      title: taskTitle,
      goal: taskGoal,
    };

    try {
      const created = await createTask(activeWorkspace.id, payload);
      setIsModalOpen(false);
      setTaskTitle('');
      setTaskGoal('');
      await loadTasks();
      setSelectedTask(created);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setCreating(false);
    }
  }

  function toggleStepExpand(stepId: string) {
    setExpandedSteps((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <ShieldAlert className="h-3 w-3" />
            Needs Approval
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertCircle className="h-3 w-3" />
            Failed
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            <X className="h-3 w-3" />
            Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="h-3 w-3" />
            Pending
          </span>
        );
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mr-2" />
        <span>Loading autonomous tasks...</span>
      </div>
    );
  }

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-600/20 rounded-lg text-indigo-400">
              <Workflow className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white">Autonomous Agent Tasks</h1>
              <p className="text-xs text-slate-400">
                Multi-step planning, state persistence, checkpoint retries, and Human-in-the-Loop approvals
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
              className="bg-slate-800 text-xs text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none"
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
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Task</span>
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Task List */}
        <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0">
          <div className="p-3 border-b border-slate-800 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Workflows ({tasks.length})
            </span>
            <button
              onClick={loadTasks}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200"
              title="Refresh list"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {tasks.length === 0 ? (
              <p className="text-xs text-slate-500 italic p-3">No autonomous tasks created yet</p>
            ) : (
              tasks.map((t) => {
                const isSelected = selectedTask?.id === t.id;
                const completedSteps = t.steps?.filter((s) => s.status === 'completed').length || 0;
                const totalSteps = t.steps?.length || 0;

                return (
                  <div
                    key={t.id}
                    onClick={() => selectTask(t.id)}
                    className={`p-3 rounded-xl cursor-pointer transition-colors border text-xs space-y-2 ${
                      isSelected
                        ? 'bg-indigo-600/15 border-indigo-500/40 text-white'
                        : 'bg-slate-950/40 border-slate-800/80 text-slate-300 hover:bg-slate-850 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold text-slate-100 line-clamp-1">{t.title}</p>
                      {getStatusBadge(t.status)}
                    </div>

                    <p className="text-[11px] text-slate-400 line-clamp-2">{t.goal}</p>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60 font-mono">
                      <span>
                        Steps: {completedSteps}/{totalSteps}
                      </span>
                      <span>{new Date(t.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Center / Right Details: Task DAG and Execution Timeline */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-950">
          {selectedTask ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Task Header */}
              <div className="p-5 border-b border-slate-800 bg-slate-900/40 space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-bold text-white">{selectedTask.title}</h2>
                    {getStatusBadge(selectedTask.status)}
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedTask.status !== 'completed' && selectedTask.status !== 'cancelled' && (
                      <button
                        onClick={() => handleRunTask(selectedTask.id)}
                        disabled={runningTaskId === selectedTask.id || selectedTask.status === 'waiting_approval'}
                        className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
                      >
                        {runningTaskId === selectedTask.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Play className="h-3.5 w-3.5 fill-current" />
                        )}
                        <span>{selectedTask.status === 'waiting_approval' ? 'Waiting Approval' : 'Run / Step'}</span>
                      </button>
                    )}
                  </div>
                </div>

                <div className="text-xs text-slate-300 bg-slate-900/70 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-medium">Objective: </span>
                  <span>{selectedTask.goal}</span>
                </div>

                {/* Result summary banner */}
                {selectedTask.result_summary && (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300 flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-emerald-200">Execution Complete</p>
                      <p className="text-[11px] text-emerald-300/90 mt-0.5">{selectedTask.result_summary}</p>
                    </div>
                  </div>
                )}

                {/* Error message banner */}
                {selectedTask.error_message && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-300 flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-red-200">Execution Error</p>
                      <p className="text-[11px] text-red-300/90 mt-0.5">{selectedTask.error_message}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Step Pipeline List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Sequential Execution Steps ({selectedTask.steps?.length || 0})
                </h3>

                <div className="space-y-3">
                  {selectedTask.steps?.map((step) => {
                    const isExpanded = expandedSteps[step.id];
                    const isWaiting = step.status === 'waiting_approval';
                    const isApproving = approvingStepId === step.id;
                    const isRejecting = rejectingStepId === step.id;

                    return (
                      <div
                        key={step.id}
                        className={`border rounded-xl transition-all ${
                          isWaiting
                            ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-950/30'
                            : step.status === 'completed'
                            ? 'bg-slate-900/60 border-slate-800'
                            : 'bg-slate-900/30 border-slate-800/80'
                        }`}
                      >
                        {/* Step Card Header */}
                        <div className="p-4 flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <div className="h-6 w-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-slate-300 shrink-0 mt-0.5">
                              {step.step_number}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-semibold text-white">{step.name}</h4>
                                {getStatusBadge(step.status)}
                                {step.tool_name && (
                                  <span className="font-mono text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded">
                                    {step.tool_name}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-400 mt-1">{step.description}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {step.execution_time_ms !== null && step.execution_time_ms !== undefined && (
                              <span className="text-[10px] text-slate-500 font-mono">
                                {step.execution_time_ms}ms
                              </span>
                            )}
                            <button
                              onClick={() => toggleStepExpand(step.id)}
                              className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded"
                            >
                              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </button>
                          </div>
                        </div>

                        {/* Human Approval Required Action Banner */}
                        {isWaiting && (
                          <div className="m-4 mt-0 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between gap-4">
                            <div className="flex items-center gap-2">
                              <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0" />
                              <div>
                                <p className="text-xs font-semibold text-amber-200">
                                  Human Approval Required (Sensitive Action)
                                </p>
                                <p className="text-[11px] text-amber-300/80">
                                  This step requires your explicit authorization before the autonomous runner can execute it.
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                onClick={() => handleRejectStep(selectedTask.id, step.id)}
                                disabled={isRejecting}
                                className="px-3 py-1 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 rounded-lg text-xs font-medium transition-colors"
                              >
                                {isRejecting ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Reject'}
                              </button>
                              <button
                                onClick={() => handleApproveStep(selectedTask.id, step.id)}
                                disabled={isApproving}
                                className="px-3.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium flex items-center gap-1 transition-colors"
                              >
                                {isApproving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                <span>Approve & Continue</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Expanded Step Details */}
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-1 border-t border-slate-800/80 space-y-2 text-xs font-mono">
                            {step.tool_arguments && Object.keys(step.tool_arguments).length > 0 && (
                              <div>
                                <p className="text-[11px] text-slate-500 font-sans mb-1">Tool Arguments:</p>
                                <pre className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto text-[11px]">
                                  {JSON.stringify(step.tool_arguments, null, 2)}
                                </pre>
                              </div>
                            )}

                            {step.tool_result && (
                              <div>
                                <p className="text-[11px] text-slate-500 font-sans mb-1">Execution Output:</p>
                                <pre className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto text-[11px]">
                                  {JSON.stringify(step.tool_result, null, 2)}
                                </pre>
                              </div>
                            )}

                            {step.error_message && (
                              <div>
                                <p className="text-[11px] text-red-400 font-sans mb-1">Step Error:</p>
                                <pre className="bg-red-950/20 p-2.5 rounded-lg border border-red-500/20 text-red-300 overflow-x-auto text-[11px]">
                                  {step.error_message}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs p-8 text-center">
              <Workflow className="h-12 w-12 text-slate-700 mb-3" />
              <p className="font-medium text-slate-400">No task selected</p>
              <p className="text-slate-600 max-w-sm mt-1">
                Select an autonomous workflow from the left sidebar or create a new goal.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* New Task Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Create Autonomous Task</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Task Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Audit Database & Verify Invoices"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">High-Level Objective / Goal</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe what you want the AI agent to accomplish sequentially..."
                  value={taskGoal}
                  onChange={(e) => setTaskGoal(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {createError && (
                <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="py-1.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {creating && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span>Generate Plan & Start</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
