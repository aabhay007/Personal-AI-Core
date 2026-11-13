export interface AgentStep {
  id: string;
  task_id: string;
  step_number: number;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'skipped';
  tool_name?: string | null;
  tool_arguments?: Record<string, unknown> | null;
  tool_result?: Record<string, unknown> | null;
  requires_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected' | null;
  error_message?: string | null;
  retry_count: number;
  execution_time_ms?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface AgentTask {
  id: string;
  workspace_id: string;
  title: string;
  goal: string;
  status: 'planning' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled';
  current_step_index: number;
  result_summary?: string | null;
  error_message?: string | null;
  steps: AgentStep[];
  created_at: string;
  updated_at: string;
}

export interface AgentTaskCreate {
  title: string;
  goal: string;
  conversation_id?: string | null;
  custom_plan?: Array<Record<string, unknown>>;
}
