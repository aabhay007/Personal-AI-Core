import {
  Integration,
  IntegrationCreate,
  IntegrationTestRequest,
  IntegrationTestResponse,
  SchemaMetadata,
} from '@/types/integration';
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

export async function listIntegrations(workspaceId: string): Promise<Integration[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to load integrations');
  return res.json();
}

export async function createIntegration(
  workspaceId: string,
  data: IntegrationCreate
): Promise<Integration> {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations?workspace_id=${workspaceId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to create database integration');
  }
  return res.json();
}

export async function deleteIntegration(integrationId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations/${integrationId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete integration');
}

export async function testUnsavedConnection(
  data: IntegrationTestRequest
): Promise<IntegrationTestResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Connection test failed');
  }
  return res.json();
}

export async function testSavedIntegration(
  integrationId: string
): Promise<IntegrationTestResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations/${integrationId}/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to test connection');
  return res.json();
}

export async function getIntegrationSchemas(
  integrationId: string,
  schemaName: string = 'public'
): Promise<SchemaMetadata> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/integrations/${integrationId}/schemas?schema_name=${schemaName}`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to inspect schema');
  }
  return res.json();
}
