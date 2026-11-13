import { AgentTask, AgentTaskCreate } from '@/types/task';
import { getAccessToken } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function listTasks(workspaceId: string): Promise<AgentTask[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load tasks');
  return res.json();
}

export async function createTask(
  workspaceId: string,
  data: AgentTaskCreate
): Promise<AgentTask> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks?workspace_id=${workspaceId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to create task');
  }
  return res.json();
}

export async function getTask(taskId: string): Promise<AgentTask> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load task details');
  return res.json();
}

export async function runTask(taskId: string): Promise<AgentTask> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/run`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to execute task');
  }
  return res.json();
}

export async function approveStep(taskId: string, stepId: string): Promise<AgentTask> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/steps/${stepId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Approval failed');
  }
  return res.json();
}

export async function rejectStep(
  taskId: string,
  stepId: string,
  reason: string = 'User rejected action'
): Promise<AgentTask> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/steps/${stepId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved: false, reason }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Rejection failed');
  }
  return res.json();
}
