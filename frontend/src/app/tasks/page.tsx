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
import { useToast } from '@/components/Toast';
import { TaskCardSkeleton, Skeleton } from '@/components/Skeleton';
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
  const toast = useToast();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<AgentTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [taskDetailsLoading, setTaskDetailsLoading] = useState(false);
  const [loadingTaskId, setLoadingTaskId] = useState<string | null>(null);

  // Execution states
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [approvingStepId, setApprovingStepId] = useState<string | null>(null);
  const [rejectingStepId, setRejectingStepId] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  // Reject modal state (replaces window.prompt)
  const [rejectStepData, setRejectStepData] = useState<{ taskId: string; stepId: string } | null>(null);
  const [rejectReason, setRejectReason] = useState('Security policy violation or unverified action');

  // Create Task modal state
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
      toast.error('Failed to load tasks');
    }
  }

  async function selectTask(taskId: string) {
    setTaskDetailsLoading(true);
    setLoadingTaskId(taskId);
    try {
      const details = await getTask(taskId);
      setSelectedTask(details);
    } catch (err) {
      console.error('Failed to get task', err);
      toast.error('Failed to load task details');
    } finally {
      setTaskDetailsLoading(false);
      setLoadingTaskId(null);
    }
  }

  async function handleRunTask(taskId: string) {
    setRunningTaskId(taskId);
    try {
      const updated = await runTask(taskId);
      setSelectedTask(updated);
      await loadTasks();
      toast.success('Task execution updated');
    } catch (err) {
      console.error('Task execution failed', err);
      toast.error('Task execution failed');
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
      toast.success('Step approved successfully');
    } catch (err) {
      console.error('Approval failed', err);
      toast.error('Failed to approve step');
    } finally {
      setApprovingStepId(null);
    }
  }

  async function handleConfirmReject() {
    if (!rejectStepData) return;
    setRejectingStepId(rejectStepData.stepId);
    try {
      const updated = await rejectStep(rejectStepData.taskId, rejectStepData.stepId, rejectReason);
      setSelectedTask(updated);
      await loadTasks();
      toast.success('Step rejected');
      setRejectStepData(null);
    } catch (err) {
      console.error('Rejection failed', err);
      toast.error('Failed to reject step');
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
      toast.success(`Autonomous task "${created.title}" created`);
      await loadTasks();
      setSelectedTask(created);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create task';
      setCreateError(msg);
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  }

  function toggleStepExpand(stepId: string) {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" /> Completed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
            <Loader2 className="h-3 w-3 animate-spin" /> Running
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
            <ShieldAlert className="h-3 w-3" /> Awaiting Approval
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
            <AlertCircle className="h-3 w-3" /> Failed
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
            <X className="h-3 w-3" /> Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-zinc-400 bg-white/[0.05] px-2 py-0.5 rounded-full border border-white/[0.06]">
            <Clock className="h-3 w-3" /> Pending
          </span>
        );
    }
  };

  return (
    <div className="h-screen bg-[#090a0f] text-zinc-100 flex flex-col font-sans overflow-hidden">
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
              <Workflow className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white tracking-tight">Autonomous Agent Tasks</h1>
              <p className="text-xs text-zinc-400">
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
            <span>New Task</span>
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Task List */}
        <div className="w-80 bg-[#0d1017] border-r border-white/[0.08] flex flex-col shrink-0">
          <div className="p-3.5 border-b border-white/[0.08] flex items-center justify-between">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Workflows ({tasks.length})
            </span>
            <button
              onClick={loadTasks}
              className="p-1 hover:bg-white/[0.08] rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Refresh list"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
            {loading ? (
              <TaskCardSkeleton count={3} />
            ) : tasks.length === 0 ? (
              <p className="text-xs text-zinc-500 italic p-4 text-center">No autonomous tasks created yet</p>
            ) : (
              tasks.map((t) => {
                const isSelected = selectedTask?.id === t.id;
                const isLoadingThis = taskDetailsLoading && loadingTaskId === t.id;
                const completedSteps = t.steps?.filter((s) => s.status === 'completed').length || 0;
                const totalSteps = t.steps?.length || 0;

                return (
                  <div
                    key={t.id}
                    onClick={() => selectTask(t.id)}
                    className={`p-3.5 rounded-xl cursor-pointer transition-all border text-xs space-y-2 ${
                      isSelected
                        ? 'bg-white/[0.08] border-l-2 border-indigo-500 border-white/[0.1] text-white shadow-sm'
                        : 'bg-white/[0.02] border-white/[0.04] text-zinc-300 hover:bg-white/[0.05]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 truncate">
                        {isLoadingThis && <Loader2 className="h-3 w-3 animate-spin text-indigo-400 shrink-0" />}
                        <p className="font-semibold text-white line-clamp-1">{t.title}</p>
                      </div>
                      {getStatusBadge(t.status)}
                    </div>

                    <p className="text-[11px] text-zinc-400 line-clamp-2">{t.goal}</p>

                    <div className="flex items-center justify-between text-[10px] text-zinc-500 pt-1.5 border-t border-white/[0.06] font-mono">
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
        <div className="flex-1 flex flex-col overflow-hidden bg-[#090a0f]">
          {taskDetailsLoading ? (
            <div className="p-8 space-y-6">
              <Skeleton className="h-24 w-full rounded-2xl" />
              <div className="space-y-3">
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            </div>
          ) : selectedTask ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Task Header */}
              <div className="p-6 border-b border-white/[0.08] bg-[#0d1017]/40 backdrop-blur space-y-3.5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-bold text-white tracking-tight">{selectedTask.title}</h2>
                    {getStatusBadge(selectedTask.status)}
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedTask.status !== 'completed' && selectedTask.status !== 'cancelled' && (
                      <button
                        onClick={() => handleRunTask(selectedTask.id)}
                        disabled={runningTaskId === selectedTask.id || selectedTask.status === 'waiting_approval'}
                        className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-md shadow-indigo-950/40 cursor-pointer"
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

                <div className="text-xs text-zinc-300 bg-white/[0.03] p-3.5 rounded-xl border border-white/[0.06]">
                  <span className="text-zinc-500 font-medium">Objective: </span>
                  <span>{selectedTask.goal}</span>
                </div>

                {/* Result summary banner */}
                {selectedTask.result_summary && (
                  <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-300 flex items-start gap-2.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-emerald-200">Execution Complete</p>
                      <p className="text-[11px] text-emerald-300/90 mt-0.5">{selectedTask.result_summary}</p>
                    </div>
                  </div>
                )}

                {/* Error message banner */}
                {selectedTask.error_message && (
                  <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300 flex items-start gap-2.5">
                    <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-rose-200">Execution Error</p>
                      <p className="text-[11px] text-rose-300/90 mt-0.5">{selectedTask.error_message}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Step Pipeline List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
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
                        className={`border rounded-2xl transition-all overflow-hidden ${
                          isWaiting
                            ? 'bg-amber-950/20 border-amber-500/40 shadow-lg shadow-amber-950/20'
                            : step.status === 'completed'
                            ? 'bg-[#0d1017] border-white/[0.08]'
                            : 'bg-white/[0.02] border-white/[0.04]'
                        }`}
                      >
                        {/* Step Card Header */}
                        <div className="p-4 flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <div className="h-7 w-7 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center font-bold text-xs text-zinc-300 shrink-0 mt-0.5">
                              {step.step_number}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-semibold text-white">{step.name}</h4>
                                {getStatusBadge(step.status)}
                                {step.tool_name && (
                                  <span className="font-mono text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                                    {step.tool_name}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-zinc-400 mt-1">{step.description}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {step.execution_time_ms !== null && step.execution_time_ms !== undefined && (
                              <span className="text-[10px] text-zinc-500 font-mono">
                                {step.execution_time_ms}ms
                              </span>
                            )}
                            <button
                              onClick={() => toggleStepExpand(step.id)}
                              className="p-1 hover:bg-white/[0.08] text-zinc-400 hover:text-white rounded-lg transition-colors cursor-pointer"
                            >
                              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </button>
                          </div>
                        </div>

                        {/* Interactive Approval Bar for Human-In-The-Loop */}
                        {isWaiting && (
                          <div className="px-4 py-3 bg-amber-500/10 border-t border-amber-500/20 flex items-center justify-between gap-4">
                            <div className="flex items-center gap-2 text-xs text-amber-300">
                              <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0" />
                              <span>Critical tool approval required before execution can proceed.</span>
                            </div>

                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setRejectStepData({ taskId: selectedTask.id, stepId: step.id })}
                                disabled={isRejecting || isApproving}
                                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-medium flex items-center gap-1 transition-all disabled:opacity-50 cursor-pointer shadow-sm"
                              >
                                {isRejecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                                <span>Reject</span>
                              </button>
                              <button
                                onClick={() => handleApproveStep(selectedTask.id, step.id)}
                                disabled={isApproving || isRejecting}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-medium flex items-center gap-1 transition-all disabled:opacity-50 cursor-pointer shadow-sm"
                              >
                                {isApproving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                <span>Approve</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Expandable Step Details */}
                        {isExpanded && (
                          <div className="p-4 border-t border-white/[0.06] bg-black/40 space-y-3 font-mono text-xs">
                            {step.tool_arguments && (
                              <div>
                                <span className="text-zinc-500 text-[10px] uppercase font-sans font-semibold block mb-1">
                                  Tool Input Parameters
                                </span>
                                <pre className="bg-[#08090d] p-3 rounded-xl border border-white/[0.06] text-zinc-300 overflow-x-auto text-[11px]">
                                  {JSON.stringify(step.tool_arguments, null, 2)}
                                </pre>
                              </div>
                            )}

                            {step.tool_result && (
                              <div>
                                <span className="text-zinc-500 text-[10px] uppercase font-sans font-semibold block mb-1">
                                  Execution Result
                                </span>
                                <pre className="bg-[#08090d] p-3 rounded-xl border border-white/[0.06] text-emerald-400 overflow-x-auto text-[11px]">
                                  {JSON.stringify(step.tool_result, null, 2)}
                                </pre>
                              </div>
                            )}

                            {step.error_message && (
                              <div>
                                <span className="text-rose-500 text-[10px] uppercase font-sans font-semibold block mb-1">
                                  Failure Trace
                                </span>
                                <div className="bg-rose-950/40 p-3 rounded-xl border border-rose-800/40 text-rose-300 font-sans text-xs">
                                  {step.error_message}
                                </div>
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
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 text-xs p-8 text-center">
              <Workflow className="h-12 w-12 text-zinc-700 mb-3" />
              <p className="font-medium text-zinc-400">No task selected</p>
              <p className="text-zinc-600 max-w-sm mt-1">
                Select a task from the list or create a new autonomous workflow.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Reject Step Modal (replacing window.prompt) */}
      {rejectStepData && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Reject Execution Step</h3>
                <p className="text-xs text-zinc-400 mt-1">
                  Specify a reason for rejecting this step. The workflow execution will halt safely.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">Rejection Reason</label>
              <textarea
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500 font-sans"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setRejectStepData(null)}
                className="py-2 px-3.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReject}
                className="py-2 px-4 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-medium transition-colors cursor-pointer shadow-md shadow-rose-950/40"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Workflow className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Create Autonomous Task</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Task Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Audit Repository & Inspect DB Schema"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Primary Goal / Objective</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe what the agent should accomplish across multiple steps..."
                  value={taskGoal}
                  onChange={(e) => setTaskGoal(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 leading-relaxed font-sans"
                />
              </div>

              {createError && (
                <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="py-2 px-3.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="py-2 px-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer shadow-md shadow-indigo-950/40"
                >
                  {creating && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span>Create Plan</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
