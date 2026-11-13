export interface ColumnMetadata {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  default?: string | null;
}

export interface TableMetadata {
  table_name: string;
  schema: string;
  columns: ColumnMetadata[];
}

export interface SchemaMetadata {
  integration_id: string;
  integration_name: string;
  integration_type: string;
  schemas: string[];
  tables: TableMetadata[];
}

export interface Integration {
  id: string;
  workspace_id: string;
  name: string;
  integration_type: string;
  host?: string | null;
  port?: number | null;
  database?: string | null;
  username?: string | null;
  has_password: boolean;
  ssl_mode: string;
  approved_schemas?: string[] | null;
  approved_tables?: string[] | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IntegrationCreate {
  name: string;
  integration_type: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl_mode?: string;
  approved_schemas?: string[];
  approved_tables?: string[];
  options?: Record<string, unknown>;
}

export interface IntegrationTestRequest {
  integration_type: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl_mode?: string;
  options?: Record<string, unknown>;
}

export interface IntegrationTestResponse {
  success: boolean;
  latency_ms: number;
  version?: string | null;
  database?: string | null;
  error?: string | null;
}
