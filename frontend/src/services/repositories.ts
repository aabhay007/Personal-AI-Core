import {
  CodeRepository,
  CodeRepositoryCreate,
  RepositoryFile,
  CodeSearchResponse,
} from '@/types/repository';
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

export async function listRepositories(workspaceId: string): Promise<CodeRepository[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load repositories');
  return res.json();
}

export async function createRepository(
  workspaceId: string,
  data: CodeRepositoryCreate
): Promise<CodeRepository> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories?workspace_id=${workspaceId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to connect repository');
  }
  return res.json();
}

export async function deleteRepository(repoId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories/${repoId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete repository');
}

export async function syncRepository(
  repoId: string
): Promise<{ status: string; indexed_files: number }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/sync`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to sync repository');
  }
  return res.json();
}

export async function getRepositoryTree(repoId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/tree`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load repository tree');
  return res.json();
}

export async function getRepositoryFile(
  repoId: string,
  path: string
): Promise<RepositoryFile> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/repositories/${repoId}/file?path=${encodeURIComponent(path)}`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) throw new Error('Failed to load file content');
  return res.json();
}

export async function searchRepositoryCode(
  repoId: string,
  query: string,
  extension?: string
): Promise<CodeSearchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/repositories/${repoId}/search`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query, file_extension: extension, limit: 5 }),
  });
  if (!res.ok) throw new Error('Code search failed');
  return res.json();
}
