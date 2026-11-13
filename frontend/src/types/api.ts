export interface DatabaseHealth {
  connected: boolean;
  message?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  project_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
}

export interface RootResponse {
  message: string;
  version: string;
  docs: string;
  health: string;
}
