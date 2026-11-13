import { Workspace, Conversation, Message } from '@/types/auth';
import { getAccessToken } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load workspaces');
  return res.json();
}

export async function listConversations(workspaceId: string): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load conversations');
  return res.json();
}

export async function createConversation(workspaceId: string, title?: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      workspace_id: workspaceId,
      title: title || 'New Conversation',
      model_provider: 'openai',
      model_name: 'gpt-4o',
    }),
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return res.json();
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load conversation details');
  return res.json();
}

export async function addMessage(conversationId: string, role: string, content: string): Promise<Message> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ role, content }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
}
