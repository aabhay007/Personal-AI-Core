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

export async function createConversation(
  workspaceId: string,
  title?: string,
  provider: string = 'groq',
  model: string = 'qwen/qwen3.8-27b'
): Promise<Conversation> {
  const res = await fetch(`${API_BASE_URL}/api/v1/conversations`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      workspace_id: workspaceId,
      title: title || 'New Conversation',
      model_provider: provider,
      model_name: model,
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

export interface ToolItem {
  name: string;
  description: string;
  parameters: Record<string, any>;
  requires_approval: boolean;
  timeout_seconds: number;
}

export async function listTools(): Promise<ToolItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tools`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to list tools');
  return res.json();
}

export interface StreamChatParams {
  conversationId: string;
  prompt: string;
  provider?: string;
  model?: string;
  onDelta: (delta: string) => void;
  onToolStart?: (data: { tool_name: string; arguments: any }) => void;
  onToolResult?: (data: { tool_name: string; result: any }) => void;
  onComplete: (data: { message_id?: string; token_usage?: any }) => void;
  onError: (error: string) => void;
}

export function streamChatMessage(params: StreamChatParams): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          conversation_id: params.conversationId,
          prompt: params.prompt,
          provider: params.provider,
          model: params.model,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        params.onError(error.detail || 'Streaming failed');
        return;
      }

      if (!res.body) {
        params.onError('ReadableStream not supported by backend response');
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;
          const lines = eventBlock.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6).trim();
            }
          }

          if (eventType && dataStr) {
            try {
              const parsed = JSON.parse(dataStr);
              if (eventType === 'content_delta') {
                params.onDelta(parsed.delta || '');
              } else if (eventType === 'tool_start') {
                params.onToolStart?.(parsed);
              } else if (eventType === 'tool_result') {
                params.onToolResult?.(parsed);
              } else if (eventType === 'message_complete') {
                params.onComplete(parsed);
              } else if (eventType === 'error') {
                params.onError(parsed.error || 'Server error during stream');
              }
            } catch (err) {
              console.error('Error parsing SSE event payload', err);
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Stream aborted by user
        return;
      }
      params.onError(err instanceof Error ? err.message : 'Unknown streaming error');
    }
  })();

  return () => controller.abort();
}
