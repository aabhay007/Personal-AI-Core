import { HealthResponse, RootResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch health status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRoot(): Promise<RootResponse> {
  const res = await fetch(`${API_BASE_URL}/`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch root status: ${res.statusText}`);
  }
  return res.json();
}
