import { DocumentItem } from '@/types/document';
import { getAccessToken } from './auth';

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

function getAuthHeaders(isFormData: boolean = false): HeadersInit {
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function uploadDocument(workspaceId: string, file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('workspace_id', workspaceId);
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Document upload failed');
  }
  return res.json();
}

export async function listDocuments(workspaceId: string): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/documents?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load documents');
  return res.json();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete document');
}
